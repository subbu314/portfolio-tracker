from portfolio_tracker.modules import metrics


def test_absolute_return():
    result = metrics.absolute_return(invested_cost=100_000, current_value=125_000)
    assert result["gain_inr"] == 25_000
    assert abs(result["gain_pct"] - 0.25) < 1e-9


def test_absolute_return_na_when_zero_cost():
    result = metrics.absolute_return(invested_cost=0, current_value=1000)
    assert result["gain_pct"] is None


def test_cagr_requires_365_days():
    assert metrics.cagr(100, 110, "2024-01-01", "2024-06-01") is None
    value = metrics.cagr(100, 121, "2022-01-01", "2024-01-01")
    assert value is not None
    assert abs(value - 0.1) < 1e-6


def test_xirr_simple():
    flows = [
        ("2022-01-01", -1000.0),
        ("2024-01-01", 1210.0),
    ]
    rate = metrics.xirr(flows)
    assert rate is not None
    assert abs(rate - 0.1) < 1e-3


def test_invested_cost_with_partial_sell():
    # buy 10 @ 100 fee 0 → cost 1000; sell 4 → remove 400; remaining cost 600
    cost = metrics.invested_cost_from_transactions(
        [
            ("buy", 10, 100.0, 0.0),
            ("sell", 4, 120.0, 0.0),
        ]
    )
    assert abs(cost - 600.0) < 1e-9


def test_excess_pp():
    assert abs(metrics.excess_pp(0.15, 0.10) - 5.0) < 1e-9


def test_cagr_not_suppressed_for_multi_buy_span():
    # Multiple buys do not block CAGR when span ≥ 365d — use invested_cost → MV heuristic
    assert metrics.cagr(100_000, 120_000, "2022-01-01", "2024-01-01") is not None


def test_window_start_requires_enough_history():
    # 2024-06-01 − 365d = 2023-06-02; inception 2023-06-01 → 1Y available; 3Y not
    assert metrics.window_start("2024-06-01", "1Y", "2023-06-01") == "2023-06-02"
    assert metrics.window_start("2024-06-01", "3Y", "2023-06-01") is None
    assert metrics.window_start("2024-06-01", "ITD", "2023-06-01") == "2023-06-01"


def test_rolling_xirr_includes_opening_mv():
    flows = metrics.build_rolling_xirr_cashflows(
        opening_mv=1000.0,
        window_start="2023-01-01",
        trades_in_window=[("2023-06-01", "buy", 1, 100.0, 0.0)],
        terminal_mv=1500.0,
        as_of="2024-01-01",
    )
    assert flows[0] == ("2023-01-01", -1000.0)
    assert flows[-1] == ("2024-01-01", 1500.0)


def test_benchmark_xirr_same_cashflows_not_point_to_point():
    # Buy ₹1000 of "stock" when index=100 → 10 units; as_of index=121 → terminal 1210
    prices = {"2022-01-01": 100.0, "2024-01-01": 121.0}

    def idx(day: str) -> float | None:
        return prices.get(day)

    trades = [("2022-01-01", "buy", 1, 1000.0, 0.0)]
    bx = metrics.benchmark_xirr_from_trades(trades, idx, "2024-01-01")
    assert bx is not None
    assert abs(bx - 0.1) < 1e-3
    # Must not equal a mistaken excess that compared XIRR to simple return incorrectly in callers
    assert abs(metrics.excess_pp(0.1, bx)) < 1e-6


def test_benchmark_xirr_with_opening_mv_and_window():
    # Same shape as rolling XIRR: opening MV buys index units at window_start too.
    prices = {"2023-01-01": 100.0, "2023-06-01": 110.0, "2024-01-01": 121.0}

    def idx(day: str) -> float | None:
        return prices.get(day)

    trades = [("2023-06-01", "buy", 1, 110.0, 0.0)]
    bx = metrics.benchmark_xirr_from_trades(
        trades,
        idx,
        "2024-01-01",
        opening_mv=1000.0,
        window_start="2023-01-01",
    )
    assert bx is not None


def test_benchmark_xirr_none_when_index_price_missing():
    def idx(day: str) -> float | None:
        return None

    trades = [("2022-01-01", "buy", 1, 1000.0, 0.0)]
    assert metrics.benchmark_xirr_from_trades(trades, idx, "2024-01-01") is None


def test_xirr_none_for_single_flow():
    assert metrics.xirr([("2022-01-01", -1000.0)]) is None


def test_xirr_none_for_all_same_sign():
    assert (
        metrics.xirr([("2022-01-01", -1000.0), ("2023-01-01", -100.0)]) is None
    )


def test_point_to_point_return():
    assert abs(metrics.point_to_point_return(100.0, 125.0) - 0.25) < 1e-9
    assert metrics.point_to_point_return(0.0, 125.0) is None


def test_benchmark_return_matches_point_to_point():
    assert metrics.benchmark_return(100.0, 110.0) == metrics.point_to_point_return(100.0, 110.0)
    assert metrics.benchmark_return(0.0, 110.0) is None


def test_rolling_absolute_uses_point_to_point_when_opening_mv_positive():
    result = metrics.rolling_absolute(opening_mv=1000.0, terminal_mv=1250.0)
    assert result["invested_cost"] == 1000.0
    assert abs(result["gain_pct"] - 0.25) < 1e-9


def test_rolling_absolute_falls_back_to_invested_cost_without_opening_position():
    # No position at window start: use in-window buys/sells only vs terminal MV.
    result = metrics.rolling_absolute(
        opening_mv=0.0,
        terminal_mv=1200.0,
        trades_in_window=[("buy", 10, 100.0, 0.0)],
    )
    assert result["invested_cost"] == 1000.0
    assert abs(result["gain_pct"] - 0.2) < 1e-9


def test_rolling_cagr_none_without_opening_position():
    assert metrics.rolling_cagr(
        opening_mv=0.0, terminal_mv=1200.0, window_start="2022-01-01", as_of="2024-01-01"
    ) is None


def test_rolling_cagr_with_opening_position():
    value = metrics.rolling_cagr(
        opening_mv=100.0, terminal_mv=121.0, window_start="2022-01-01", as_of="2024-01-01"
    )
    assert value is not None
    assert abs(value - 0.1) < 1e-6


def test_window_metric_bundle_excess_units():
    absolute = metrics.absolute_return(invested_cost=100_000, current_value=115_000)
    bundle = metrics.window_metric_bundle(
        absolute=absolute,
        xirr_value=0.12,
        cagr_value=0.10,
        bench_return=0.10,
        bench_cagr=0.08,
        bench_xirr=0.09,
    )
    assert abs(bundle["absolute_excess_pp"] - 5.0) < 1e-9  # (0.15 - 0.10) * 100
    assert abs(bundle["cagr_excess_pp"] - 2.0) < 1e-9  # (0.10 - 0.08) * 100
    assert abs(bundle["xirr_excess_pp"] - 3.0) < 1e-9  # (0.12 - 0.09) * 100


def test_window_metric_bundle_null_fields_when_missing():
    absolute = metrics.absolute_return(invested_cost=0, current_value=1000)
    bundle = metrics.window_metric_bundle(
        absolute=absolute,
        xirr_value=None,
        cagr_value=None,
        bench_return=None,
        bench_cagr=None,
        bench_xirr=None,
    )
    assert bundle["absolute_excess_pp"] is None
    assert bundle["cagr_excess_pp"] is None
    assert bundle["xirr_excess_pp"] is None
