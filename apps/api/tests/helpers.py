from portfolio_tracker.db.models import BenchmarkPrice, Price


def seed_equity_fixture_prices(session, as_of: str) -> None:
    """Prices + Nifty 500 benches matching equity_tradebook.csv symbols."""
    session.add_all(
        [
            Price(
                symbol="RELIANCE.NS",
                price_date="2024-01-15",
                close=2500.0,
                source="yahoo",
            ),
            Price(
                symbol="RELIANCE.NS",
                price_date=as_of,
                close=3000.0,
                source="yahoo",
            ),
            Price(
                symbol="INFY.NS",
                price_date="2024-02-01",
                close=1500.0,
                source="yahoo",
            ),
            Price(
                symbol="INFY.NS",
                price_date=as_of,
                close=1800.0,
                source="yahoo",
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date="2024-01-15",
                close=10000.0,
            ),
            BenchmarkPrice(
                index_symbol="Nifty 500",
                price_date=as_of,
                close=12000.0,
            ),
        ]
    )
    session.commit()
