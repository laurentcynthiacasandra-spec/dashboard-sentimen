import os

import bcrypt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

# ---------------------------------------------------------------------------
# Konfigurasi halaman dan tema
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Analisis Sentimen Instagram, TikTok, dan X",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

HD = "#175A85"
POS = "#3F8A1E"
NEG = "#D94545"
BG = "#EFEAE8"

st.markdown(
    f"""
    <style>
    .main .block-container {{max-width: 1100px; padding-top: 1rem; padding-bottom: 2rem;}}
    .stTabs [data-baseweb="tab-list"] {{gap: 4px;}}
    .stTabs [data-baseweb="tab"] {{background: {BG}; border-radius: 8px 8px 0 0;}}
    .stTabs [aria-selected="true"] {{background: {HD}; color: white;}}
    .metric-card {{background: white; padding: 1rem; border-radius: 8px; border: 1px solid #ddd;}}
    .metric-label {{color: #666; font-size: 0.85rem; text-transform: uppercase;}}
    .metric-value {{font-size: 2rem; font-weight: bold; color: {HD};}}
    .metric-sub {{color: #666; font-size: 0.9rem;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Koneksi basis data
# ---------------------------------------------------------------------------
def _get_dsn() -> str:
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return os.environ["DATABASE_URL"]


@st.cache_resource
def get_conn():
    return psycopg2.connect(_get_dsn(), sslmode="require")


def kueri(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            data = cur.fetchall()
        return pd.DataFrame(data, columns=cols)
    except Exception:
        conn.rollback()
        raise


def eksekusi(sql: str, params: tuple = ()) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Autentikasi
# ---------------------------------------------------------------------------
def masuk(username: str, password: str):
    df = kueri(
        "SELECT id_user, username, password_hash, role FROM users WHERE username = %s",
        (username.strip(),),
    )
    if df.empty:
        return None
    row = df.iloc[0]
    try:
        cocok = bcrypt.checkpw(
            password.encode("utf-8"), row["password_hash"].encode("utf-8")
        )
    except Exception:
        cocok = False
    if not cocok:
        return None
    return {"id_user": int(row["id_user"]), "username": row["username"], "role": row["role"]}


def daftar(username: str, password: str, konfirmasi: str) -> tuple[bool, str]:
    username = username.strip()
    if len(username) < 3:
        return False, "Username minimal 3 karakter."
    if len(password) < 6:
        return False, "Password minimal 6 karakter."
    if password != konfirmasi:
        return False, "Konfirmasi password tidak cocok."
    ada = kueri("SELECT 1 FROM users WHERE username = %s", (username,))
    if not ada.empty:
        return False, "Username sudah terpakai."
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    eksekusi(
        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'Pengguna')",
        (username, hashed),
    )
    return True, "Akun berhasil dibuat. Silakan masuk."


# ---------------------------------------------------------------------------
# Kueri data analitis
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def model_utama_id() -> int:
    """Ambil id_model bukan pembanding (SVM/NB utama)."""
    df = kueri(
        "SELECT id_model FROM dim_model WHERE COALESCE(pembanding, FALSE) = FALSE ORDER BY id_model LIMIT 1"
    )
    if not df.empty:
        return int(df.iloc[0]["id_model"])
    df2 = kueri("SELECT MIN(id_model) AS id_min FROM fact_sentimen")
    return int(df2.iloc[0]["id_min"]) if not df2.empty else 1


@st.cache_data(ttl=300, show_spinner=False)
def daftar_aplikasi() -> list[str]:
    df = kueri("SELECT nama_aplikasi FROM dim_aplikasi ORDER BY nama_aplikasi")
    return df["nama_aplikasi"].tolist()


@st.cache_data(ttl=300, show_spinner=False)
def ringkasan_global() -> dict:
    """Total ulasan, rata-rata positif, dan jumlah aplikasi."""
    df = kueri(
        """
        SELECT a.nama_aplikasi AS aplikasi,
               s.label_sentimen AS label,
               COUNT(*) AS jumlah
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
        GROUP BY a.nama_aplikasi, s.label_sentimen
        ORDER BY a.nama_aplikasi, s.label_sentimen
        """
    )
    # Normalkan label jadi Title Case supaya konsisten
    df["label"] = df["label"].str.strip().str.title()
    total_rincian = (
        df.groupby("aplikasi")["jumlah"].sum().reset_index().rename(columns={"jumlah": "total_app"})
    )
    df = df.merge(total_rincian, on="aplikasi")
    total = int(df["jumlah"].sum()) // 2 if False else int(total_rincian["total_app"].sum())
    positif = int(df[df["label"] == "Positif"]["jumlah"].sum())
    pos_pct = (positif / total * 100) if total else 0.0
    aplikasi = sorted(df["aplikasi"].unique())
    return {
        "total": total,
        "positif_pct": pos_pct,
        "jumlah_aplikasi": len(aplikasi),
        "aplikasi": aplikasi,
        "rincian": df,
    }


@st.cache_data(ttl=300, show_spinner=False)
def metrik_model() -> pd.DataFrame:
    """Hitung metrik evaluasi per (aplikasi, model) dari data uji.

    Pakai id_sentimen (aktual) vs id_sentimen_prediksi, difilter data_uji = TRUE.
    """
    df = kueri(
        """
        SELECT a.nama_aplikasi AS aplikasi,
               m.nama_model AS model,
               s_akt.label_sentimen AS aktual,
               s_pre.label_sentimen AS prediksi,
               COUNT(*) AS n
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_model m ON m.id_model = f.id_model
        JOIN dim_sentimen s_akt ON s_akt.id_sentimen = f.id_sentimen
        JOIN dim_sentimen s_pre ON s_pre.id_sentimen = f.id_sentimen_prediksi
        WHERE f.data_uji = TRUE
        GROUP BY a.nama_aplikasi, m.nama_model, s_akt.label_sentimen, s_pre.label_sentimen
        ORDER BY a.nama_aplikasi, m.nama_model
        """
    )
    if df.empty:
        return df
    df["aktual"] = df["aktual"].str.strip().str.title()
    df["prediksi"] = df["prediksi"].str.strip().str.title()
    return df


def hitung_metrik(cm: dict) -> dict:
    """Hitung accuracy, precision, recall, F1 untuk kelas positif & negatif."""
    tp = cm.get(("Positif", "Positif"), 0)
    fn = cm.get(("Positif", "Negatif"), 0)
    fp = cm.get(("Negatif", "Positif"), 0)
    tn = cm.get(("Negatif", "Negatif"), 0)
    total = tp + fn + fp + tn
    acc = (tp + tn) / total if total else 0.0

    def _prf(tp_, fp_, fn_):
        prec = tp_ / (tp_ + fp_) if (tp_ + fp_) else 0.0
        rec = tp_ / (tp_ + fn_) if (tp_ + fn_) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        return prec, rec, f1

    p_pos, r_pos, f1_pos = _prf(tp, fp, fn)
    p_neg, r_neg, f1_neg = _prf(tn, fn, fp)
    macro_f1 = (f1_pos + f1_neg) / 2
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": acc,
        "precision_pos": p_pos, "recall_pos": r_pos, "f1_pos": f1_pos,
        "precision_neg": p_neg, "recall_neg": r_neg, "f1_neg": f1_neg,
        "macro_f1": macro_f1,
    }


@st.cache_data(ttl=300, show_spinner=False)
def performa_semua() -> pd.DataFrame:
    df = metrik_model()
    if df.empty:
        return df
    baris = []
    for (app, model), grup in df.groupby(["aplikasi", "model"]):
        cm = {(a, p): int(n) for a, p, n in zip(grup["aktual"], grup["prediksi"], grup["n"])}
        hasil = hitung_metrik(cm)
        baris.append({"aplikasi": app, "model": model, **hasil})
    return pd.DataFrame(baris)


@st.cache_data(ttl=300, show_spinner=False)
def rentang_tanggal(aplikasi: str) -> tuple:
    if aplikasi == "Semua":
        df = kueri(
            """
            SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx
            FROM fact_sentimen f
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            """
        )
    else:
        df = kueri(
            """
            SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx
            FROM fact_sentimen f
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            WHERE a.nama_aplikasi = %s
            """,
            (aplikasi,),
        )
    return df.iloc[0]["mn"], df.iloc[0]["mx"]


@st.cache_data(ttl=300, show_spinner=False)
def sentimen_tersaring(aplikasi: str, dari, sampai) -> pd.DataFrame:
    kondisi_app = "" if aplikasi == "Semua" else "AND a.nama_aplikasi = %s"
    param_app = () if aplikasi == "Semua" else (aplikasi,)
    if dari and sampai:
        sql = f"""
            SELECT a.nama_aplikasi AS aplikasi,
                   s.label_sentimen AS label,
                   COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            WHERE w.tanggal BETWEEN %s AND %s {kondisi_app}
            GROUP BY a.nama_aplikasi, s.label_sentimen
            ORDER BY a.nama_aplikasi, s.label_sentimen
        """
        df = kueri(sql, (dari, sampai) + param_app)
    else:
        sql = f"""
            SELECT a.nama_aplikasi AS aplikasi,
                   s.label_sentimen AS label,
                   COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            WHERE 1 = 1 {kondisi_app}
            GROUP BY a.nama_aplikasi, s.label_sentimen
            ORDER BY a.nama_aplikasi, s.label_sentimen
        """
        df = kueri(sql, param_app)
    if not df.empty:
        df["label"] = df["label"].str.strip().str.title()
    return df


@st.cache_data(ttl=60, show_spinner=False)
def riwayat_unggahan() -> pd.DataFrame:
    try:
        return kueri(
            """
            SELECT r.id, r.waktu, u.username, r.aplikasi, r.berkas,
                   r.jumlah_baris, r.status, r.catatan
            FROM riwayat_pelatihan r
            JOIN users u ON u.id_user = r.id_user
            ORDER BY r.waktu DESC
            LIMIT 50
            """
        )
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Komponen visual
# ---------------------------------------------------------------------------
def kartu_metrik(label: str, nilai: str, sub: str = "", warna: str = HD) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{warna};">{nilai}</div>
            {f'<div class="metric-sub">{sub}</div>' if sub else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def grafik_distribusi(data: dict) -> None:
    rincian = data["rincian"]
    pos_total = int(rincian[rincian["label"] == "Positif"]["jumlah"].sum())
    neg_total = int(rincian[rincian["label"] == "Negatif"]["jumlah"].sum())
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Positif", "Negatif"],
                values=[pos_total, neg_total],
                hole=0.5,
                marker=dict(colors=[POS, NEG]),
                textinfo="label+percent",
                textfont=dict(size=14),
            )
        ]
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=320, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Halaman: Ringkasan
# ---------------------------------------------------------------------------
def halaman_ringkasan() -> None:
    st.header("Ringkasan Insight Utama")
    data = ringkasan_global()
    k1, k2, k3 = st.columns(3)
    with k1:
        kartu_metrik(
            "Total Ulasan",
            f"{data['total']:,}".replace(",", "."),
            f"{data['jumlah_aplikasi']} aplikasi",
        )
    with k2:
        kartu_metrik(
            "Sentimen Positif (Rata-rata)",
            f"{data['positif_pct']:.1f}%".replace(".", ","),
            warna=POS,
        )
    with k3:
        kartu_metrik("Model Terbaik", "SVM (kernel linear)")

    st.markdown("### Distribusi Sentimen")
    grafik_distribusi(data)

    st.markdown("### Insight Utama")
    rincian = data["rincian"]
    pos_app = rincian[rincian["label"] == "Positif"].copy()
    pos_app["pct"] = pos_app["jumlah"] / pos_app["total_app"] * 100
    if not pos_app.empty:
        terbaik = pos_app.sort_values("pct", ascending=False).iloc[0]
        st.markdown(
            f"- **{terbaik['aplikasi']}** memiliki sentimen positif tertinggi "
            f"({terbaik['pct']:.1f}%).".replace(".", ",")
        )
    st.markdown(
        "- Pada ketiga aplikasi, model SVM memberikan macro-F1 yang lebih tinggi dibanding Naive Bayes."
    )
    try:
        tgl_terakhir = kueri(
            "SELECT MAX(w.tanggal) AS mx FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu"
        ).iloc[0]["mx"]
        if pd.notna(tgl_terakhir):
            st.markdown(
                f"- Data terbaru: **{tgl_terakhir.strftime('%d %B %Y')}**."
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Halaman: Perbandingan Sentimen
# ---------------------------------------------------------------------------
def halaman_sentimen() -> None:
    st.header("Perbandingan Sentimen")
    data = ringkasan_global()
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        aplikasi = st.selectbox(
            "Aplikasi", ["Semua"] + data["aplikasi"], index=0, key="filter_sentimen_app"
        )
    mn, mx = rentang_tanggal(aplikasi)
    with col2:
        dari = st.date_input(
            "Dari", value=None, min_value=mn, max_value=mx,
            key="filter_sentimen_dari", format="DD/MM/YYYY",
        )
    with col3:
        sampai = st.date_input(
            "Sampai", value=None, min_value=mn, max_value=mx,
            key="filter_sentimen_sampai", format="DD/MM/YYYY",
        )
    if mn and mx:
        st.caption(
            f"Data tersedia pada rentang **{mn.strftime('%d %b %Y')} – {mx.strftime('%d %b %Y')}**."
        )
    if dari and sampai and dari > sampai:
        st.error("Tanggal 'Dari' tidak boleh lebih besar dari 'Sampai'.")
        return

    df = sentimen_tersaring(aplikasi, dari, sampai)
    if df.empty:
        st.warning("Tidak ada ulasan pada selang waktu ini.")
        return

    pivot = df.pivot(index="aplikasi", columns="label", values="jumlah").fillna(0)
    for kolom in ["Positif", "Negatif"]:
        if kolom not in pivot.columns:
            pivot[kolom] = 0
    pivot["Total"] = pivot["Positif"] + pivot["Negatif"]
    pivot["Positif %"] = (pivot["Positif"] / pivot["Total"] * 100).round(1)
    pivot["Negatif %"] = (pivot["Negatif"] / pivot["Total"] * 100).round(1)

    st.subheader("Persentase Sentimen per Aplikasi")
    melt = pivot.reset_index().melt(
        id_vars="aplikasi", value_vars=["Positif %", "Negatif %"],
        var_name="Sentimen", value_name="Persentase",
    )
    melt["Sentimen"] = melt["Sentimen"].str.replace(" %", "")
    fig = px.bar(
        melt, x="Persentase", y="aplikasi", color="Sentimen", orientation="h",
        color_discrete_map={"Positif": POS, "Negatif": NEG}, text="Persentase",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
    fig.update_layout(
        xaxis=dict(range=[0, 100], title=""), yaxis=dict(title=""),
        barmode="stack", height=260, margin=dict(l=10, r=10, t=30, b=10), legend_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tabel Perbandingan")
    tampil = pivot.reset_index()[["aplikasi", "Positif", "Negatif", "Total"]].copy()
    tampil.columns = ["Aplikasi", "Positif", "Negatif", "Total"]
    for c in ["Positif", "Negatif", "Total"]:
        tampil[c] = tampil[c].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    st.table(tampil)


# ---------------------------------------------------------------------------
# Halaman: Performa Algoritma
# ---------------------------------------------------------------------------
def halaman_performa() -> None:
    st.header("Perbandingan Performa Algoritma")
    data = ringkasan_global()
    aplikasi = st.selectbox("Aplikasi", data["aplikasi"], key="filter_performa_app")
    perf = performa_semua()
    if perf.empty:
        st.info(
            "Metrik performa belum tersedia. Pastikan fact_sentimen memiliki data_uji dan id_sentimen_prediksi."
        )
        return
    sub = perf[perf["aplikasi"] == aplikasi].sort_values("model")
    if sub.empty:
        st.warning(f"Tidak ada data performa untuk aplikasi {aplikasi}.")
        return

    st.subheader("Macro-F1 (data uji)")
    fig = px.bar(
        sub, x="macro_f1", y="model", orientation="h", color="model",
        color_discrete_map={"Naive Bayes": "#2A79D6", "SVM": "#1B4F8A",
                            "Complement Naive Bayes": "#2A79D6"},
        text="macro_f1",
    )
    fig.update_traces(texttemplate="%{text:.4f}", textposition="outside")
    fig.update_layout(
        xaxis=dict(range=[0, 1], title=""), yaxis=dict(title=""),
        showlegend=False, height=220, margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
    terbaik = sub.sort_values("macro_f1", ascending=False).iloc[0]["model"]
    st.success(f"Model terbaik untuk {aplikasi}: **{terbaik}**")

    st.subheader("Metrik Evaluasi")
    kolom = [
        ("accuracy", "Accuracy"),
        ("precision_pos", "Precision (+)"),
        ("recall_pos", "Recall (+)"),
        ("f1_pos", "F1 (+)"),
        ("precision_neg", "Precision (−)"),
        ("recall_neg", "Recall (−)"),
        ("f1_neg", "F1 (−)"),
        ("macro_f1", "Macro-F1"),
    ]
    tabel = pd.DataFrame({"Metrik": [n for _, n in kolom]})
    for _, baris in sub.iterrows():
        tabel[baris["model"]] = [
            f"{baris[k]:.4f}".replace(".", ",") if pd.notna(baris[k]) else "-"
            for k, _ in kolom
        ]
    st.table(tabel)

    st.subheader(f"Confusion Matrix ({terbaik})")
    bar_terbaik = sub[sub["model"] == terbaik].iloc[0]
    cm_df = pd.DataFrame(
        [
            ["Aktual Positif", int(bar_terbaik["tp"]), int(bar_terbaik["fn"])],
            ["Aktual Negatif", int(bar_terbaik["fp"]), int(bar_terbaik["tn"])],
        ],
        columns=["", "Prediksi Positif", "Prediksi Negatif"],
    )
    st.table(cm_df)


# ---------------------------------------------------------------------------
# Halaman: Admin — Unggah dan Riwayat
# ---------------------------------------------------------------------------
def halaman_admin(user: dict) -> None:
    st.header("Halaman Admin")
    data = ringkasan_global()

    st.subheader("Unggah Data Ulasan Baru")
    aplikasi = st.selectbox("Aplikasi", data["aplikasi"], key="admin_app")
    berkas = st.file_uploader(
        "Berkas ulasan (.csv atau .xlsx, kolom: content, score, at)",
        type=["csv", "xlsx"],
    )
    if st.button("Unggah dan Proses", type="primary", use_container_width=True):
        if berkas is None:
            st.error("Pilih berkas terlebih dahulu.")
        else:
            proses_unggahan(user, aplikasi, berkas)
            ringkasan_global.clear()
            riwayat_unggahan.clear()
            st.rerun()

    st.divider()
    st.subheader("Riwayat Unggahan")
    riwayat = riwayat_unggahan()
    if riwayat.empty:
        st.info("Belum ada unggahan.")
        return
    for _, baris in riwayat.iterrows():
        kolom = st.columns([2, 2, 2, 3, 2, 1])
        kolom[0].write(
            baris["waktu"].strftime("%d %b %Y %H:%M") if pd.notna(baris["waktu"]) else "-"
        )
        kolom[1].write(baris["aplikasi"])
        kolom[2].write(baris["username"])
        kolom[3].write(baris["berkas"] or "-")
        kolom[4].write(
            f"{int(baris['jumlah_baris']):,} ulasan".replace(",", ".")
            if pd.notna(baris["jumlah_baris"]) else "-"
        )
        if baris["status"] not in ("Dibatalkan",):
            if kolom[5].button("Batal", key=f"batal_{baris['id']}"):
                batalkan_unggahan(int(baris["id"]))
                ringkasan_global.clear()
                riwayat_unggahan.clear()
                st.rerun()
        else:
            kolom[5].caption(baris["status"])


def proses_unggahan(user: dict, aplikasi: str, berkas) -> None:
    """Validasi berkas Admin dan simpan sebagai pending di riwayat_pelatihan."""
    try:
        if berkas.name.lower().endswith(".csv"):
            df = pd.read_csv(berkas)
        else:
            df = pd.read_excel(berkas)
    except Exception as exc:
        st.error(f"Berkas tidak dapat dibaca: {exc}")
        return
    kolom_rendah = [c.lower() for c in df.columns]
    wajib = {"content", "score", "at"}
    hilang = wajib - set(kolom_rendah)
    if hilang:
        st.error(f"Kolom wajib tidak lengkap: {', '.join(sorted(hilang))}.")
        return
    if len(df) > 2000:
        st.error(f"Jumlah baris ({len(df)}) melebihi batas 2.000 ulasan per unggahan.")
        return
    try:
        eksekusi(
            """
            INSERT INTO riwayat_pelatihan (waktu, id_user, aplikasi, berkas, jumlah_baris, status, catatan)
            VALUES (NOW(), %s, %s, %s, %s, 'Pending', %s)
            """,
            (
                user["id_user"],
                aplikasi,
                berkas.name,
                len(df),
                "Menunggu pemrosesan oleh skrip pipeline peneliti",
            ),
        )
        st.success(
            f"Berkas {berkas.name} ({len(df)} ulasan) tercatat pada riwayat sebagai 'Pending'. "
            "Pemrosesan pelabelan dan prediksi dijalankan oleh skrip pipeline peneliti."
        )
    except Exception as exc:
        st.error(f"Gagal mencatat unggahan: {exc}")


def batalkan_unggahan(id_unggahan: int) -> None:
    try:
        eksekusi(
            "UPDATE riwayat_pelatihan SET status = 'Dibatalkan' WHERE id = %s",
            (id_unggahan,),
        )
        st.success("Unggahan dibatalkan.")
    except Exception as exc:
        st.error(f"Gagal membatalkan: {exc}")


# ---------------------------------------------------------------------------
# Halaman: Login dan Daftar
# ---------------------------------------------------------------------------
def halaman_login() -> None:
    st.markdown(
        f"<h1 style='color:{HD};text-align:center;margin-top:2rem;'>Analisis Sentimen</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#666;'>Instagram · TikTok · X</p>",
        unsafe_allow_html=True,
    )
    tab_masuk, tab_daftar = st.tabs(["Masuk", "Daftar"])
    with tab_masuk:
        with st.form("form_masuk", clear_on_submit=False):
            u = st.text_input("Username", key="masuk_u")
            p = st.text_input("Password", type="password", key="masuk_p")
            submit = st.form_submit_button("Masuk", use_container_width=True, type="primary")
        if submit:
            if not u or not p:
                st.error("Username dan password wajib diisi.")
            else:
                user = masuk(u, p)
                if user is None:
                    st.error("Username atau password salah.")
                else:
                    st.session_state["user"] = user
                    st.rerun()

    with tab_daftar:
        with st.form("form_daftar", clear_on_submit=True):
            u = st.text_input("Username baru", key="daftar_u")
            p = st.text_input("Password", type="password", key="daftar_p")
            k = st.text_input("Konfirmasi password", type="password", key="daftar_k")
            submit = st.form_submit_button("Daftar", use_container_width=True, type="primary")
        if submit:
            ok, pesan = daftar(u, p, k)
            if ok:
                st.success(pesan)
            else:
                st.error(pesan)
        st.caption("Akun baru otomatis berperan Pengguna.")


# ---------------------------------------------------------------------------
# Routing utama
# ---------------------------------------------------------------------------
def aplikasi_utama() -> None:
    user = st.session_state["user"]
    with st.sidebar:
        st.markdown(f"**{user['username']}**  \nPeran: `{user['role']}`")
        if st.button("Keluar", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()
        st.divider()
        st.caption("Analisis Sentimen Instagram, TikTok, dan X")
        st.caption("Universitas Tarumanagara")

    if user["role"] == "Admin":
        tab_ring, tab_sent, tab_perf, tab_adm = st.tabs(
            ["Ringkasan", "Sentimen", "Performa", "Admin"]
        )
        with tab_ring:
            halaman_ringkasan()
        with tab_sent:
            halaman_sentimen()
        with tab_perf:
            halaman_performa()
        with tab_adm:
            halaman_admin(user)
    else:
        tab_ring, tab_sent, tab_perf = st.tabs(["Ringkasan", "Sentimen", "Performa"])
        with tab_ring:
            halaman_ringkasan()
        with tab_sent:
            halaman_sentimen()
        with tab_perf:
            halaman_performa()


def main() -> None:
    if "user" not in st.session_state:
        halaman_login()
    else:
        aplikasi_utama()


if __name__ == "__main__":
    main()
