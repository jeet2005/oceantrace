from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from oceantrace_vision.interfaces import (
    CheckpointLoader,
    ModelRegistry,
    SatelliteModel,
    SegmentationResult,
)


class UNet(nn.Module):
    """Simple U-Net architecture for oil spill segmentation."""

    def __init__(self, in_channels: int = 2, out_channels: int = 1, features: list[int] | None = None) -> None:
        super().__init__()
        if features is None:
            features = [64, 128, 256, 512]

        self.encoder = nn.ModuleList()
        self.decoder = nn.ModuleList()
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # Encoder
        for feature in features:
            self.encoder.append(self._block(in_channels, feature))
            in_channels = feature

        # Bottleneck
        self.bottleneck = self._block(features[-1], features[-1] * 2)

        # Decoder
        for feature in reversed(features):
            self.decoder.append(nn.ConvTranspose2d(feature * 2, feature, kernel_size=2, stride=2))
            self.decoder.append(self._block(feature * 2, feature))

        self.final_conv = nn.Conv2d(features[0], out_channels, kernel_size=1)

    def _block(self, in_channels: int, out_channels: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skip_connections = []

        for encoder_block in self.encoder:
            x = encoder_block(x)
            skip_connections.append(x)
            x = self.pool(x)

        x = self.bottleneck(x)
        skip_connections = skip_connections[::-1]

        for idx in range(0, len(self.decoder), 2):
            x = self.decoder[idx](x)
            skip = skip_connections[idx // 2]

            # Handle shape mismatch
            if x.shape != skip.shape:
                x = nn.functional.interpolate(x, size=skip.shape[2:], mode="bilinear", align_corners=False)

            x = torch.cat((skip, x), dim=1)
            x = self.decoder[idx + 1](x)

        return torch.sigmoid(self.final_conv(x))


class UNetModel(SatelliteModel):
    name = "unet"

    def __init__(self, model: nn.Module, device: str = "cpu", threshold: float = 0.5) -> None:
        self.model = model.to(device)
        self.device = device
        self.threshold = threshold
        self.model.eval()

    def segment(self, raster_path: Path) -> SegmentationResult:
        import rasterio

        with rasterio.open(raster_path) as src:
            array = src.read().astype(np.float32)
            transform = src.transform
            crs = src.crs

        return self.segment_array(array, transform=transform, crs=crs)

    def segment_batch(self, raster_paths: list[Path]) -> list[SegmentationResult]:
        return [self.segment(path) for path in raster_paths]

    def segment_array(
        self,
        array: np.ndarray,
        transform: Any = None,
        crs: Any = None,
    ) -> SegmentationResult:
        # Normalize array to [0, 1] if not already
        if array.max() > 1.0:
            array = array / (array.max() + 1e-8)

        # Ensure correct shape: [C, H, W]
        if array.ndim == 2:
            array = array[np.newaxis, ...]
        elif array.ndim == 3 and array.shape[0] > 4:
            array = array.transpose(2, 0, 1)

        # Pad to multiple of 32 for U-Net
        h, w = array.shape[-2:]
        pad_h = (32 - h % 32) % 32
        pad_w = (32 - w % 32) % 32
        array = np.pad(array, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")

        tensor = torch.from_numpy(array).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(tensor)
            prob_map = output.squeeze().cpu().numpy()

        # Remove padding
        prob_map = prob_map[:h, :w]
        mask = (prob_map > self.threshold).astype(np.uint8)

        # Calculate confidence as mean probability in positive regions
        if mask.sum() > 0:
            confidence = float(prob_map[mask == 1].mean())
        else:
            confidence = 0.0

        return SegmentationResult(
            mask=mask,
            probability_map=prob_map.astype(np.float32),
            confidence=confidence,
            uncertainty="medium" if 0.3 < confidence < 0.8 else "high" if confidence >= 0.8 else "low",
            transform=transform,
            crs=crs,
            metadata={"threshold": self.threshold, "model": self.name},
        )


class PyTorchCheckpointLoader(CheckpointLoader):
    def load(self, checkpoint_path: Path, device: str = "cpu") -> SatelliteModel:
        checkpoint_path = Path(checkpoint_path)
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        checkpoint = torch.load(checkpoint_path, map_location=device)

        # Support different checkpoint formats
        if isinstance(checkpoint, dict):
            if "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
            elif "state_dict" in checkpoint:
                state_dict = checkpoint["state_dict"]
            else:
                state_dict = checkpoint
        else:
            state_dict = checkpoint

        # Create model and load weights
        model = UNet(in_channels=2, out_channels=1)
        model.load_state_dict(state_dict, strict=False)

        return UNetModel(model, device=device)


class SimpleModelRegistry(ModelRegistry):
    def __init__(self) -> None:
        self._models: dict[str, SatelliteModel] = {}

    def register(self, name: str, model: SatelliteModel) -> None:
        self._models[name] = model

    def get(self, name: str) -> SatelliteModel | None:
        return self._models.get(name)

    def list_models(self) -> list[str]:
        return list(self._models.keys())