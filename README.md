# Dashboard Analisis Sentimen (Web App) - Instagram, TikTok, X

Isi folder
- `db.py`          skema database (star schema + `users` + `riwayat_pelatihan`); versi SQL ada di `schema.sql`
- `etl.py`         memuat hasil pipeline (folder `data/`) ke PostgreSQL
- `buat_user.py`   membuat akun Admin / Pengguna
- `app.py`         web app + REST API (login, peran, 4 halaman, kelola pengguna)
- `tests/test_blackbox.py`  45 skenario black box -> `tests/hasil_blackbox.csv`
- `data/`          kosong; isi dengan 9 file hasil pipeline-mu (langkah 4)

## Langkah menjalankan (Windows, di folder ini)

1. Pasang PostgreSQL 15+ (ingat password user `postgres`). Buka **pgAdmin** atau `psql`, buat database:
   `CREATE DATABASE sentimen;`
2. Pasang pustaka: `pip install -r requirements.txt`
3. Atur alamat database (PowerShell, ganti PASSWORD):
   `$env:DATABASE_URL="postgresql+psycopg2://postgres:PASSWORD@localhost:5432/sentimen"`
4. Salin hasil pipeline-mu ke folder `data/` (9 file): `prediksi_<app>.csv`, `hasil_<app>.xlsx`, `ringkasan_<app>.xlsx` untuk instagram, tiktok, x.
5. Muat ke database: `python etl.py`
6. Buat akun (akan diminta password): `python buat_user.py admin Admin` lalu `python buat_user.py pengguna1 Pengguna`
7. Jalankan: `python app.py` lalu buka http://localhost:5000
8. Uji black box: `python tests/test_blackbox.py`

Akses dari HP (satu Wi-Fi): `$env:HOST="0.0.0.0"; python app.py`, lalu buka `http://<IP-laptop>:5000`.

## Yang sudah / belum
- Sudah: login, pembedaan peran, kelola pengguna (tambah, ganti password/peran, hapus akun di halaman Admin), 3 halaman dashboard + filter, halaman Admin (unggah dan validasi berkas, riwayat), black box test.
- Belum: tombol "latih ulang" yang benar-benar menjalankan pipeline penuh (saat ini berkas divalidasi dan disimpan di `uploads/`, menunggu pemrosesan); tahap berikutnya.

## Dipasang untuk pengguna umum
Lihat `PANDUAN_RAILWAY.md`. Pengguna mendaftar sendiri di `/daftar` (peran Pengguna); login dikunci 5 menit setelah 5 kali gagal.
