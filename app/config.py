from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GEAR_HOUND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:////data/gear-hound.db"
    max_price: int = Field(default=500, gt=0)
    region: str = "austin"
    craigslist_area_url: str = "https://www.craigslist.org/area/austin"
    guitar_center_store_names: tuple[str, ...] = ("Round Rock", "Austin", "South Austin")
    guitar_center_store_urls: tuple[str, ...] = (
        "https://www.guitarcenter.com/Round-Rock/Used",
        "https://www.guitarcenter.com/Austin/Used",
        "https://www.guitarcenter.com/South-Austin?filters=condition:Used&Ns=cD",
    )
