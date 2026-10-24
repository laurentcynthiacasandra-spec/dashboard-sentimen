# Memasang Dashboard agar Dapat Dipakai Pengguna Umum (Railway)

Hasil akhirnya: alamat `https://....up.railway.app` yang bisa dibuka siapa saja. Pengguna baru mendaftar sendiri lewat tombol "Daftar" dan otomatis berperan **Pengguna**. Admin hanya dibuat olehmu.
Catatan: tampilan menu Railway bisa berubah; ikuti nama menunya, bukan posisinya.

## A. Unggah kode ke GitHub (sekali saja)
1. Buat akun di github.com, lalu **New repository** -> nama `dashboard-sentimen` -> **Private** -> Create.
2. Klik **uploading an existing file**, lalu seret SELURUH ISI folder `dashboard` (bukan folder `data` dan `uploads`, keduanya tidak perlu) -> **Commit changes**.
   Pastikan file `Procfile`, `app.py`, `requirements.txt`, folder `templates` dan `static` ikut terunggah.

## B. Buat proyek di Railway
1. railway.com -> **New Project** -> **Deploy from GitHub repo** -> pilih `dashboard-sentimen`.
2. Di proyek yang sama: **+ New** -> **Database** -> **Add PostgreSQL**.
3. Klik layanan web (bukan Postgres) -> tab **Variables** -> isi:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`  (pilih lewat tombol referensi bila tersedia)
   - `SECRET_KEY` = teks acak panjang buatanmu
   - `ADMIN_USER` = `admin`
   - `ADMIN_PASSWORD` = password Admin pilihanmu (minimal 8 karakter)
   - `HTTPS` = `1`
4. Tab **Settings** -> **Networking** -> **Generate Domain**. Catat alamatnya.
5. Tunggu deploy selesai (status hijau). Admin pertama dibuat otomatis dari `ADMIN_USER` dan `ADMIN_PASSWORD`.

## C. Muat data ke database online (dari laptopmu)
1. Klik layanan **Postgres** -> **Variables** -> salin nilai **DATABASE_PUBLIC_URL**.
2. Di PowerShell (folder `dashboard` di laptopmu):
   ```
   $env:DATABASE_URL="<tempel DATABASE_PUBLIC_URL>"
   python etl.py data
   ```
   (bentuk `postgresql://...` otomatis diubah menjadi `+psycopg2` oleh program)
3. Tunggu "SELESAI. 290496 baris fakta dimuat" (bisa 10-30 menit tergantung internet).

## D. Uji
1. Buka alamat dari langkah B4, login sebagai admin.
2. Buka di jendela penyamaran, klik **Daftar**, buat akun, lalu pastikan menu Admin tidak tampil.
3. Bagikan alamat itu ke responden.

## Hal penting
- Berkas yang diunggah Admin disimpan di disk sementara Railway dan hilang saat deploy ulang.
- Untuk mematikan pendaftaran mandiri, isi variabel `BOLEH_DAFTAR` = `0`.
- Pantau pemakaian/biaya Railway (paket gratis ada batasnya).
- Jangan simpan password asli (milikmu sendiri) di GitHub; semua rahasia hanya di tab Variables.
