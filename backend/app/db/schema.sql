-- Construction Claims Evidence Investigator — V0 initial schema
-- Requires the pgvector extension.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE projects (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE documents (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    doc_type        TEXT,                  -- e.g. 'drawing', 'site_instruction', 'dpr', etc. (filled by classification step)
    doc_date        DATE,
    referenced_ids  TEXT[],                -- e.g. ARRAY['SI-088', 'DMV7-STR-P42-001 Rev 1']
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_text_path   TEXT NOT NULL          -- path to extracted plain text on disk
);

CREATE TABLE document_chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number     INTEGER,
    chunk_text      TEXT NOT NULL,
    embedding       vector(384)            -- dimension depends on embedding model chosen; adjust if needed
);

CREATE TABLE investigations (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    question        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | running | complete | failed
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE investigation_steps (
    id                  SERIAL PRIMARY KEY,
    investigation_id    INTEGER NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    step_number         INTEGER NOT NULL,
    tool_called         TEXT,
    tool_input          JSONB,
    tool_output         JSONB,
    agent_reasoning     TEXT
);

CREATE TABLE dossier_findings (
    id                  SERIAL PRIMARY KEY,
    investigation_id    INTEGER NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    finding_type        TEXT NOT NULL CHECK (finding_type IN ('FACT', 'INFERENCE', 'CONTRADICTION', 'GAP', 'UNVERIFIED')),
    text                TEXT NOT NULL,
    source_document_id  INTEGER REFERENCES documents(id),
    source_page         INTEGER,
    source_excerpt      TEXT,
    verified            BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_investigation_steps_investigation_id ON investigation_steps(investigation_id);
CREATE INDEX idx_dossier_findings_investigation_id ON dossier_findings(investigation_id);
