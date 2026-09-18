from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.windows import Window


@dataclass(frozen=True)
class SentinelObservation:
    vv: np.ndarray
    vh: np.ndarray | None
    transform: Affine
    crs: CRS
    bounds: tuple[float, float, float, float]
    width: int
    height: int
    metadata: dict[str, Any]
    product_type: str
    acquisition_time: str | None
    orbit_direction: str | None


@dataclass(frozen=True)
class Tile:
    """A single tile from a larger raster."""
    data: np.ndarray
    transform: Affine
    window: Window
    tile_index: tuple[int, int]  # (row, col)


class SentinelReader:
    def __init__(self, tile_size: int = 512, overlap: int = 32) -> None:
        self.tile_size = tile_size
        self.overlap = overlap

    def read_safe(self, safe_path: Path) -> SentinelObservation:
        safe_path = Path(safe_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"SAFE directory not found: {safe_path}")

        measurement_dir = safe_path / "measurement"
        if not measurement_dir.exists():
            raise ValueError(f"Not a valid SAFE product: {measurement_dir} not found")

        vv_files = list(measurement_dir.glob("*vv*.tiff")) + list(measurement_dir.glob("*VV*.tiff"))
        vh_files = list(measurement_dir.glob("*vh*.tiff")) + list(measurement_dir.glob("*VH*.tiff"))

        if not vv_files:
            raise ValueError("No VV polarization file found in SAFE product")

        vv_path = vv_files[0]
        vh_path = vh_files[0] if vh_files else None

        metadata = self._parse_manifest(safe_path)

        with rasterio.open(vv_path) as vv_ds:
            vv = vv_ds.read(1).astype(np.float32)
            transform = vv_ds.transform
            crs = vv_ds.crs
            width = vv_ds.width
            height = vv_ds.height
            bounds = vv_ds.bounds

        vh = None
        if vh_path:
            with rasterio.open(vh_path) as vh_ds:
                vh = vh_ds.read(1).astype(np.float32)

        return SentinelObservation(
            vv=vv,
            vh=vh,
            transform=transform,
            crs=crs,
            bounds=(bounds.left, bounds.bottom, bounds.right, bounds.top),
            width=width,
            height=height,
            metadata=metadata,
            product_type=metadata.get("product_type", "GRD"),
            acquisition_time=metadata.get("acquisition_time"),
            orbit_direction=metadata.get("orbit_direction"),
        )

    def read_geotiff(self, tiff_path: Path) -> SentinelObservation:
        tiff_path = Path(tiff_path)
        if not tiff_path.exists():
            raise FileNotFoundError(f"GeoTIFF not found: {tiff_path}")

        with rasterio.open(tiff_path) as ds:
            vv = ds.read(1).astype(np.float32)
            vh = ds.read(2) if ds.count >= 2 else None
            if vh is not None:
                vh = vh.astype(np.float32)
            transform = ds.transform
            crs = ds.crs
            width = ds.width
            height = ds.height
            bounds = ds.bounds
            metadata = dict(ds.tags())

        return SentinelObservation(
            vv=vv,
            vh=vh,
            transform=transform,
            crs=crs,
            bounds=(bounds.left, bounds.bottom, bounds.right, bounds.top),
            width=width,
            height=height,
            metadata=metadata,
            product_type="GeoTIFF",
            acquisition_time=metadata.get("TIFFTAG_DATETIME"),
            orbit_direction=None,
        )

    def _parse_manifest(self, safe_path: Path) -> dict[str, Any]:
        manifest_path = safe_path / "manifest.safe"
        metadata = {}

        if manifest_path.exists():
            import xml.etree.ElementTree as ET

            tree = ET.parse(manifest_path)
            root = tree.getroot()

            for elem in root.iter():
                if "productType" in elem.tag:
                    metadata["product_type"] = elem.text
                elif "startTime" in elem.tag or "stopTime" in elem.tag:
                    if "acquisition_time" not in metadata:
                        metadata["acquisition_time"] = elem.text
                elif "orbitDirection" in elem.tag:
                    metadata["orbit_direction"] = elem.text

        return metadata

    def validate_crs(self, observation: SentinelObservation, expected_crs: str | CRS = "EPSG:4326") -> bool:
        """Validate that the observation CRS matches expected CRS."""
        if isinstance(expected_crs, str):
            expected_crs = CRS.from_string(expected_crs)
        return bool(observation.crs == expected_crs)

    def validate_transform(self, observation: SentinelObservation) -> bool:
        """Validate that the transform is valid (not identity, has reasonable scale)."""
        if observation.transform.is_identity:
            return False
        # Check for reasonable pixel size (not degenerate)
        if abs(observation.transform.a) < 1e-10 or abs(observation.transform.e) < 1e-10:
            return False
        return True

    def reproject_to_wgs84(self, observation: SentinelObservation) -> SentinelObservation:
        """Reproject observation to WGS84 (EPSG:4326) if not already."""
        if self.validate_crs(observation, "EPSG:4326"):
            return observation

        from rasterio.warp import calculate_default_transform, reproject

        dst_crs = CRS.from_epsg(4326)
        dst_transform, dst_width, dst_height = calculate_default_transform(
            observation.crs, dst_crs, observation.width, observation.height, *observation.bounds
        )

        vv_reprojected = np.empty((dst_height, dst_width), dtype=np.float32)
        reproject(
            source=observation.vv,
            destination=vv_reprojected,
            src_transform=observation.transform,
            src_crs=observation.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
        )

        vh_reprojected = None
        if observation.vh is not None:
            vh_reprojected = np.empty((dst_height, dst_width), dtype=np.float32)
            reproject(
                source=observation.vh,
                destination=vh_reprojected,
                src_transform=observation.transform,
                src_crs=observation.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear,
            )

        return SentinelObservation(
            vv=vv_reprojected,
            vh=vh_reprojected,
            transform=dst_transform,
            crs=dst_crs,
            bounds=rasterio.transform.array_bounds(dst_height, dst_width, dst_transform),
            width=dst_width,
            height=dst_height,
            metadata={**observation.metadata, "reprojected_to_wgs84": True},
            product_type=observation.product_type,
            acquisition_time=observation.acquisition_time,
            orbit_direction=observation.orbit_direction,
        )

    def tile_raster(self, observation: SentinelObservation) -> list[Tile]:
        """Split raster into overlapping tiles for model inference."""
        tiles = []
        h, w = observation.vv.shape

        step = self.tile_size - self.overlap
        n_rows = (h + step - 1) // step
        n_cols = (w + step - 1) // step

        for row_idx in range(n_rows):
            for col_idx in range(n_cols):
                y_start = row_idx * step
                x_start = col_idx * step
                y_end = min(y_start + self.tile_size, h)
                x_end = min(x_start + self.tile_size, w)

                window = Window(x_start, y_start, x_end - x_start, y_end - y_start)
                tile_transform = rasterio.windows.transform(window, observation.transform)

                vv_tile = observation.vv[y_start:y_end, x_start:x_end]
                vh_tile = None
                if observation.vh is not None:
                    vh_tile = observation.vh[y_start:y_end, x_start:x_end]

                # Stack VV and VH if both present
                if vh_tile is not None:
                    tile_data = np.stack([vv_tile, vh_tile], axis=0)
                else:
                    tile_data = vv_tile[np.newaxis, ...]

                tiles.append(Tile(
                    data=tile_data.astype(np.float32),
                    transform=tile_transform,
                    window=window,
                    tile_index=(row_idx, col_idx),
                ))

        return tiles

    def stitch_tiles(
        self,
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

        # Avoid division by zero
        count[count == 0] = 1
        return result / count

    def calibrate(self, observation: SentinelObservation) -> SentinelObservation:
        vv_calibrated = self._apply_calibration(observation.vv, "vv", observation.metadata)
        vh_calibrated = None
        if observation.vh is not None:
            vh_calibrated = self._apply_calibration(observation.vh, "vh", observation.metadata)

        return SentinelObservation(
            vv=vv_calibrated,
            vh=vh_calibrated,
            transform=observation.transform,
            crs=observation.crs,
            bounds=observation.bounds,
            width=observation.width,
            height=observation.height,
            metadata={**observation.metadata, "calibrated": True},
            product_type=observation.product_type,
            acquisition_time=observation.acquisition_time,
            orbit_direction=observation.orbit_direction,
        )

    def _apply_calibration(self, band: np.ndarray, pol: str, metadata: dict[str, Any]) -> np.ndarray:
        calibration_vector = metadata.get(f"calibration_vector_{pol}")
        if calibration_vector is None:
            return band
        return band * float(calibration_vector)

    def to_db_scale(self, observation: SentinelObservation) -> SentinelObservation:
        vv_db = 10 * np.log10(observation.vv + 1e-10)
        vh_db = None
        if observation.vh is not None:
            vh_db = 10 * np.log10(observation.vh + 1e-10)

        return SentinelObservation(
            vv=vv_db.astype(np.float32),
            vh=vh_db.astype(np.float32) if vh_db is not None else None,
            transform=observation.transform,
            crs=observation.crs,
            bounds=observation.bounds,
            width=observation.width,
            height=observation.height,
            metadata={**observation.metadata, "scale": "dB"},
            product_type=observation.product_type,
            acquisition_time=observation.acquisition_time,
            orbit_direction=observation.orbit_direction,
        )

    def normalize(self, observation: SentinelObservation, vv_range: tuple[float, float] = (-25, 5), vh_range: tuple[float, float] = (-30, 0)) -> SentinelObservation:
        vv_norm = np.clip((observation.vv - vv_range[0]) / (vv_range[1] - vv_range[0]), 0, 1)
        vh_norm = None
        if observation.vh is not None:
            vh_norm = np.clip((observation.vh - vh_range[0]) / (vh_range[1] - vh_range[0]), 0, 1)

        return SentinelObservation(
            vv=vv_norm.astype(np.float32),
            vh=vh_norm.astype(np.float32) if vh_norm is not None else None,
            transform=observation.transform,
            crs=observation.crs,
            bounds=observation.bounds,
            width=observation.width,
            height=observation.height,
            metadata={**observation.metadata, "normalized": True, "vv_range": vv_range, "vh_range": vh_range},
            product_type=observation.product_type,
            acquisition_time=observation.acquisition_time,
            orbit_direction=observation.orbit_direction,
        )