def contamination_report(train_records, evaluation_hashes: set[str]):
    overlaps = [record.content_hash for record in train_records if record.content_hash in evaluation_hashes]
    return {"passed": not overlaps, "overlap_count": len(overlaps), "overlap_hashes": overlaps}

