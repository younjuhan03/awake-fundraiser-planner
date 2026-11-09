-- AWAKE fundraiser planner: SQLite schema.
-- Privacy: no names or phone numbers anywhere. Orders are keyed by order_id only.

DROP TABLE IF EXISTS events;
CREATE TABLE events (
    event_id            TEXT PRIMARY KEY,          -- F24, S25, S26
    label               TEXT NOT NULL,
    semester            TEXT NOT NULL,
    event_date          TEXT,                      -- ISO date; NULL if not recorded
    status              TEXT NOT NULL CHECK (status IN ('observed','partial')),
    notes               TEXT,
    ledger_memo_net_usd REAL                       -- net profit quoted in the ledger memo (F24 only)
);

DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
    txn_id          INTEGER PRIMARY KEY,
    date            TEXT NOT NULL,
    amount_usd      REAL NOT NULL,                 -- negative = expense
    description     TEXT NOT NULL,                 -- translated from Korean
    event_id        TEXT NOT NULL REFERENCES events(event_id),
    category        TEXT NOT NULL CHECK (category IN
                      ('revenue','ingredients','supplies','printing','market_research','unplanned')),
    units_purchased INTEGER                        -- only where the description states item counts (S25 ramen)
);

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    order_id   TEXT PRIMARY KEY,
    timestamp  TEXT NOT NULL,                      -- 'YYYY-MM-DD HH:MM:SS', timezone not recorded
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    amount_usd REAL NOT NULL,
    event_id   TEXT NOT NULL REFERENCES events(event_id)
);

DROP TABLE IF EXISTS unit_costs;
CREATE TABLE unit_costs (
    item          TEXT PRIMARY KEY,
    cost_usd      REAL,
    pack_size     INTEGER,
    unit_cost_usd REAL,
    source        TEXT,
    confidence    TEXT,
    note          TEXT
);

DROP TABLE IF EXISTS assumptions;
CREATE TABLE assumptions (
    key        TEXT PRIMARY KEY,
    value      REAL NOT NULL,
    source     TEXT NOT NULL,
    confidence TEXT NOT NULL CHECK (confidence IN ('observed','derived','assumed')),
    note       TEXT NOT NULL
);

DROP TABLE IF EXISTS ledger_budget;
CREATE TABLE ledger_budget (
    event_id   TEXT NOT NULL REFERENCES events(event_id),
    line       TEXT NOT NULL,
    budget_usd REAL NOT NULL,
    actual_usd REAL NOT NULL
);
