from portfolio_tracker.schemas.common import AbsoluteReturn, WindowMetrics, WindowsMap


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


def test_windows_map_round_trip_preserves_json_keys():
    raw = {
        "ITD": {
            "absolute_pct": 0.1,
            "absolute_inr": 10.0,
            "xirr": None,
            "cagr": None,
            "benchmark_return": None,
            "absolute_excess_pp": None,
            "xirr_excess_pp": None,
            "cagr_excess_pp": None,
        },
        "1Y": None,
        "3Y": None,
        "5Y": None,
    }
    model = WindowsMap.model_validate(raw)
    dumped = model.model_dump(by_alias=True)
    assert set(dumped.keys()) == {"ITD", "1Y", "3Y", "5Y"}
    assert dumped["ITD"]["absolute_pct"] == 0.1
    assert dumped["1Y"] is None
