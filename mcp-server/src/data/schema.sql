CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    email TEXT,
    phone TEXT,
    title TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER,
    title TEXT NOT NULL,
    value REAL,
    stage TEXT DEFAULT 'lead',
    notes TEXT,
    sentiment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS followups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER,
    deal_id INTEGER,
    title TEXT NOT NULL,
    due_date TIMESTAMP,
    completed BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);

CREATE TABLE IF NOT EXISTS call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER,
    deal_id INTEGER,
    transcript TEXT,
    summary TEXT,
    duration_seconds INTEGER,
    sentiment TEXT,
    buying_signals TEXT,
    risks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER,
    deal_id INTEGER,
    type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER,
    deal_id INTEGER,
    title TEXT NOT NULL,
    due_date TIMESTAMP,
    priority TEXT DEFAULT 'medium',
    notes TEXT,
    completed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);

CREATE TABLE IF NOT EXISTS stage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER,
    from_stage TEXT,
    to_stage TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'local',
    meta TEXT,
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);

-- ==========================================================================
-- Local CRM target (the "local" sync_to_crm target)
-- ==========================================================================
-- A real, working CRM implementation — not a stub — so the demo can show a
-- sync that genuinely succeeds without any external credentials. Field names
-- deliberately mirror Salesforce's sobjects vocabulary (FirstName, StageName,
-- CloseDate, Account): swapping in the Salesforce adapter is a credential
-- change, not a code change.
--
-- The UNIQUE constraint on crm_local_sync_log.idempotency_key is load-bearing:
-- it is what lets a repeated sync prove idempotency rather than assert it. The
-- second attempt raises IntegrityError, which LocalCRMSync catches and
-- reports as already_synced with the original record ID.

CREATE TABLE IF NOT EXISTS crm_local_contacts (
    id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT NOT NULL,
    email TEXT,
    title TEXT,
    account_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm_local_deals (
    id TEXT PRIMARY KEY,
    contact_id TEXT,
    name TEXT NOT NULL,
    amount REAL,
    stage_name TEXT,
    close_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES crm_local_contacts(id)
);

CREATE TABLE IF NOT EXISTS crm_local_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    target TEXT NOT NULL,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
