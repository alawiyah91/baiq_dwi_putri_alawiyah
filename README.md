# IDB Bali — Sistem Peminjaman Ruangan Kampus IDB Bali

Implementasi web untuk PRD **Sistem Informasi Peminjaman Ruangan Kampus IDB Bali — Release 1.0**. Aplikasi mencakup pencarian slot, reservasi eksklusif tanpa double booking, approval Sarpras, pembatalan mandiri, bukti QR, audit log, dan pengelolaan aturan ruang.

## Menjalankan aplikasi

```bash
# 1. (Opsional) buat virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Pasang dependensi
pip install -r requirements.txt

# 3. Jalankan
python3 app.py
# atau tentukan port lain: PORT=9000 python3 app.py
```

Buka **http://127.0.0.1:8080**. Server berjalan di `0.0.0.0`, jadi perangkat lain pada jaringan yang sama dapat membuka **http://<IP-komputer>:8080**.

Cari IP lokal komputer:

```bash
ipconfig getifaddr en0 || ipconfig getifaddr en1
```

Aktifkan debug hanya untuk lokal: `FLASK_DEBUG=1 python3 app.py`.

Database SQLite dan 28 ruangan contoh dibuat otomatis saat aplikasi pertama kali dijalankan (`instance/idb_rooms.db`). Untuk mereset data demo, hentikan server lalu hapus folder `instance/` dan isi `uploads/` (kecuali `.gitkeep`).

### Akun demo

| Peran | Email | Kata sandi |
| --- | --- | --- |
| Mahasiswa | `mahasiswa@idb.ac.id` | `demo123` |
| Dosen / Staf | `dosen@idb.ac.id` | `demo123` |
| Petugas Sarpras | `sarpras@idb.ac.id` | `demo123` |
| Super Admin | `superadmin@idb.ac.id` | `demo123` |

## Fitur Release 1.0

- **Pencarian slot** berdasarkan tanggal, rentang jam, gedung, kapasitas, kategori, dan kata kunci.
- **Reservasi eksklusif** dengan transaksi `BEGIN IMMEDIATE` + write lock; dua permintaan pada slot yang sama menghasilkan tepat satu `confirmed` dan satu `failed`.
- **Alur status** `processing → confirmed / failed` dan `cancelled`, dengan validasi `mulai < selesai` (BR-01).
- **Aturan ruang**: ruang lab/studio tertentu mewajibkan dokumen; Aula memerlukan approval Sarpras; UKS dan Ruang Dosen dikecualikan dari peminjaman rutin.
- **Pembatalan mandiri** hanya oleh pemilik dan sebelum waktu mulai (BR-03), dengan alasan wajib.
- **Dashboard Sarpras**: antrean verifikasi, approval/penolakan, pembatalan dengan alasan, filter reservasi, dan utilization ruang.
- **Audit log** mencatat aktor, waktu, aksi, dan alasan untuk setiap perubahan status (BR-04).
- **Bukti peminjaman QR** + halaman verifikasi publik yang membatasi data pribadi.
- **Pengelolaan aturan ruang** oleh Sarpras/Super Admin.
- UI responsif untuk ponsel dan desktop, tanpa framework frontend.

## Test

```bash
python3 -m unittest discover -s tests -v
```

Test suite mencakup BR-01, BR-02 (termasuk request konkuren), BR-03, BR-04, approval Aula, QR, verifikasi publik, dan skenario AC-02A/AC-02B/AC-02D/AC-05A.

## Struktur proyek

```
app.py                 # routes, validasi, transaksi reservasi, QR, audit
schema.sql             # skema SQLite
templates/             # Jinja: publik, auth, user, admin, bukti, verifikasi
static/css/style.css   # desain responsif
static/js/app.js       # navigasi, toast, upload label, print, time helper
tests/test_app.py      # test suite
docs/PRD.md            # ringkasan requirement & traceability
docs/DATA.md           # model data, business rules, guardrail transaksi
docs/ACCEPTANCE.md     # matriks acceptance + test
AGENTS.md              # instruksi untuk AI code agent berikutnya
```

## Catatan implementasi

- Database: SQLite dengan WAL, `busy_timeout`, `BEGIN IMMEDIATE`, dan `threading.Lock` proses-level. Untuk deployment multi-proses, gunakan PostgreSQL/MySQL dan row-level locking (`SELECT ... FOR UPDATE`) atau constraint eksklusi.
- Autentikasi: session cookie Flask yang ditandatangani, password PBKDF2-SHA256 (kompatibel dengan Python 3.9 tanpa OpenSSL scrypt).
- Dokumen pendukung disimpan di `uploads/` dan hanya dapat diunduh pemilik reservasi atau Sarpras.
- Aplikasi ini adalah demo fungsional Release 1.0; belum mencakup pembayaran, AI recommendation, peta 3D, atau integrasi IoT sesuai out-of-scope PRD.
