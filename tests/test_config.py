import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_have_mvp_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEAR_HOUND_DATABASE_URL", raising=False)
    monkeypatch.delenv("GEAR_HOUND_MAX_PRICE", raising=False)
    monkeypatch.delenv("GEAR_HOUND_REGION", raising=False)

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:////data/gear-hound.db"
    assert settings.max_price == 500
    assert settings.region == "austin"
    assert settings.craigslist_area_url == "https://www.craigslist.org/area/austin"
    assert settings.guitar_center_store_names == ("Round Rock", "Austin", "South Austin")
    assert settings.guitar_center_store_urls == (
        "https://www.guitarcenter.com/Round-Rock/Used",
        "https://www.guitarcenter.com/Austin/Used",
        "https://www.guitarcenter.com/South-Austin?filters=condition:Used&Ns=cD",
    )


def test_settings_accept_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEAR_HOUND_DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("GEAR_HOUND_MAX_PRICE", "750")
    monkeypatch.setenv("GEAR_HOUND_REGION", "austin-cedar-park")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///test.db"
    assert settings.max_price == 750
    assert settings.region == "austin-cedar-park"


def test_settings_reject_non_positive_max_price() -> None:
    with pytest.raises(ValidationError):
        Settings(max_price=0, _env_file=None)
