from typing import Any, Literal

from pydantic import BaseModel


ImportMode = Literal["api", "file", "paste", "folder"]
ImportStatus = Literal["pending", "scanning", "preview_ready", "importing", "completed", "failed", "cancelled"]


class ProviderCapability(BaseModel):
    provider: str
    display_name: str
    supports_api_import: bool
    supports_file_import: bool
    supports_project_import: bool
    supports_attachment_import: bool
    supports_memory_import: bool
    supports_chat_history_import: bool
    preferred_import_mode: str
    supported_data_types: list[str]
    privacy_note: str
    api_status: dict[str, Any]


class DateRange(BaseModel):
    preset: str = "last_6_months"
    start: str | None = None
    end: str | None = None


class ImportOptions(BaseModel):
    import_chats: bool = True
    import_projects: bool = True
    import_files: bool = False
    generate_summaries: bool = True
    generate_memory_suggestions: bool = True
    rebuild_context_graph: bool = True
    add_files_to_rag: bool = False
    keep_provider_names_visible: bool = True
    cloud_summarization_enabled: bool = False


class PasteImportRequest(BaseModel):
    provider: str = "generic"
    content: str
    title: str | None = None
    date_range: DateRange = DateRange()
    options: ImportOptions = ImportOptions()


class ScanRequest(BaseModel):
    job_id: str


class ConfirmImportRequest(BaseModel):
    options: ImportOptions = ImportOptions()


class ConnectRequest(BaseModel):
    date_range: DateRange = DateRange()


class CallbackRequest(BaseModel):
    code: str | None = None
    state: str | None = None


class MemoryDecisionRequest(BaseModel):
    note: str | None = None


class DeleteJobRequest(BaseModel):
    delete_imported_data: bool = False
