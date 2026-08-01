from portfolio_tracker.schemas.common import AbsoluteReturn, WindowMetrics


def test_absolute_return_round_trip():
    model = AbsoluteReturn(
        gain_inr=100.0,
        gain_pct=0.1,
        invested_cost=1000.0,
        current_value=1100.0,
    )
    assert model.model_dump()["gain_pct"] == 0.1


def test_window_metrics_allows_nulls():
    model = WindowMetrics(
        absolute_pct=None,
        absolute_inr=None,
        xirr=None,
        cagr=None,
        benchmark_return=None,
        absolute_excess_pp=None,
        xirr_excess_pp=None,
        cagr_excess_pp=None,
    )
    assert model.xirr is None
