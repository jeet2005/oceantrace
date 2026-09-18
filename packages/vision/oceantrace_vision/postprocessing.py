from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.features import shapes
from rasterio.transform import Affine
from scipy import ndimage
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import transform as shapely_transform

from oceantrace_vision.interfaces import SegmentationResult, SentinelObservation, Tile


@dataclass(frozen=True)
class SpillPolygon:
    polygon: Polygon | MultiPolygon
    area_km2: float
    perimeter_km: float
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]
    confidence: float
    properties: dict[str, Any]


def postprocess_mask(
    mask: np.ndarray,
    min_area_pixels: int = 50,
    max_hole_area_pixels: int = 100,
    morphology_kernel_size: int = 3,
) -> np.ndarray:
    """Clean up binary mask: remove small objects, fill holes, morphological operations."""
    if mask.dtype != np.uint8:
        mask = mask.astype(np.uint8)

    # Remove small connected components
    labeled, num_features = ndimage.label(mask)
    for i in range(1, num_features + 1):
        component_mask = (labeled == i)
        if component_mask.sum() < min_area_pixels:
            mask[component_mask] = 0

    # Fill small holes
    if max_hole_area_pixels > 0:
        inverted = 1 - mask
        labeled_holes, num_holes = ndimage.label(inverted)
        for i in range(1, num_holes + 1):
            hole_mask = (labeled_holes == i)
            if hole_mask.sum() < max_hole_area_pixels:
                mask[hole_mask] = 1

    # Morphological closing to smooth boundaries
    if morphology_kernel_size > 0:
        kernel = np.ones((morphology_kernel_size, morphology_kernel_size), np.uint8)
        mask = cv2_morphology_close(mask, kernel)

    return mask


