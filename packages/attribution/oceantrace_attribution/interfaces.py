from typing import Protocol

from oceantrace_common.models import CandidateScore, VesselTrack
from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    proximity: float = Field(default=0.25, ge=0)
    temporal_overlap: float = Field(default=0.25, ge=0)
    trajectory_consistency: float = Field(default=0.20, ge=0)
    drift_consistency: float = Field(default=0.20, ge=0)
    behavioral_anomaly: float = Field(default=0.10, ge=0)


class CandidateScorer(Protocol):
    def score(self, track: VesselTrack, weights: ScoringWeights) -> CandidateScore:
        """Calculate a transparent investigative score from deterministic features."""

