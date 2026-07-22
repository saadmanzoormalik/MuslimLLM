from .registry import ALLOWED_LICENSES


def licensing_decision(license_id: str, copyright_status: str):
    permitted = license_id in ALLOWED_LICENSES and copyright_status.lower() not in {"unknown", "restricted"}
    return {"permitted": permitted, "reason": "approved" if permitted else "license_or_copyright_block"}

