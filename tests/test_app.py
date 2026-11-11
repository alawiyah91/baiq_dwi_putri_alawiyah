import io
import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import date, datetime, time, timedelta

from app import create_app


class IDBSpaceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": os.path.join(self.temp.name, "test.db"),
                "UPLOAD_DIR": os.path.join(self.temp.name, "uploads"),
            }
        )
        self.day = (date.today() + timedelta(days=2)).isoformat()

    def tearDown(self):
        self.temp.cleanup()

    # -- helpers ---------------------------------------------------------
    def client(self):
        return self.app.test_client()

    def login(self, client, email="mahasiswa@idb.ac.id", password="demo123"):
        return client.post(
            "/login",
            data={"email": email, "password": password},
            follow_redirects=True,
        )

    def register(self, client, name, email, role="mahasiswa"):
        return client.post(
            "/register",
            data={
                "nama": name,
                "email": email,
                "nim_nip": "22109999",
                "role": role,
                "password": "secret123",
                "confirm": "secret123",
            },
            follow_redirects=True,
        )

    def room_id(self, kode):
        db = sqlite3.connect(self.app.config["DATABASE"])
        try:
            row = db.execute("SELECT id FROM rooms WHERE kode = ?", (kode,)).fetchone()
            return row[0]
        finally:
            db.close()

    def book(self, client, kode, mulai="09:00", selesai="11:00", day=None,
             purpose="Diskusi kelompok untuk proyek desain", peserta=6, doc=None):
        data = {
            "tanggal": day or self.day,
            "mulai": mulai,
            "selesai": selesai,
            "keperluan": purpose,
            "jumlah_peserta": peserta,
        }
        if doc:
            data["dokumen"] = doc
        return client.post(
            f"/book/{self.room_id(kode)}",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    def reservation_rows(self, kode=None):
        db = sqlite3.connect(self.app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        try:
            if kode:
                return db.execute(
                    """SELECT r.* FROM reservations r JOIN rooms rm ON rm.id = r.room_id
                       WHERE rm.kode = ? ORDER BY r.id""",
                    (kode,),
                ).fetchall()
            return db.execute("SELECT * FROM reservations ORDER BY id").fetchall()
        finally:
            db.close()

    def reservation_id_from(self, response):
        marker = b"/reservations/"
        text = response.data
        index = text.find(marker)
        self.assertNotEqual(index, -1, "Halaman harus memuat tautan detail reservasi")
        tail = text[index + len(marker):]
        digits = b""
        for byte in tail:
            char = bytes([byte])
            if not char.isdigit():
                break
            digits += char
        return int(digits)

    # -- public & auth ---------------------------------------------------
    def test_search_page_lists_all_rooms(self):
        response = self.client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Studio Pola", response.data)
        self.assertIn(b"Ruang Dosen", response.data)
        self.assertEqual(response.data.count(b'<article class="room-card'), 28)

    def test_non_admin_cannot_open_admin(self):
        client = self.client()
        self.login(client)
        self.assertEqual(client.get("/admin").status_code, 403)

    def test_registration_and_login(self):
        client = self.client()
        response = self.register(client, "Budi Santana", "budi@idb.ac.id")
        self.assertIn(b"Halo, Budi", response.data)
        client.post("/logout")
        response = self.login(client, "budi@idb.ac.id", "secret123")
        self.assertIn(b"Halo, Budi", response.data)

    # -- FR-01 / FR-02 / BR-01 / AC-02A ---------------------------------
    def test_booking_confirmed_issues_qr_and_public_verify(self):
        client = self.client()
        self.login(client)
        response = self.book(client, "A.1.2")
        self.assertIn(b"Slot berhasil dialokasikan", response.data)
        self.assertIn(b"Terkonfirmasi", response.data)

        rows = self.reservation_rows("A.1.2")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "confirmed")
        self.assertTrue(rows[0]["kode_booking"].startswith("IDB-"))

        reservation_id = rows[0]["id"]
        qr = client.get(f"/reservations/{reservation_id}/qr.png")
        self.assertEqual(qr.status_code, 200)
        self.assertEqual(qr.mimetype, "image/png")

        verify = self.client().get(f"/verify/{rows[0]['kode_booking']}")
        self.assertEqual(verify.status_code, 200)
        self.assertIn(b"Bukti reservasi valid", verify.data)
        self.assertNotIn(b"mahasiswa@idb.ac.id", verify.data)

    def test_invalid_time_is_rejected(self):
        client = self.client()
        self.login(client)
        response = self.book(client, "A.1.2", mulai="11:00", selesai="09:00")
        self.assertIn(b"Jam mulai harus lebih awal", response.data)
        self.assertEqual(len(self.reservation_rows()), 0)

    def test_equal_start_and_end_is_rejected(self):
        client = self.client()
        self.login(client)
        response = self.book(client, "A.1.2", mulai="10:00", selesai="10:00")
        self.assertIn(b"Jam mulai harus lebih awal", response.data)
        self.assertEqual(len(self.reservation_rows()), 0)

    def test_booking_in_the_past_is_rejected(self):
        client = self.client()
        self.login(client)
        response = self.book(client, "A.1.2", day="2020-01-01")
        self.assertIn(b"Waktu mulai reservasi sudah terlewat", response.data)
        self.assertEqual(len(self.reservation_rows()), 0)

    # -- BR-02 / AC-02B / AC-02D ----------------------------------------
    def test_second_request_on_same_slot_gets_failed_status(self):
        first = self.client()
        self.login(first)
        self.book(first, "A.1.2")

        second = self.client()
        self.register(second, "Sinta Dewi", "sinta@idb.ac.id")
        response = self.book(second, "A.1.2")
        self.assertIn(b"Maaf, slot tersebut baru saja dialokasikan", response.data)

        rows = self.reservation_rows("A.1.2")
        statuses = [row["status"] for row in rows]
        self.assertEqual(statuses.count("confirmed"), 1)
        self.assertEqual(statuses.count("failed"), 1)

    def test_concurrent_requests_exactly_one_confirmed(self):
        client_a = self.client()
        client_b = self.client()
        self.login(client_a)
        self.register(client_b, "Bayu Pratama", "bayu@idb.ac.id")

        barrier = threading.Barrier(2)
        results = []
        errors = []

        def attempt(client):
            try:
                barrier.wait(timeout=10)
                response = self.book(client, "A.1.3", doc=(io.BytesIO(b"%PDF-1.4 test"), "izin.pdf"))
                results.append(response.status_code)
            except Exception as exc:  # pragma: no cover - surfaced in assertion
                errors.append(exc)

        threads = [threading.Thread(target=attempt, args=(client_a,)),
                   threading.Thread(target=attempt, args=(client_b,))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertEqual(errors, [])
        self.assertEqual(results, [200, 200])

        rows = self.reservation_rows("A.1.3")
        statuses = [row["status"] for row in rows]
        self.assertEqual(statuses.count("confirmed"), 1)
        self.assertEqual(statuses.count("processing") + statuses.count("failed"), 1)
        self.assertEqual(len(rows), 2)

    def test_double_click_does_not_create_duplicate(self):
        client = self.client()
        self.login(client)
        self.book(client, "A.1.2")
        response = self.book(client, "A.1.2")
        self.assertIn(b"Tidak ada duplikasi dibuat", response.data)
        rows = self.reservation_rows("A.1.2")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "confirmed")

    # -- BR-03 / FR-05 / AC-05A -----------------------------------------
    def test_other_student_cannot_cancel_reservation(self):
        owner = self.client()
        self.login(owner)
        self.book(owner, "A.1.2")
        reservation = self.reservation_rows("A.1.2")[0]

        other = self.client()
        self.register(other, "Maya Lestari", "maya@idb.ac.id")
        response = other.post(
            f"/reservations/{reservation['id']}/cancel",
            data={"alasan": "Bukan milik saya"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.reservation_rows("A.1.2")[0]["status"], "confirmed")

    def test_owner_cancel_reopens_slot(self):
        owner = self.client()
        self.login(owner)
        self.book(owner, "A.1.2")
        reservation = self.reservation_rows("A.1.2")[0]
        response = owner.post(
            f"/reservations/{reservation['id']}/cancel",
            data={"alasan": "Jadwal kelas berubah"},
            follow_redirects=True,
        )
        self.assertIn(b"Reservasi dibatalkan", response.data)
        self.assertEqual(self.reservation_rows("A.1.2")[0]["status"], "cancelled")

        replacement = self.client()
        self.register(replacement, "Tia Kusuma", "tia@idb.ac.id")
        response = self.book(replacement, "A.1.2")
        self.assertIn(b"Slot berhasil dialokasikan", response.data)

    def test_cancel_requires_reason(self):
        owner = self.client()
        self.login(owner)
        self.book(owner, "A.1.2")
        reservation = self.reservation_rows("A.1.2")[0]
        response = owner.post(
            f"/reservations/{reservation['id']}/cancel",
            data={"alasan": ""},
            follow_redirects=True,
        )
        self.assertIn(b"Alasan pembatalan wajib diisi", response.data)
        self.assertEqual(self.reservation_rows("A.1.2")[0]["status"], "confirmed")

    # -- Approval & audit ------------------------------------------------
    def test_aula_requires_document_and_sarpras_approval(self):
        student = self.client()
        self.login(student)

        missing_doc = self.book(student, "Aula", purpose="Seminar nasional desain", peserta=120)
        self.assertIn(b"membutuhkan dokumen permohonan", missing_doc.data)
        self.assertEqual(len(self.reservation_rows("Aula")), 0)

        response = self.book(
            student, "Aula", purpose="Seminar nasional desain", peserta=120,
            doc=(io.BytesIO(b"%PDF-1.4 rekomendasi"), "rekomendasi.pdf"),
        )
        self.assertIn(b"menunggu verifikasi", response.data)
        reservation = self.reservation_rows("Aula")[0]
        self.assertEqual(reservation["status"], "processing")

        admin = self.client()
        self.login(admin, "sarpras@idb.ac.id")
        approval = admin.post(
            f"/admin/reservations/{reservation['id']}/approve",
            follow_redirects=True,
        )
        self.assertIn(b"berhasil disetujui", approval.data)
        self.assertEqual(self.reservation_rows("Aula")[0]["status"], "confirmed")

        db = sqlite3.connect(self.app.config["DATABASE"])
        try:
            actions = [row[0] for row in db.execute(
                "SELECT action FROM audit_logs WHERE reservation_id = ? ORDER BY id",
                (reservation["id"],),
            ).fetchall()]
        finally:
            db.close()
        self.assertEqual(actions, ["booking_created", "reservation_approved"])

    def test_audit_log_records_actor_time_and_reason(self):
        owner = self.client()
        self.login(owner)
        self.book(owner, "A.1.2")
        reservation = self.reservation_rows("A.1.2")[0]
        owner.post(
            f"/reservations/{reservation['id']}/cancel",
            data={"alasan": "Kegiatan dibatalkan"},
        )

        db = sqlite3.connect(self.app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        try:
            log = db.execute(
                "SELECT * FROM audit_logs WHERE reservation_id = ? AND action = 'reservation_cancelled'",
                (reservation["id"],),
            ).fetchone()
        finally:
            db.close()
        self.assertIsNotNone(log)
        self.assertIsNotNone(log["actor_id"])
        self.assertIsNotNone(log["created_at"])
        self.assertIn("Kegiatan dibatalkan", log["detail"])

    def test_sarpras_can_update_room_rules_and_audit(self):
        admin = self.client()
        self.login(admin, "superadmin@idb.ac.id")
        room_id = self.room_id("B.1.2")
        response = admin.post(
            f"/admin/rooms/{room_id}",
            data={"kapasitas": "18", "aktif": "on", "butuh_dokumen": "on"},
            follow_redirects=True,
        )
        self.assertIn(b"disimpan", response.data)

        db = sqlite3.connect(self.app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        try:
            room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
            log = db.execute(
                "SELECT * FROM audit_logs WHERE action = 'room_updated' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(room["kapasitas"], 18)
        self.assertEqual(room["butuh_dokumen"], 1)
        self.assertIn("kapasitas", log["detail"])


    # -- Live hero availability -----------------------------------------
    def test_home_renders_live_availability_slides(self):
        response = self.client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'class="hero-live-slide'), 6)
        self.assertEqual(response.data.count(b'class="mock-row hero-live-row"'), 28)
        self.assertIn(b"heroLiveDots", response.data)
        with open("static/js/app.js", encoding="utf-8") as handle:
            self.assertIn("/api/hero-availability", handle.read())

    def test_hero_availability_api_marks_active_booking(self):
        db = sqlite3.connect(self.app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        try:
            user_id = db.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
            room_id = self.room_id("A.1.2")
            db.execute(
                """INSERT INTO reservations
                   (kode_booking, user_id, room_id, tanggal, mulai, selesai, status,
                    keperluan, jumlah_peserta)
                   VALUES ('IDB-TEST-LIVE', ?, ?, ?, '00:00', '23:59', 'confirmed', 'Tes live', 4)""",
                (user_id, room_id, date.today().isoformat()),
            )
            db.commit()
        finally:
            db.close()

        response = self.client().get("/api/hero-availability")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        rooms = {room["kode"]: room for room in response.get_json()["rooms"]}
        self.assertEqual(rooms["A.1.2"]["status"], "terisi")
        self.assertIn("Terisi s.d.", rooms["A.1.2"]["detail"])
        self.assertNotIn("users", response.get_json())
        self.assertNotIn("pemohon", rooms["A.1.2"])


if __name__ == "__main__":
    unittest.main()
