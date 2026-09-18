from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine


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


class SentinelReader:
    def __init__(self) -> None:
        pass

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

        annotation_dir = safe_path / "annotation"
        calibration_dir = safe_path / "annotation" / "calibration"
        noise_dir = safe_path / "annotation" / "noise"

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