def cv2_morphology_close(mask: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Morphological closing without OpenCV dependency."""
    from scipy.ndimage import binary_dilation, binary_erosion

    dilated = binary_dilation(mask, structure=kernel)
    closed = binary_erosion(dilated, structure=kernel)
    return closed.astype(np.uint8)  # type: ignore[no-any-return]


def extract_polygons(
    mask: np.ndarray,
    transform: Affine,
    crs: CRS,
    probability_map: np.ndarray | None = None,
    min_area_km2: float = 0.001,
) -> list[SpillPolygon]:
    """Extract GeoJSON polygons from binary mask with geometry calculations."""
    polygons = []

    # Use rasterio.features.shapes to extract polygons
    results = shapes(mask.astype(np.uint8), mask=(mask == 1), transform=transform)

    for geom, value in results:
        if value != 1:
            continue

        shapely_geom = shape(geom)
        if shapely_geom.is_empty:
            continue

        # Calculate area in km² using CRS-aware projection
        if crs and crs.is_projected:
            # Already in projected CRS
            area_km2 = shapely_geom.area / 1_000_000
            perimeter_km = shapely_geom.length / 1000
        else:
            # Geographic CRS - need to project for accurate area
            area_km2, perimeter_km = calculate_geodesic_area_perimeter(shapely_geom, crs)

        if area_km2 < min_area_km2:
            continue

        # Calculate centroid in geographic coordinates
        centroid = (shapely_geom.centroid.y, shapely_geom.centroid.x)

        # Bounding box
        minx, miny, maxx, maxy = shapely_geom.bounds

        # Confidence from probability map
        confidence = 0.5
        if probability_map is not None:
            # Create a rasterized version of this polygon to sample probabilities
            confidence = sample_probability(probability_map, shapely_geom, transform)

        polygons.append(SpillPolygon(
            polygon=shapely_geom,
            area_km2=area_km2,
            perimeter_km=perimeter_km,
            centroid=centroid,
            bbox=(minx, miny, maxx, maxy),
            confidence=confidence,
            properties={"value": int(value)},
        ))

    return polygons


def calculate_geodesic_area_perimeter(geom: Polygon | MultiPolygon, crs: CRS) -> tuple[float, float]:
    """Calculate area and perimeter using geodesic calculations for geographic CRS."""
    from pyproj import Geod

    geod = Geod(ellps="WGS84")

    if isinstance(geom, MultiPolygon):
        total_area = 0.0
        total_perim = 0.0
        for poly in geom.geoms:
            area, perim = calculate_geodesic_area_perimeter(poly, crs)
            total_area += area
            total_perim += perim
        return total_area, total_perim

    # Calculate geodesic area
    exterior_coords = list(geom.exterior.coords)
    lons = [c[0] for c in exterior_coords]
    lats = [c[1] for c in exterior_coords]
    area = abs(geod.polygon_area_perimeter(lons, lats)[0]) / 1_000_000

    # Calculate geodesic perimeter
    perim = 0.0
    for i in range(len(exterior_coords) - 1):
        _, _, dist = geod.inv(lons[i], lats[i], lons[i + 1], lats[i + 1])
        perim += dist
    perim /= 1000  # Convert to km

    return area, perim


def sample_probability(
    prob_map: np.ndarray,
    polygon: Polygon | MultiPolygon,
    transform: Affine,
) -> float:
    """Sample probability values within a polygon."""
    from rasterio.features import rasterize

    # Rasterize polygon to mask
    mask = rasterize(
        [(polygon, 1)],
        out_shape=prob_map.shape,
        transform=transform,
        fill=0,
        dtype=np.uint8,
    )

    values = prob_map[mask == 1]
    if len(values) == 0:
        return 0.5
    return float(values.mean())


def mask_to_geojson(polygons: list[SpillPolygon]) -> dict[str, Any]:
    """Convert spill polygons to GeoJSON FeatureCollection."""
    features = []
    for poly in polygons:
        features.append({
            "type": "Feature",
            "geometry": poly.polygon.__geo_interface__,
            "properties": {
                "area_km2": poly.area_km2,
                "perimeter_km": poly.perimeter_km,
                "centroid": poly.centroid,
                "bbox": poly.bbox,
                "confidence": poly.confidence,
                **poly.properties,
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def stitch_tiled_predictions(
    tiles: list[Tile],
    output_shape: tuple[int, int],
    num_channels: int = 1,
) -> np.ndarray:
    """Stitch tiles back into full raster, handling overlap by averaging."""
    h, w = output_shape
    result = np.zeros((num_channels, h, w), dtype=np.float32)
    count = np.zeros((num_channels, h, w), dtype=np.float32)

    for tile in tiles:
        y_start, x_start = tile.window.row_off, tile.window.col_off
        y_end = y_start + tile.window.height
        x_end = x_start + tile.window.width

        if tile.data.ndim == 3:
            tile_channels = tile.data
        else:
            tile_channels = tile.data[np.newaxis, ...]

        c, th, tw = tile_channels.shape
        result[:, y_start:y_end, x_start:x_end] += tile_channels
        count[:, y_start:y_end, x_start:x_end] += 1

    count[count == 0] = 1
    return result / count


def run_segmentation_pipeline(
    observation: SentinelObservation,
    model: "SatelliteModel",  # type: ignore[name-defined]
    tile_size: int = 512,
    overlap: int = 32,
    min_area_km2: float = 0.001,
) -> tuple[SegmentationResult, list[SpillPolygon], dict[str, Any]]:
    """Run full segmentation pipeline: tile -> predict -> stitch -> postprocess -> extract polygons."""
    from oceantrace_vision.reader import SentinelReader

    reader = SentinelReader(tile_size=tile_size, overlap=overlap)

    # Normalize observation
    normalized = reader.normalize(reader.to_db_scale(reader.calibrate(observation)))  # type: ignore[arg-type]

    # Tile the observation
    tiles = reader.tile_raster(normalized)

    # Run inference on each tile
    tile_results = []
    for tile in tiles:
        result = model.segment_array(tile.data)
        tile_results.append(Tile(
            data=result.probability_map if result.probability_map is not None else result.mask,
            transform=tile.transform,
            window=tile.window,
            tile_index=tile.tile_index,
        ))

    # Stitch probability maps
    prob_map = stitch_tiled_predictions(
        tile_results,
        output_shape=(normalized.height, normalized.width),
        num_channels=1,
    ).squeeze()

    # Threshold and postprocess
    mask = (prob_map > 0.5).astype(np.uint8)
    mask = postprocess_mask(mask)

    # Extract polygons
    polygons = extract_polygons(mask, observation.transform, observation.crs, prob_map, min_area_km2)

    # Calculate overall confidence
    overall_confidence = float(prob_map[mask == 1].mean()) if mask.sum() > 0 else 0.0

    result = SegmentationResult(
        mask=mask,
        probability_map=prob_map.astype(np.float32),
        confidence=overall_confidence,
        uncertainty="medium" if 0.3 < overall_confidence < 0.8 else "high" if overall_confidence >= 0.8 else "low",
        transform=observation.transform,
        crs=observation.crs,
        metadata={
            "tile_size": tile_size,
            "overlap": overlap,
            "num_tiles": len(tiles),
            "num_polygons": len(polygons),
            "total_area_km2": sum(p.area_km2 for p in polygons),
        },
    )

    return result, polygons, {
        "tiles": tiles,
        "prob_map": prob_map,
        "mask": mask,
    }