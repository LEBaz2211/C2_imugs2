"""Legacy compatibility adapters kept outside the core domain."""

from .rest import LegacyRestClient, LegacyRestResponse, to_legacy_mission_config

__all__ = ["LegacyRestClient", "LegacyRestResponse", "to_legacy_mission_config"]
