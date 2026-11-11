# Model Data, Relasi, dan Guardrail Transaksi

## 1. Entitas

### `users`
| Kolom | Tipe | Keterangan |
| --- | --- | --- |
| id | INTEGER PK | |
| nama | TEXT | |
| email | TEXT UNIQUE | login |
| password_hash | TEXT | PBKDF2-SHA256 |
| role | TEXT | `mahasiswa`, `dosen`, `sarpras`, `superadmin` |
| nim_nip | TEXT | identitas kampus |
| created_at | TEXT | waktu lokal |

Relasi: 1 pengguna → banyak reservasi (1:N).

### `rooms`
| Kolom | Tipe | Keterangan |
| --- | --- | --- |
| id | INTEGER PK | |
| kode | TEXT UNIQUE | contoh `A.1.1` |
| nama, gedung, lantai, kategori | TEXT/INTEGER | master data PRD |
| kapasitas | INTEGER | default dan validasi form |
| butuh_dokumen | INTEGER 0/1 | wajib upload dokumen |
| butuh_approval | INTEGER 0/1 | status awal `processing` |
| terbatas | INTEGER 0/1 | hanya Sarpras |
| aktif | INTEGER 0/1 | tampil di pencarian |

Relasi: 1 ruang → banyak reservasi (1:N).

### `reservations`
| Kolom | Tipe | Keterangan |
| --- | --- | --- |
| id | INTEGER PK | |
| kode_booking | TEXT UNIQUE | `IDB-YYMMDD-XXXXXX` |
| user_id | FK users.id | pemohon |
| room_id | FK rooms.id | ruang |
| tanggal | TEXT `YYYY-MM-DD` | |
| mulai, selesai | TEXT `HH:MM` | `CHECK (mulai < selesai)` |
| status | TEXT | `processing`, `confirmed`, `failed`, `cancelled` |
| keperluan | TEXT | minimal 10 karakter |
| jumlah_peserta | INTEGER | ≤ kapasitas ruang |
| dokumen | TEXT | nama file acak di `uploads/` |
| alasan_gagal / alasan_batal | TEXT | terlihat pemohon |
| approved_by / approved_at | FK users.id / TEXT | jejak approval |
| created_at / updated_at | TEXT | waktu lokal |

### `audit_logs`
| Kolom | Tipe | Keterangan |
| --- | --- | --- |
| id | INTEGER PK | |
| reservation_id | FK nullable | null untuk perubahan aturan ruang |
| actor_id | FK users.id | |
| action | TEXT | `booking_created`, `booking_failed`, `reservation_approved`, `approval_failed`, `reservation_rejected`, `reservation_cancelled`, `room_updated` |
| detail | TEXT | alasan / ringkasan perubahan |
| created_at | TEXT | |

## 2. Aturan integritas

1. **Tidak ada overlap** untuk `status IN ('processing','confirmed')`:
   ```
   NOT (selesai <= :mulai OR mulai >= :selesai)
   ≡ mulai < :selesai AND selesai > :mulai
   ```
2. **Validasi server** (bukan hanya HTML): BR-01, kapasitas, tanggal, jam operasional, dokumen wajib.
3. **Duplikasi klik ganda**: dicek di dalam transaksi berdasarkan `user_id, room_id, tanggal, mulai, selesai` dan status aktif. Bila ada, pengguna diarahkan ke reservasi yang sudah ada dan tidak membuat baris baru.
4. **Konflik**: request yang kalah tetap dicatat sebagai `failed` (bukan dihapus) agar dapat diaudit dan memenuhi AC-02B.
5. **Pembatalan** mengubah status menjadi `cancelled`, sehingga slot otomatis kembali tersedia pada query ketersediaan.

## 3. Implementasi transaksi (BR-02)

```python
_write_lock.acquire()
try:
    db.execute("BEGIN IMMEDIATE")        # kunci tulis SQLite segera
    duplicate = ...                      # cek klik ganda
    conflict = slot_conflict(...)        # cek overlap
    insert reservation / failed record
    log_audit(...)
    db.commit()
except Exception:
    db.rollback()
    raise
finally:
    _write_lock.release()
```

Konfigurasi koneksi: `timeout=30`, `PRAGMA busy_timeout=30000`, `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`.

Mengapa `BEGIN IMMEDIATE`: SQLite default menunda lock hingga operasi tulis. Dua request dapat sama-sama lolos pengecekan konflik sebelum salah satu menulis. `BEGIN IMMEDIATE` mengambil reserved lock lebih awal sehingga pengecekan dan penulisan menjadi satu unit serial. Write lock proses menambahkan serialisasi untuk request dalam satu proses Flask.

### Catatan deployment multi-proses

SQLite + `threading.Lock` hanya menjamin serialisasi dalam satu proses. Untuk produksi multi-worker/multi-instance:
- gunakan PostgreSQL/MySQL,
- gunakan row-level lock `SELECT ... FOR UPDATE` pada ruang/slot,
- atau PostgreSQL exclusion constraint (`tsrange` + `EXCLUDE USING gist`) untuk menjamin non-overlap di level database,
- pertahankan audit log append-only.

## 4. Indeks

- `idx_reservations_slot (room_id, tanggal, status, mulai, selesai)` — pencarian ketersediaan dan cek konflik.
- `idx_reservations_user (user_id, tanggal)` — dashboard pengguna.
- `idx_audit_reservation (reservation_id)` — timeline audit.

## 5. Privasi data

- Halaman verifikasi publik hanya menampilkan nama, ruang, waktu, status, dan kode booking; email/NIM tidak ditampilkan.
- Dokumen pendukung hanya dapat diunduh oleh pemilik reservasi atau Sarpras/Super Admin.
- Dosen tidak dapat melihat reservasi pribadi mahasiswa lain dari dashboard pribadi; data operasional tersedia di area Sarpras sesuai wewenang.
