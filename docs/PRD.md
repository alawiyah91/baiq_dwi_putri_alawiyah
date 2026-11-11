# PRD Implementation Notes — IDB Bali Release 1.0

Sumber: *Product Requirement Document (PRD) Sistem Informasi Peminjaman Ruangan Kampus IDB Bali — Release 1.0, SVPG Standards*. Dokumen ini merangkum requirement yang diimplementasikan pada repository.

## 1. Tujuan produk

Mahasiswa dan dosen IDB Bali harus dapat menemukan ruang yang benar-benar tersedia dan mendapatkan kepastian reservasi tanpa konfirmasi manual. Baseline: konfirmasi 20 menit dan 42% transaksi gagal. Target Release 1.0:

| Tujuan | Target | Implementasi |
| --- | --- | --- |
| Reservasi berhasil tanpa bantuan | ≥ 85% | Alur pencarian → pilih slot → isi form → konfirmasi, tanpa langkah manual |
| Waktu konfirmasi status | ≤ 2 menit | Alokasi dilakukan langsung dalam transaksi database |
| Konflik / double booking | 0 | `BEGIN IMMEDIATE` + write lock + cek overlap atomik |

## 2. Persona & prinsip

- **Rani (mahasiswa/UKM/HIMA)** — memesan ruang lewat ponsel, ingin kepastian tanpa bertanya berulang.
- **Dedi (Petugas Sarpras)** — mengelola 28 ruang, mencegah bentrok, mencatat alasan pembatalan, menangani kasus khusus.
- Prinsip: **Status Integrity**, **Frictionless Booking**, **Data Privacy**.

## 3. Scope

### In-scope (diterapkan)
- Pencarian slot berdasarkan tanggal, jam, gedung, kapasitas, kategori, kata kunci.
- Reservasi 1 slot eksklusif tanpa konflik (FR-02, BR-02).
- Konfirmasi status real-time: `processing`, `confirmed`, `failed`, `cancelled` (FR-03).
- Pembatalan mandiri sebelum mulai (FR-05, BR-03).
- Dashboard verifikasi & approval Sarpras.
- Bukti peminjaman QR + verifikasi publik.
- Audit log aktor/waktu/alasan (BR-04).
- Pengelolaan aturan ruang oleh Sarpras (dokumen, approval, area terbatas, kapasitas, aktif).

### Out-of-scope (tidak dibuat)
Pembayaran/sewa, reservasi inter-kampus, rekomendasi AI, peta 3D/VR, dan IoT smart lock. Tidak ada endpoint atau UI untuk fitur tersebut.

## 4. Master data

Total **28 ruang/fasilitas** dari PRD, terdiri dari:

- **Gedung A — Jl. Tukad Batanghari No. 29 (19 entri)**: A.1.1–A.1.4, B.1.1–B.1.4, A.2.1–A.2.4, B.2.1–B.2.2, Kantin, Musholla, Perpustakaan, Ruang Asistensi, Aula.
- **Gedung A Barito — Jl. Tukad Barito No. 5X (9 entri)**: C.1.1–C.1.2, Ruang Dosen & Admin, C.2.1–C.2.3, C.3.1–C.3.3.

Aturan khusus:
- Lab Komputer, Lab iMac, Studio Foto, Studio Pola, Studio Praktikum Desain, Lab Fashion, dan Aula memiliki flag **wajib dokumen**.
- Aula memiliki flag **wajib approval Sarpras** sehingga status awal `processing`.
- UKS dan Ruang Dosen & Administrasi memiliki flag **area terbatas**; hanya Sarpras/Super Admin yang dapat mengakses form pemesanan.

## 5. Peran & hak akses

| Aksi | Mahasiswa | Dosen/Staf | Sarpras | Super Admin |
| --- | --- | --- | --- | --- |
| Melihat jadwal & slot | Ya | Ya | Ya | Ya |
| Membuat reservasi | Diri sendiri | Diri/kelas | Sesuai wewenang | Bypass |
| Membatalkan | Milik sendiri sebelum mulai | Milik sendiri sebelum mulai | Dengan alasan + audit | Dengan alasan + audit |
| Approval / aturan ruang | Tidak | Tidak | Ya | Ya |

Implementasi peran menggunakan session Flask dan decorator `roles_required("sarpras", "superadmin")` untuk area admin.

## 6. Business rules

- **BR-01** — `mulai < selesai` divalidasi di server; `mulai = selesai` atau terbalik ditolak. Ditambah validasi waktu mulai tidak boleh lewat dan jam operasional 06:00–23:00.
- **BR-02** — Reservasi aktif (`processing`/`confirmed`) tidak boleh overlap pada ruang dan tanggal yang sama. Dua request simultan: tepat satu sukses. Permintaan kalah dicatat sebagai `failed` dengan alasan konflik.
- **BR-03** — Pembatalan hanya oleh pemilik (atau Sarpras) dan hanya sebelum `tanggal + mulai`. Alasan wajib.
- **BR-04** — Setiap perubahan status dan aturan ruang dicatat di `audit_logs` (aktor, waktu, aksi, detail/alasan).

## 7. User flow & state

```
Cari slot (FR-01)
   → Submit request
   → BEGIN IMMEDIATE + cek konflik
   → confirmed (langsung) atau processing (butuh approval)
   → cancelled (pembatalan sebelum mulai)
   → failed (konflik / ditolak)
```

Status `processing` menahan slot secara eksklusif hingga diputuskan Sarpras. Approval melakukan pengecekan konflik ulang sebelum mengubah status menjadi `confirmed`.

## 8. Traceability FR → implementasi

| FR | Implementasi |
| --- | --- |
| FR-01 Cari Slot | `GET /` — filter tanggal/jam/gedung/kapasitas/kategori/q, penanda slot terpakai |
| FR-02 Reservasi Eksklusif | `POST /book/<room_id>` — validasi, duplikasi, transaksi `BEGIN IMMEDIATE`, cek overlap |
| FR-03 Konfirmasi Real-Time | Status langsung dirender pada halaman detail; QR hanya untuk `confirmed` |
| FR-04 Alokasi Transaksional | Write lock proses + transaksi SQLite + audit konflik |
| FR-05 Pembatalan Mandiri | `POST /reservations/<id>/cancel` — kepemilikan, batas waktu, alasan, audit |

## 9. Release criteria

- Performa: query pencarian memakai indeks `(room_id, tanggal, status, mulai, selesai)`.
- Skalabilitas: arsitektur single-process SQLite untuk demo; catatan migrasi ke PostgreSQL ada di `docs/DATA.md`.
- Usability: mobile-first, form minimal, status jelas, aksesibilitas dasar (label, fokus, ARIA navigasi).
