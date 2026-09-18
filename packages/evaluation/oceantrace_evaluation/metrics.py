from collections.abc import Sequence


def iou(predicted: Sequence[bool], actual: Sequence[bool]) -> float:
    intersection = sum(p and a for p, a in zip(predicted, actual, strict=True))
    union = sum(p or a for p, a in zip(predicted, actual, strict=True))
    return 1.0 if union == 0 else intersection / union


def dice(predicted: Sequence[bool], actual: Sequence[bool]) -> float:
    intersection = sum(p and a for p, a in zip(predicted, actual, strict=True))
    total = sum(predicted) + sum(actual)
    return 1.0 if total == 0 else 2 * intersection / total

