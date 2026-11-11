# Acceptance Test Matrix

Jalankan seluruh test:

```bash
python3 -m unittest discover -s tests -v
```

## Matriks AC PRD

| Test ID | Given | When | Then | Test otomatis |
| --- | --- | --- | --- | --- |
| AC-02A | Slot tersedia & akun valid | Konfirmasi reservasi | Status `confirmed` & ID diterbitkan | `test_booking_confirmed_issues_qr_and_public_verify` |
| AC-02B | Slot tersedia, 2 akun valid | 2 request bersamaan | Tepat 1 `confirmed`, 1 gagal/konflik | `test_concurrent_requests_exactly_one_confirmed`, `test_second_request_on_same_slot_gets_failed_status` |
| AC-02D | Reservasi sukses terbentuk | Konfirmasi diulang (double click) | Duplikasi diabaikan, 0 double booking | `test_double_click_does_not_create_duplicate` |
| AC-05A | Reservasi milik mahasiswa A | Mahasiswa B mencoba membatalkan | Akses ditolak, status tetap `confirmed` | `test_other_student_cannot_cancel_reservation` |

## Business rule coverage

| Rule | Skenario | Test |
| --- | --- | --- |
| BR-01 | `mulai = selesai` ditolak | `test_equal_start_and_end_is_rejected` |
| BR-01 | `mulai > selesai` ditolak | `test_invalid_time_is_rejected` |
| BR-01 | Waktu mulai lewat ditolak | `test_booking_in_the_past_is_rejected` |
| BR-02 | Overlap dua request | `test_second_request_on_same_slot_gets_failed_status` |
| BR-02 | Konkurensi nyata (barrier + 2 thread) | `test_concurrent_requests_exactly_one_confirmed` |
| BR-03 | Pemilik membatalkan sebelum mulai | `test_owner_cancel_reopens_slot` |
| BR-03 | Bukan pemilik tidak dapat membatalkan | `test_other_student_cannot_cancel_reservation` |
| BR-03 | Alasan pembatalan wajib | `test_cancel_requires_reason` |
| BR-04 | Audit mencatat aktor, waktu, alasan | `test_audit_log_records_actor_time_and_reason` |

## Fitur pendukung

| Fitur | Test |
| --- | --- |
| Pencarian menampilkan 28 ruang | `test_search_page_lists_all_rooms` |
| Registrasi & login | `test_registration_and_login` |
| QR Code bukti peminjaman | `test_booking_confirmed_issues_qr_and_public_verify` |
| Verifikasi publik tanpa email | `test_booking_confirmed_issues_qr_and_public_verify` |
| Aula wajib dokumen + approval Sarpras | `test_aula_requires_document_and_sarpras_approval` |
| Aturan akses area admin | `test_non_admin_cannot_open_admin` |
| Pengelolaan aturan ruang + audit | `test_sarpras_can_update_room_rules_and_audit` |

## Manual smoke test

1. Buka `/`, pilih tanggal besok, jam 09:00–11:00, lalu pesan **R Lecture** sebagai mahasiswa.
2. Buka halaman detail — status **Terkonfirmasi**, QR tampil, tombol cetak berfungsi.
3. Buka tautan verifikasi di tab privat — bukti valid, email tidak ditampilkan.
4. Login akun dosen dan coba pesan slot yang sama — status **Gagal / Konflik** dengan alasan.
5. Login Sarpras → **Kelola Sarpras** → setujui/tolak antrean, cek **Audit log**.
6. Pesan **Aula** sebagai mahasiswa tanpa dokumen → ditolak. Ulangi dengan dokumen → status **Menunggu Verifikasi**. Setujui sebagai Sarpras → **Terkonfirmasi**.
7. Batalkan reservasi milik sendiri sebelum mulai → slot kembali muncul pada pencarian.
