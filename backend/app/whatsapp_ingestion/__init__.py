"""WhatsApp chat export ingestion (Phase W1: WhatsApp Export Ingestion).

Mirrors app/email_ingestion/'s own package shape and conventions exactly:
parsing.py (raw text in, structured data out, no DB/storage access),
dedup.py (deterministic duplicate detection), zip_import.py (safe archive
extraction, reusing app/email_ingestion/zip_import.py's own security
primitives rather than reimplementing them), pipeline.py (orchestrates the
other three into real Document/WhatsAppMessage/WhatsAppMediaAttachment
rows, reusing app/ingestion/pipeline.py's ingest_document() and
app/ingestion/indexing.py's index_document() unchanged).
"""
