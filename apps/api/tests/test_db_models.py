from portfolio_tracker.db.engine import init_db, get_session_factory, reset_db_cache
from portfolio_tracker.db.models import Instrument, Transaction


def test_init_db_creates_parent_directory(tmp_path, monkeypatch):
    db_path = tmp_path / "nested" / "dir" / "portfolio.db"
    assert not db_path.parent.exists()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    from portfolio_tracker.config import get_settings

    get_settings.cache_clear()
    reset_db_cache()
    init_db()

    assert db_path.parent.exists()
    assert db_path.exists()


def test_can_insert_instrument_and_transaction():
    init_db()
    Session = get_session_factory()
    with Session() as session:
        inst = Instrument(
            symbol="RELIANCE",
            isin="INE002A01018",
            instrument_type="equity",
            exchange="NSE",
            mf_category=None,
        )
        session.add(inst)
        session.flush()
        tx = Transaction(
            instrument_id=inst.id,
            trade_date="2024-01-15",
            side="buy",
            quantity=10,
            price=2500.0,
            fees=20.0,
            source="csv",
            dedupe_key="csv:equity:RELIANCE:2024-01-15:buy:10:2500.0:OID1",
        )
        session.add(tx)
        session.commit()
        assert session.get(Instrument, inst.id).symbol == "RELIANCE"
        assert session.query(Transaction).count() == 1
