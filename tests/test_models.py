import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Listing,
    ListingObservation,
    ListingState,
    OwnedGear,
    TradeDetail,
)


def test_listing_identity_is_unique_within_a_source() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Listing(
                source="craigslist",
                source_listing_id="8001021969",
                url="https://example.test/first",
                title="Oddball synth",
                price_cents=40000,
            )
        )
        session.commit()

        session.add(
            Listing(
                source="craigslist",
                source_listing_id="8001021969",
                url="https://example.test/repost",
                title="Oddball synth repost",
                price_cents=39000,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_listing_observations_preserve_price_history_and_allow_barter() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        listing = Listing(
            source="craigslist",
            source_listing_id="trade-1",
            url="https://example.test/trade",
            title="FSOT synth for bass",
            price_cents=None,
        )
        session.add(listing)
        session.flush()
        session.add_all(
            [
                ListingObservation(listing_id=listing.id, price_cents=None, available=True),
                ListingObservation(listing_id=listing.id, price_cents=35000, available=True),
            ]
        )
        session.commit()

        observations = session.query(ListingObservation).order_by(ListingObservation.id).all()

        assert [observation.price_cents for observation in observations] == [None, 35000]
        assert all(observation.listing_id == listing.id for observation in observations)


def test_listing_state_survives_marketplace_updates() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        listing = Listing(
            source="guitar-center",
            source_listing_id="sku-1",
            url="https://example.test/sku-1",
            title="Used bass",
            price_cents=49999,
        )
        session.add(listing)
        session.flush()
        session.add(ListingState(listing_id=listing.id, state="interested"))
        session.commit()

        listing.title = "Used bass - price drop"
        listing.price_cents = 44999
        session.commit()
        session.expire_all()

        state = session.query(ListingState).one()
        assert state.state == "interested"
        assert state.listing_id == listing.id


def test_trade_details_explain_matches_against_owned_gear() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        owned = OwnedGear(
            name="Fender Jazz Bass",
            aliases=["jazz bass", "j-bass"],
            category="Bass",
            available_for_trade=True,
        )
        listing = Listing(
            source="craigslist",
            source_listing_id="fsot-1",
            url="https://example.test/fsot-1",
            title="FSOT Korg synth for Jazz Bass",
            price_cents=None,
        )
        session.add_all([owned, listing])
        session.flush()
        session.add(
            TradeDetail(
                listing_id=listing.id,
                offered_text="Korg synth",
                wanted_text="Jazz Bass",
                match_type="two-way",
                matched_terms=["synth", "jazz bass"],
                explanation="Offers a synth and wants My Gear: Fender Jazz Bass",
            )
        )
        session.commit()

        trade = session.query(TradeDetail).one()
        assert owned.aliases == ["jazz bass", "j-bass"]
        assert trade.matched_terms == ["synth", "jazz bass"]
        assert trade.explanation.startswith("Offers a synth")
