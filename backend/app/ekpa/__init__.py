import os
from datetime import date

from app.ekpa.provider import EkpaProvider


def get_ekpa_provider(today: date) -> EkpaProvider:
    """EKPA_PROVIDER=mock (default) or eclass."""
    if os.getenv("EKPA_PROVIDER", "mock").lower() == "eclass":
        from app.ekpa.eclass import EclassProvider

        return EclassProvider()
    from app.ekpa.mock import MockEkpaProvider

    return MockEkpaProvider(today)


def is_simulated() -> bool:
    return os.getenv("EKPA_PROVIDER", "mock").lower() != "eclass"
