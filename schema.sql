-- Skema data warehouse (star schema Kimball) + tabel operasional, PostgreSQL

CREATE TABLE dim_aplikasi (
	id_aplikasi SERIAL NOT NULL, 
	nama_aplikasi VARCHAR(50) NOT NULL, 
	package_name VARCHAR(100), 
	PRIMARY KEY (id_aplikasi), 
	UNIQUE (nama_aplikasi)
);

CREATE TABLE dim_model (
	id_model SERIAL NOT NULL, 
	nama_model VARCHAR(80) NOT NULL, 
	pembanding BOOLEAN, 
	PRIMARY KEY (id_model), 
	UNIQUE (nama_model)
);

CREATE TABLE dim_sentimen (
	id_sentimen SERIAL NOT NULL, 
	label_sentimen VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id_sentimen), 
	UNIQUE (label_sentimen)
);

CREATE TABLE dim_waktu (
	id_waktu SERIAL NOT NULL, 
	tanggal DATE NOT NULL, 
	bulan INTEGER NOT NULL, 
	tahun INTEGER NOT NULL, 
	PRIMARY KEY (id_waktu), 
	UNIQUE (tanggal)
);

CREATE TABLE users (
	id_user SERIAL NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id_user), 
	UNIQUE (username)
);

CREATE TABLE fact_evaluasi (
	id_aplikasi INTEGER NOT NULL, 
	id_model INTEGER NOT NULL, 
	accuracy FLOAT, 
	precision_pos FLOAT, 
	recall_pos FLOAT, 
	f1_pos FLOAT, 
	macro_f1 FLOAT, 
	waktu_latih FLOAT, 
	terbaik BOOLEAN, 
	n_latih INTEGER, 
	n_uji INTEGER, 
	tp INTEGER, 
	fn INTEGER, 
	fp INTEGER, 
	tn INTEGER, 
	PRIMARY KEY (id_aplikasi, id_model), 
	FOREIGN KEY(id_aplikasi) REFERENCES dim_aplikasi (id_aplikasi), 
	FOREIGN KEY(id_model) REFERENCES dim_model (id_model)
);

CREATE TABLE fact_sentimen (
	id_fact SERIAL NOT NULL, 
	id_ulasan INTEGER NOT NULL, 
	id_aplikasi INTEGER NOT NULL, 
	id_waktu INTEGER NOT NULL, 
	id_model INTEGER NOT NULL, 
	id_sentimen INTEGER NOT NULL, 
	id_sentimen_prediksi INTEGER NOT NULL, 
	prediksi_benar BOOLEAN NOT NULL, 
	data_uji BOOLEAN NOT NULL, 
	PRIMARY KEY (id_fact), 
	FOREIGN KEY(id_aplikasi) REFERENCES dim_aplikasi (id_aplikasi), 
	FOREIGN KEY(id_waktu) REFERENCES dim_waktu (id_waktu), 
	FOREIGN KEY(id_model) REFERENCES dim_model (id_model), 
	FOREIGN KEY(id_sentimen) REFERENCES dim_sentimen (id_sentimen), 
	FOREIGN KEY(id_sentimen_prediksi) REFERENCES dim_sentimen (id_sentimen)
);

CREATE INDEX ix_fact_app_model ON fact_sentimen (id_aplikasi, id_model);

CREATE INDEX ix_fact_waktu ON fact_sentimen (id_waktu);

CREATE TABLE ringkasan_label (
	id_aplikasi INTEGER NOT NULL, 
	data_awal INTEGER, 
	data_dipakai INTEGER, 
	dibuang_kosong INTEGER, 
	label_leksikon INTEGER, 
	label_rating INTEGER, 
	netral_kata INTEGER, 
	netral_model INTEGER, 
	positif INTEGER, 
	negatif INTEGER, 
	sejalan_persen FLOAT, 
	PRIMARY KEY (id_aplikasi), 
	FOREIGN KEY(id_aplikasi) REFERENCES dim_aplikasi (id_aplikasi)
);

CREATE TABLE riwayat_pelatihan (
	id SERIAL NOT NULL, 
	waktu TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	id_user INTEGER, 
	aplikasi VARCHAR(50), 
	berkas VARCHAR(255), 
	jumlah_baris INTEGER, 
	status VARCHAR(30), 
	catatan TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(id_user) REFERENCES users (id_user)
);
