# AGENTS.md — IDB Bali

Panduan wajib untuk AI code agent yang bekerja pada repository ini.

## Konteks produk

Aplikasi Flask + SQLite untuk **Sistem Peminjaman Ruangan Kampus IDB Bali Release 1.0**. Baca `docs/PRD.md`, `docs/DATA.md`, dan `docs/ACCEPTANCE.md` sebelum mengubah alur reservasi.

## Aturan yang tidak boleh dilanggar

1. **BR-01** — Server wajib menolak `mulai >= selesai`; jangan hanya mengandalkan validasi HTML.
2. **BR-02** — Cek konflik dan insert reservasi harus berada dalam satu transaksi `BEGIN IMMEDIATE` di bawah `_write_lock`. Jangan memindahkan pengecekan konflik ke luar transaksi.
3. **BR-03** — Pembatalan hanya oleh pemilik/Sarpras, hanya sebelum `tanggal + mulai`, dan alasan wajib.
4. **BR-04** — Setiap perubahan status reservasi dan aturan ruang wajib memanggil `log_audit` dengan aktor, aksi, dan alasan/detail.
5. **Status integrity** — Jangan menandai reservasi `confirmed` jika alokasi eksklusif belum berhasil. Jangan menghapus baris `failed`; baris tersebut bagian dari audit konflik.
6. **Data privacy** — Jangan menampilkan email/NIM pada halaman verifikasi publik. Dokumen hanya untuk pemilik atau Sarpras/Super Admin.
7. **Jangan mengubah struktur tabel tanpa approval** dan **jangan menghapus test yang sudah ada**. Tambahkan test baru untuk perubahan perilaku.
8. Jangan menambahkan fitur out-of-scope PRD (pembayaran, AI, peta 3D, IoT) tanpa persetujuan.

## Alur kerja yang diharapkan

- Baca kode terkait (`app.py`, schema, template) sebelum mengedit.
- Pertahankan gaya kode dan nama Indonesia yang sudah dipakai.
- Setelah perubahan, jalankan:

```bash
python3 -m unittest discover -s tests -v
```

- Untuk perubahan UI, lakukan smoke test route `/`, `/login`, `/dashboard`, `/admin`, `/admin/reservations`, `/admin/audit`, `/admin/rooms`, dan halaman detail reservasi.
- Laporkan file yang diubah dan hasil test suite.

## Struktur penting

| Path | Isi |
| --- | --- |
| `app.py` | Semua route, validasi, transaksi, QR, audit |
| `schema.sql` | Skema SQLite + indeks |
| `templates/` | Jinja templates |
| `static/css/style.css` | Design system dan responsif |
| `tests/test_app.py` | Regression + acceptance tests |
| `instance/idb_rooms.db` | Database runtime (ignored) |
| `uploads/` | Dokumen pendukung (ignored, kecuali `.gitkeep`) |

## Akun demo

`mahasiswa@idb.ac.id`, `dosen@idb.ac.id`, `sarpras@idb.ac.id`, `superadmin@idb.ac.id` — password `demo123`.
