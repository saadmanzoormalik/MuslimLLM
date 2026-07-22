from __future__ import annotations

import hashlib
import os
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


@dataclass
class ArchiveValidationResult:
    valid: bool
    code: str = "ok"
    archive_hash: str | None = None
    file_count: int = 0
    expanded_bytes: int = 0
    suspicious_files: list[str] = field(default_factory=list)


EXECUTABLE_SUFFIXES = {".app", ".bat", ".bin", ".cmd", ".com", ".dll", ".dmg", ".exe", ".jar", ".msi", ".pkg", ".ps1", ".scr", ".sh"}


def validate_archive_for_extraction(path: Path) -> ArchiveValidationResult:
    max_archive = int(os.getenv("CONTEXT_SYNC_MAX_ARCHIVE_BYTES", str(2 * 1024 * 1024 * 1024)))
    max_expanded = int(os.getenv("CONTEXT_SYNC_MAX_EXPANDED_BYTES", str(8 * 1024 * 1024 * 1024)))
    max_files = int(os.getenv("CONTEXT_SYNC_MAX_FILES", "250000"))
    allow_executables = os.getenv("CONTEXT_SYNC_ALLOW_EXECUTABLES", "false").lower() == "true"
    if not path.is_file() or path.stat().st_size <= 0:
        return ArchiveValidationResult(False, "archive_unreadable")
    if path.stat().st_size > max_archive:
        return ArchiveValidationResult(False, "archive_too_large")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > max_files:
                return ArchiveValidationResult(False, "too_many_files", digest.hexdigest(), len(members))
            expanded = 0
            suspicious = []
            has_conversations = False
            for member in members:
                normalized = member.filename.replace("\\", "/")
                pure = PurePosixPath(normalized)
                if pure.is_absolute() or ".." in pure.parts or normalized.startswith(("/", "\\")):
                    return ArchiveValidationResult(False, "path_traversal", digest.hexdigest(), len(members), expanded)
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    return ArchiveValidationResult(False, "symlink_rejected", digest.hexdigest(), len(members), expanded)
                expanded += member.file_size
                if expanded > max_expanded:
                    return ArchiveValidationResult(False, "expanded_size_exceeded", digest.hexdigest(), len(members), expanded)
                if member.compress_size and member.file_size > 10_000_000 and member.file_size / member.compress_size > 500:
                    return ArchiveValidationResult(False, "decompression_bomb", digest.hexdigest(), len(members), expanded)
                suffix = PurePosixPath(normalized.lower()).suffix
                if suffix in EXECUTABLE_SUFFIXES:
                    suspicious.append(normalized)
                    if not allow_executables:
                        return ArchiveValidationResult(False, "executable_rejected", digest.hexdigest(), len(members), expanded, suspicious)
                base = PurePosixPath(normalized).name.lower()
                if base == "conversations.json" or (base.endswith(".json") and base[:-5].isdigit()):
                    has_conversations = True
            if not has_conversations:
                return ArchiveValidationResult(False, "chatgpt_export_not_recognized", digest.hexdigest(), len(members), expanded)
            return ArchiveValidationResult(True, archive_hash=digest.hexdigest(), file_count=len(members), expanded_bytes=expanded, suspicious_files=suspicious)
    except (zipfile.BadZipFile, OSError):
        return ArchiveValidationResult(False, "invalid_zip", digest.hexdigest())
