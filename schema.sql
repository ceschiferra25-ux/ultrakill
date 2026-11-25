-- ULTRAKILL Guide database schema (SQLite).
-- Recreated from scratch by `python init_db.py`.

DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS entries;
DROP TABLE IF EXISTS admins;

-- One row per enemy or boss shown in the guide.
CREATE TABLE entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    category        TEXT    NOT NULL CHECK (category IN ('boss', 'enemy')),
    faction         TEXT    NOT NULL CHECK (faction IN ('Husks', 'Machines', 'Demons', 'Angels', 'Other', 'Prime Souls')),
    is_cyber_grind  INTEGER NOT NULL DEFAULT 0 CHECK (is_cyber_grind IN (0, 1)),
    is_secret       INTEGER NOT NULL DEFAULT 0 CHECK (is_secret IN (0, 1)),
    lore            TEXT    NOT NULL,
    attack_patterns TEXT    NOT NULL,
    weaknesses      TEXT    NOT NULL,
    strategies      TEXT    NOT NULL,
    image           TEXT,              -- optional file name in static/images/enemies/
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Community tips attached to an entry; deleted together with it.
CREATE TABLE comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id   INTEGER NOT NULL REFERENCES entries (id) ON DELETE CASCADE,
    author     TEXT    NOT NULL,
    message    TEXT    NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_comments_entry ON comments (entry_id);

-- Administrators. Passwords are stored only as salted hashes (werkzeug.security).
CREATE TABLE admins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
