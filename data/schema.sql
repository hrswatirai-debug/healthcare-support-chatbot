-- ============================================================
-- Healthcare Equipment Support Chatbot — SQL schema (SQLite)
-- Structured data for: users, equipment, orders, warranty/AMC,
-- complaints, invoices, spare parts.
-- All customer-facing tables carry client_id for row scoping.
-- ============================================================

PRAGMA foreign_keys = ON;

-- Customers / hospitals and their login identity ------------
CREATE TABLE IF NOT EXISTS users (
    client_id       TEXT PRIMARY KEY,          -- e.g. CLI-1001
    email           TEXT NOT NULL UNIQUE,
    org_name        TEXT NOT NULL,             -- hospital / clinic name
    contact_name    TEXT,
    phone           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Catalogue of equipment models ----------------------------
CREATE TABLE IF NOT EXISTS equipment (
    equipment_id    TEXT PRIMARY KEY,          -- e.g. EQ-MRI-15T
    model_name      TEXT NOT NULL,
    category        TEXT NOT NULL,             -- MRI / CT / Ultrasound / Monitor ...
    manufacturer    TEXT NOT NULL,
    manual_doc      TEXT,                      -- filename in data/docs
    list_price_usd  REAL
);

-- Orders placed by a client for equipment ------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id        TEXT PRIMARY KEY,          -- e.g. ORD-4402
    client_id       TEXT NOT NULL REFERENCES users(client_id),
    equipment_id    TEXT NOT NULL REFERENCES equipment(equipment_id),
    quantity        INTEGER NOT NULL DEFAULT 1,
    order_date      TEXT NOT NULL,
    status          TEXT NOT NULL,             -- Processing/Shipped/In Transit/Delivered/Delayed
    est_delivery    TEXT,
    tracking_no     TEXT,
    notes           TEXT
);

-- Warranty and Annual Maintenance Contract ------------------
CREATE TABLE IF NOT EXISTS warranty_amc (
    contract_id     TEXT PRIMARY KEY,          -- e.g. WAR-9001
    client_id       TEXT NOT NULL REFERENCES users(client_id),
    order_id        TEXT REFERENCES orders(order_id),
    equipment_id    TEXT NOT NULL REFERENCES equipment(equipment_id),
    warranty_start  TEXT,
    warranty_end    TEXT,
    amc_plan        TEXT,                      -- None/Basic/Standard/Premium
    amc_status      TEXT,                      -- Active/Expired/NotEnrolled
    amc_end         TEXT
);

-- Complaints / service tickets -----------------------------
CREATE TABLE IF NOT EXISTS complaints (
    ticket_id       TEXT PRIMARY KEY,          -- e.g. TIC-7001
    client_id       TEXT NOT NULL REFERENCES users(client_id),
    equipment_id    TEXT REFERENCES equipment(equipment_id),
    subject         TEXT NOT NULL,
    priority        TEXT,                      -- Low/Medium/High/Critical
    status          TEXT NOT NULL,             -- Open/In Progress/Escalated/Resolved
    created_at      TEXT NOT NULL,
    updated_at      TEXT,
    assigned_team   TEXT
);

-- Invoices and payments ------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id      TEXT PRIMARY KEY,          -- e.g. INV-3001
    client_id       TEXT NOT NULL REFERENCES users(client_id),
    order_id        TEXT REFERENCES orders(order_id),
    amount_usd      REAL NOT NULL,
    issued_date     TEXT NOT NULL,
    due_date        TEXT,
    status          TEXT NOT NULL,             -- Paid/Unpaid/Overdue/Refunded
    pdf_link        TEXT
);

-- Spare parts inventory ------------------------------------
CREATE TABLE IF NOT EXISTS spare_parts (
    part_id         TEXT PRIMARY KEY,          -- e.g. SP-201
    part_name       TEXT NOT NULL,
    compatible_with TEXT,                      -- equipment_id or category
    in_stock        INTEGER NOT NULL DEFAULT 0,
    unit_price_usd  REAL,
    lead_time_days  INTEGER
);

-- Audit log of every chatbot interaction -------------------
CREATE TABLE IF NOT EXISTS chat_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    client_id       TEXT,
    intent          TEXT,
    data_source     TEXT,                      -- SQL / RAG / FALLBACK / AUTH
    answered        INTEGER,                   -- 1/0
    latency_ms      INTEGER,
    message_preview TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_client   ON orders(client_id);
CREATE INDEX IF NOT EXISTS idx_warranty_client ON warranty_amc(client_id);
CREATE INDEX IF NOT EXISTS idx_complaints_client ON complaints(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_client ON invoices(client_id);
