PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nama            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('mahasiswa', 'dosen', 'sarpras', 'superadmin')),
    nim_nip         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS rooms (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    kode                TEXT NOT NULL UNIQUE,
    nama                TEXT NOT NULL,
    gedung              TEXT NOT NULL,
    lantai              INTEGER NOT NULL,
    kapasitas           INTEGER NOT NULL DEFAULT 20,
    kategori            TEXT NOT NULL,
    deskripsi           TEXT,
    butuh_dokumen       INTEGER NOT NULL DEFAULT 0,
    butuh_approval      INTEGER NOT NULL DEFAULT 0,
    terbatas            INTEGER NOT NULL DEFAULT 0,
    aktif               INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS reservations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_booking    TEXT NOT NULL UNIQUE,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    room_id         INTEGER NOT NULL REFERENCES rooms(id),
    tanggal         TEXT NOT NULL,
    mulai           TEXT NOT NULL,
    selesai         TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('processing', 'confirmed', 'failed', 'cancelled')),
    keperluan       TEXT NOT NULL,
    jumlah_peserta  INTEGER NOT NULL DEFAULT 1,
    dokumen         TEXT,
    alasan_gagal    TEXT,
    alasan_batal    TEXT,
    approved_by     INTEGER REFERENCES users(id),
    approved_at     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CHECK (mulai < selesai)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id  INTEGER REFERENCES reservations(id),
    actor_id        INTEGER REFERENCES users(id),
    action          TEXT NOT NULL,
    detail          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_reservations_slot
    ON reservations (room_id, tanggal, status, mulai, selesai);

CREATE INDEX IF NOT EXISTS idx_reservations_user
    ON reservations (user_id, tanggal);

CREATE INDEX IF NOT EXISTS idx_audit_reservation
    ON audit_logs (reservation_id);
