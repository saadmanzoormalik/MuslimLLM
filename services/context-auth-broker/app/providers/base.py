from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDefinition:
    provider_id: str
    display_name: str
    method: str
    available: bool
    consumer_history_api: bool
    official_export_supported: bool
