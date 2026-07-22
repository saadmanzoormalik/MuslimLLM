def provenance_complete(record) -> bool:
    return all((record.source, record.retrieval_date, record.license, record.content_hash))

