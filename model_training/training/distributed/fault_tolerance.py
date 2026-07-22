def classify_failure(error: Exception):
    message = str(error).lower()
    if "out of memory" in message: return {"recoverable": True, "action": "reduce_microbatch_and_resume"}
    if "nan" in message or "inf" in message: return {"recoverable": True, "action": "restore_last_verified_checkpoint"}
    if "hash mismatch" in message: return {"recoverable": False, "action": "quarantine_checkpoint"}
    return {"recoverable": False, "action": "human_review"}

