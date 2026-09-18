from oceantrace_evaluation.metrics import dice, iou


def test_segmentation_metrics() -> None:
    predicted = [True, True, False, False]
    actual = [True, False, True, False]

    assert iou(predicted, actual) == 1 / 3
    assert dice(predicted, actual) == 0.5

