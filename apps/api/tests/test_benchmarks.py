from portfolio_tracker.db.engine import get_session_factory
from portfolio_tracker.db.models import Instrument
from portfolio_tracker.modules import benchmarks


def test_default_benchmark_by_category():
    mid = Instrument(symbol="X", instrument_type="mf", mf_category="Mid Cap")
    assert benchmarks.default_benchmark_for(mid) == "Nifty Midcap 150"
    eq = Instrument(symbol="RELIANCE", instrument_type="equity")
    assert benchmarks.default_benchmark_for(eq) == "Nifty 500"
    unknown = Instrument(symbol="Y", instrument_type="mf", mf_category=None)
    assert benchmarks.default_benchmark_for(unknown) == "Nifty 500"


def test_user_override_wins():
    Session = get_session_factory()
    with Session() as session:
        inst = Instrument(symbol="RELIANCE", instrument_type="equity", exchange="NSE")
        session.add(inst)
        session.flush()
        benchmarks.ensure_benchmark_map(session, inst)
        benchmarks.set_benchmark_override(session, inst.id, "Nifty 50")
        session.commit()
        row = benchmarks.ensure_benchmark_map(session, inst)
        assert row.benchmark_index == "Nifty 50"
        assert row.source == "user"


def test_value_weighted_blend():
    # weights 0.7 and 0.3, returns 10% and 20% → 13%
    assert abs(benchmarks.portfolio_blended_benchmark_return([(0.7, 0.10), (0.3, 0.20)]) - 0.13) < 1e-9
