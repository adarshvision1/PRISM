"""Compatibility import for historical scripts; implementation lives in inference."""
from .inference import SegmentationPredictor

PointNetPredictor = SegmentationPredictor
