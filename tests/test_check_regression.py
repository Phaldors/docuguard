from app.scripts.check_regression import check_regression


def test_no_regression_when_metrics_are_unchanged() -> None:
    report = {"metrics": {"total_accuracy": 0.95}}

    assert check_regression(report, report) == []


def test_no_regression_when_a_higher_is_better_metric_improves() -> None:
    baseline = {"metrics": {"total_accuracy": 0.90}}
    candidate = {"metrics": {"total_accuracy": 0.97}}

    assert check_regression(baseline, candidate) == []


def test_detects_a_regression_in_a_higher_is_better_metric() -> None:
    baseline = {"metrics": {"total_accuracy": 0.95}}
    candidate = {"metrics": {"total_accuracy": 0.80}}

    failures = check_regression(baseline, candidate)

    assert len(failures) == 1
    assert "total_accuracy" in failures[0]


def test_detects_a_regression_in_a_lower_is_better_metric() -> None:
    baseline = {"metrics": {"supplier_name_flagged_rate": 0.19}}
    candidate = {"metrics": {"supplier_name_flagged_rate": 0.40}}

    failures = check_regression(baseline, candidate)

    assert len(failures) == 1
    assert "supplier_name_flagged_rate" in failures[0]


def test_a_drop_within_tolerance_is_not_flagged() -> None:
    baseline = {"metrics": {"total_accuracy": 0.95}}
    candidate = {"metrics": {"total_accuracy": 0.94}}

    assert check_regression(baseline, candidate, tolerance=0.02) == []


def test_a_drop_beyond_tolerance_is_flagged() -> None:
    baseline = {"metrics": {"total_accuracy": 0.95}}
    candidate = {"metrics": {"total_accuracy": 0.90}}

    assert check_regression(baseline, candidate, tolerance=0.02) != []


def test_an_unlisted_metric_is_ignored() -> None:
    baseline = {"metrics": {"sample_count": 100}}
    candidate = {"metrics": {"sample_count": 10}}

    assert check_regression(baseline, candidate) == []


def test_a_metric_missing_from_either_report_is_skipped() -> None:
    baseline = {"metrics": {"total_accuracy": 0.95}}
    candidate = {"metrics": {}}

    assert check_regression(baseline, candidate) == []


def test_a_null_metric_value_is_skipped() -> None:
    baseline = {"metrics": {"total_accuracy": None}}
    candidate = {"metrics": {"total_accuracy": 0.5}}

    assert check_regression(baseline, candidate) == []


def test_multiple_regressions_are_all_reported() -> None:
    baseline = {"metrics": {"total_accuracy": 0.95, "abstention_rate": 1.0}}
    candidate = {"metrics": {"total_accuracy": 0.50, "abstention_rate": 0.5}}

    failures = check_regression(baseline, candidate)

    assert len(failures) == 2
