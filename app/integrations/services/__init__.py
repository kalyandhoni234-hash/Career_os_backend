from abc import ABC, abstractmethod
from datetime import datetime, timezone


class BaseIntegrationService(ABC):
    provider: str

    @abstractmethod
    def get_authorize_url(self, redirect_uri: str, state: str = "") -> str: ...

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> dict: ...

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> dict: ...

    @abstractmethod
    def sync_data(self, access_token: str) -> dict: ...

    @abstractmethod
    def is_configured(self) -> bool: ...


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
