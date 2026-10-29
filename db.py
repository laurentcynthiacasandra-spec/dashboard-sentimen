"""Koneksi dan skema database (star schema Kimball + tabel operasional).
Produksi/Uji Program : PostgreSQL  -> set DATABASE_URL=postgresql+psycopg2://postgres:PASSWORD@localhost:5432/sentimen
Uji coba tanpa PostgreSQL: DATABASE_URL=sqlite:///sentimen_demo.db  (hanya untuk mencoba, bukan untuk skripsi)
"""
import os
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, Float, Date,
                        Boolean, DateTime, ForeignKey, Text, Index)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/sentimen")
# Railway/Heroku memberi "postgres://..." atau "postgresql://..."; paksa memakai driver psycopg2
for _p in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(_p): DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(_p):]
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
md = MetaData()

# ---- dimension
dim_aplikasi = Table("dim_aplikasi", md,
    Column("id_aplikasi", Integer, primary_key=True), Column("nama_aplikasi", String(50), nullable=False, unique=True),
    Column("package_name", String(100)))
dim_waktu = Table("dim_waktu", md,
    Column("id_waktu", Integer, primary_key=True), Column("tanggal", Date, nullable=False, unique=True),
    Column("bulan", Integer, nullable=False), Column("tahun", Integer, nullable=False))
dim_model = Table("dim_model", md,
    Column("id_model", Integer, primary_key=True), Column("nama_model", String(80), nullable=False, unique=True),
    Column("pembanding", Boolean, default=False))
dim_sentimen = Table("dim_sentimen", md,
    Column("id_sentimen", Integer, primary_key=True), Column("label_sentimen", String(20), nullable=False, unique=True))
# ---- fact (grain: satu ulasan x satu model)
fact_sentimen = Table("fact_sentimen", md,
    Column("id_fact", Integer, primary_key=True, autoincrement=True),
    Column("id_ulasan", Integer, nullable=False),
    Column("id_aplikasi", Integer, ForeignKey("dim_aplikasi.id_aplikasi"), nullable=False),
    Column("id_waktu", Integer, ForeignKey("dim_waktu.id_waktu"), nullable=False),
    Column("id_model", Integer, ForeignKey("dim_model.id_model"), nullable=False),
    Column("id_sentimen", Integer, ForeignKey("dim_sentimen.id_sentimen"), nullable=False),   # label aktual (hasil pelabelan hybrid)
    Column("id_sentimen_prediksi", Integer, ForeignKey("dim_sentimen.id_sentimen"), nullable=False),
    Column("prediksi_benar", Boolean, nullable=False),
    Column("data_uji", Boolean, nullable=False))
Index("ix_fact_app_model", fact_sentimen.c.id_aplikasi, fact_sentimen.c.id_model)
Index("ix_fact_waktu", fact_sentimen.c.id_waktu)
# ---- fact evaluasi (ringkasan metrik per aplikasi x model)
fact_evaluasi = Table("fact_evaluasi", md,
    Column("id_aplikasi", Integer, ForeignKey("dim_aplikasi.id_aplikasi"), primary_key=True),
    Column("id_model", Integer, ForeignKey("dim_model.id_model"), primary_key=True),
    Column("accuracy", Float), Column("precision_pos", Float), Column("recall_pos", Float),
    Column("f1_pos", Float), Column("macro_f1", Float), Column("waktu_latih", Float),
    Column("terbaik", Boolean), Column("n_latih", Integer), Column("n_uji", Integer),
    Column("tp", Integer), Column("fn", Integer), Column("fp", Integer), Column("tn", Integer))
# ringkasan pelabelan per aplikasi
ringkasan_label = Table("ringkasan_label", md,
    Column("id_aplikasi", Integer, ForeignKey("dim_aplikasi.id_aplikasi"), primary_key=True),
    Column("data_awal", Integer), Column("data_dipakai", Integer), Column("dibuang_kosong", Integer),
    Column("label_leksikon", Integer), Column("label_rating", Integer),
    Column("netral_kata", Integer), Column("netral_model", Integer),
    Column("positif", Integer), Column("negatif", Integer), Column("sejalan_persen", Float))
# ---- operasional
users = Table("users", md,
    Column("id_user", Integer, primary_key=True, autoincrement=True),
    Column("username", String(50), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(20), nullable=False))          # 'Admin' | 'Pengguna'
riwayat_pelatihan = Table("riwayat_pelatihan", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("waktu", DateTime, nullable=False), Column("id_user", Integer, ForeignKey("users.id_user")),
    Column("aplikasi", String(50)), Column("berkas", String(255)), Column("jumlah_baris", Integer),
    Column("status", String(30)), Column("catatan", Text))

# catatan tiap unggahan Admin yang diproses (dipakai untuk membatalkan unggahan secara bersih)
unggahan = Table("unggahan", md,
    Column("id_riwayat", Integer, ForeignKey("riwayat_pelatihan.id"), primary_key=True),
    Column("id_aplikasi", Integer, ForeignKey("dim_aplikasi.id_aplikasi")),
    Column("n_awal", Integer), Column("n_kosong", Integer), Column("n_dipakai", Integer),
    Column("n_leksikon", Integer), Column("n_rating", Integer), Column("n_netral_kata", Integer), Column("n_netral_model", Integer),
    Column("n_positif", Integer), Column("n_negatif", Integer), Column("dibatalkan", Boolean, default=False, nullable=False))

def init_db(drop=False):
    if drop: md.drop_all(engine)
    md.create_all(engine)
