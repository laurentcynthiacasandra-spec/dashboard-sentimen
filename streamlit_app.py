import os, re, time, datetime
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Dashboard Analisis Sentimen", page_icon="📊", layout="wide")

# --- koneksi: DATABASE_URL dari Secrets (cloud) atau variabel lingkungan (lokal)
try:
    if "DATABASE_URL" in st.secrets: os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
except Exception:
    pass
from sqlalchemy import select, func, insert, update, delete, and_
from werkzeug.security import check_password_hash, generate_password_hash
import db

da, dw, dm, fs, fe, rl, us, rp = db.dim_aplikasi, db.dim_waktu, db.dim_model, db.fact_sentimen, db.fact_evaluasi, db.ringkasan_label, db.users, db.riwayat_pelatihan
APPCOL = {"Instagram": "#8e44ad", "TikTok": "#16a085", "X": "#34495e"}
POS, NEG = "#2e7d32", "#c62828"
ROLES = ("Admin", "Pengguna")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

st.markdown("""<style>
.block-container{padding-top:1.4rem}
div[data-testid="stMetric"]{background:#fff;border:1px solid #e2e8f0;border-left:4px solid #e67e22;border-radius:12px;padding:12px 16px}
div[data-testid="stMetric"] *{color:#0f172a !important}
.kartu{color:#0f172a;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 18px;box-shadow:0 1px 3px rgba(15,23,42,.06)}
.kartu h4{margin:0 0 4px 0}.kartu .pct{font-size:2rem;font-weight:700}.kartu small{color:#64748b}
.meter{display:flex;height:10px;border-radius:6px;overflow:hidden;margin:8px 0}.meter i{display:block}
.hl{color:#0f172a;background:#fff4e5;border:1px solid #f5d3a6;border-radius:10px;padding:10px 14px;margin:6px 0 14px 0}
</style>""", unsafe_allow_html=True)

fmt = lambda n: f"{int(n):,}".replace(",", ".")

# ---------------------------------------------------------------- data (di-cache sebentar agar ringan)
@st.cache_data(ttl=120, show_spinner=False)
def meta():
    with db.engine.connect() as c:
        apps = [(r.id_aplikasi, r.nama_aplikasi) for r in c.execute(select(da).order_by(da.c.id_aplikasi))]
        models = [(r.id_model, r.nama_model) for r in c.execute(select(dm).order_by(dm.c.id_model))]
        mn, mx = c.execute(select(func.min(dw.c.tanggal), func.max(dw.c.tanggal))).first()
        tahun = sorted(r[0] for r in c.execute(select(dw.c.tahun).distinct()))
    return dict(apps=apps, models=models, mn=mn, mx=mx, tahun=tahun)

@st.cache_data(ttl=120, show_spinner=False)
def data_ringkasan():
    with db.engine.connect() as c:
        apps = {r.id_aplikasi: r.nama_aplikasi for r in c.execute(select(da))}
        rows = c.execute(select(rl)).all()
        per = [dict(aplikasi=apps[r.id_aplikasi], positif=r.positif, negatif=r.negatif, total=r.data_dipakai,
                    persen=round(r.positif / r.data_dipakai * 100, 1), sejalan=r.sejalan_persen) for r in rows]
        best = [dict(aplikasi=apps[r.id_aplikasi], model=r.nama_model, f1=round(r.macro_f1, 4)) for r in
                c.execute(select(fe, dm.c.nama_model).join(dm, dm.c.id_model == fe.c.id_model).where(fe.c.terbaik == True))]  # noqa
        mx = c.execute(select(func.max(dw.c.tanggal))).scalar()
    return per, best, mx

@st.cache_data(ttl=120, show_spinner=False)
def data_sentimen(app_id, dari, sampai, sumber, model_id):
    kolom = fs.c.id_sentimen if sumber == "aktual" else fs.c.id_sentimen_prediksi
    cond = [fs.c.id_model == model_id]
    if dari: cond.append(dw.c.tanggal >= dari)
    if sampai: cond.append(dw.c.tanggal <= sampai)
    if sumber == "prediksi": cond.append(fs.c.data_uji == True)  # noqa
    if app_id: cond.append(fs.c.id_aplikasi == app_id)
    with db.engine.connect() as c:
        apps = {r.id_aplikasi: r.nama_aplikasi for r in c.execute(select(da))}
        q = (select(fs.c.id_aplikasi, dw.c.tahun, dw.c.bulan, kolom.label("s"), func.count().label("n"))
             .join(dw, dw.c.id_waktu == fs.c.id_waktu).where(and_(*cond)).group_by(fs.c.id_aplikasi, dw.c.tahun, dw.c.bulan, kolom))
        rows = [(apps[r.id_aplikasi], r.tahun, r.bulan, "Positif" if r.s == 1 else "Negatif", r.n) for r in c.execute(q)]
    return pd.DataFrame(rows, columns=["aplikasi", "tahun", "bulan", "sentimen", "n"])

@st.cache_data(ttl=120, show_spinner=False)
def data_performa():
    with db.engine.connect() as c:
        apps = {r.id_aplikasi: r.nama_aplikasi for r in c.execute(select(da))}
        q = select(fe, dm.c.nama_model).join(dm, dm.c.id_model == fe.c.id_model).order_by(fe.c.id_aplikasi, fe.c.id_model)
        rows = [dict(Aplikasi=apps[r.id_aplikasi], Algoritma=r.nama_model, Accuracy=r.accuracy, Precision=r.precision_pos, Recall=r.recall_pos,
                     F1=r.f1_pos, MacroF1=r.macro_f1, Waktu=r.waktu_latih, Terbaik=bool(r.terbaik), tp=r.tp, fn=r.fn, fp=r.fp, tn=r.tn) for r in c.execute(q)]
    return pd.DataFrame(rows)

# ---------------------------------------------------------------- autentikasi
@st.cache_resource
def gagal_login(): return {}          # (username) -> [jumlah, waktu pertama]; pembatas tebak-tebakan password
BATAS, JEDA = 5, 300

def terkunci(u):
    g = gagal_login().get(u.lower())
    if not g: return 0
    sisa = JEDA - (time.time() - g[1])
    if sisa <= 0: gagal_login().pop(u.lower(), None); return 0
    return int(sisa) + 1 if g[0] >= BATAS else 0

def masuk(u, p):
    sisa = terkunci(u)
    if sisa: return f"Terlalu banyak percobaan gagal. Coba lagi dalam {sisa // 60 + 1} menit."
    with db.engine.connect() as c:
        r = c.execute(select(us).where(us.c.username == u)).first()
    if r and check_password_hash(r.password_hash, p):
        gagal_login().pop(u.lower(), None)
        st.session_state.update(user=r.username, role=r.role, uid=r.id_user); return None
    g = gagal_login().setdefault(u.lower(), [0, time.time()]); g[0] += 1
    return "Username atau password salah."

def cek_user(u, p, role, wajib_password=True, min_pw=8):
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,50}", u or ""): return "Username 3-50 karakter: huruf, angka, titik, garis bawah, atau strip."
    if role not in ROLES: return "Peran harus Admin atau Pengguna."
    if (wajib_password or p) and len(p or "") < min_pw: return f"Password minimal {min_pw} karakter."
    return None

def daftar(u, p, p2):
    err = cek_user(u, p, "Pengguna")
    if err: return err
    if p != p2: return "Konfirmasi password tidak sama."
    with db.engine.begin() as c:
        if c.execute(select(us.c.id_user).where(func.lower(us.c.username) == u.lower())).first(): return "Username sudah dipakai."
        c.execute(insert(us).values(username=u, password_hash=generate_password_hash(p), role="Pengguna"))
    return None

def halaman_login():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.title("Dashboard Analisis Sentimen")
        st.caption("Instagram, TikTok, dan X (Google Play Store)")
        t1, t2 = st.tabs(["Masuk", "Daftar"])
        with t1:
            with st.form("f_masuk"):
                u = st.text_input("Username"); p = st.text_input("Password", type="password")
                if st.form_submit_button("Masuk", width="stretch"):
                    e = masuk(u.strip(), p)
                    if e: st.error(e)
                    else: st.rerun()
        with t2:
            if st.session_state.get("daftar_ok"): st.success("Akun berhasil dibuat. Silakan masuk pada tab Masuk.")
            with st.form("f_daftar"):
                u = st.text_input("Username", key="du"); p = st.text_input("Password (minimal 8 karakter)", type="password", key="dp")
                p2 = st.text_input("Ulangi password", type="password", key="dp2")
                if st.form_submit_button("Daftar", width="stretch"):
                    e = daftar(u.strip(), p, p2)
                    if e: st.session_state["daftar_ok"] = False; st.error(e)
                    else: st.session_state["daftar_ok"] = True; st.rerun()

# ---------------------------------------------------------------- halaman
def halaman_ringkasan():
    st.header("Ringkasan Insight Utama")
    per, best, mx = data_ringkasan()
    if not per: st.warning("Data belum dimuat. Jalankan etl.py."); return
    total = sum(a["total"] for a in per); pos = sum(a["positif"] for a in per); neg = sum(a["negatif"] for a in per)
    k = st.columns(4)
    k[0].metric("Total ulasan dianalisis", fmt(total), help=f"{len(per)} aplikasi")
    k[1].metric("Rata-rata sentimen positif", f"{pos / total * 100:.1f}%".replace(".", ","))
    k[2].metric("Model terbaik", " / ".join(sorted({b["model"].split(" (")[0] for b in best})) or "-")
    k[3].metric("Data terakhir", str(mx))
    cols = st.columns(len(per))
    for col, a in zip(cols, per):
        c = APPCOL.get(a["aplikasi"], "#888")
        col.markdown(f"""<div class="kartu" style="border-top:4px solid {c}"><h4 style="color:{c}">{a['aplikasi']}</h4>
<div class="pct">{str(a['persen']).replace('.', ',')}%<small> positif</small></div>
<div class="meter"><i style="width:{a['persen']}%;background:{POS}"></i><i style="width:{100 - a['persen']}%;background:{NEG}"></i></div>
<small>{fmt(a['positif'])} positif · {fmt(a['negatif'])} negatif · {fmt(a['total'])} ulasan</small></div>""", unsafe_allow_html=True)
    st.write("")
    g1, g2 = st.columns(2)
    d = pd.DataFrame(per)
    with g1:
        st.subheader("Persentase Sentimen Positif per Aplikasi")
        ch = alt.Chart(d).mark_bar().encode(y=alt.Y("aplikasi:N", title=None, sort="-x"), x=alt.X("persen:Q", scale=alt.Scale(domain=[0, 100]), title="% positif"),
              color=alt.Color("aplikasi:N", scale=alt.Scale(domain=list(APPCOL), range=list(APPCOL.values())), legend=None),
              tooltip=["aplikasi", "persen"]).properties(height=260)
        st.altair_chart(ch, width="stretch")
    with g2:
        st.subheader("Distribusi Sentimen Keseluruhan")
        dd = pd.DataFrame({"sentimen": [f"Positif ({fmt(pos)})", f"Negatif ({fmt(neg)})"], "n": [pos, neg]})
        ch = alt.Chart(dd).mark_arc(innerRadius=60).encode(theta="n:Q", color=alt.Color("sentimen:N", scale=alt.Scale(domain=list(dd["sentimen"]), range=[POS, NEG]), legend=alt.Legend(orient="bottom", title=None)),
              tooltip=["sentimen", "n"]).properties(height=260)
        st.altair_chart(ch, width="stretch")
    st.subheader("Insight Utama")
    t = max(per, key=lambda a: a["persen"]); b = min(per, key=lambda a: a["persen"])
    ins = [f"{t['aplikasi']} memiliki proporsi sentimen positif tertinggi ({t['persen']}%), sedangkan {b['aplikasi']} terendah ({b['persen']}%)."]
    ins += [f"Pada {x['aplikasi']}, model terbaik adalah {x['model']} (macro-F1 {x['f1']})." for x in best]
    lo = min(per, key=lambda a: a["sejalan"])
    ins.append(f"Kesesuaian rating dengan skor leksikon hanya {lo['sejalan']}% pada {lo['aplikasi']}, sehingga klasifikasi berbasis teks tetap diperlukan.")
    st.markdown("\n".join(f"- {i}" for i in ins))
    st.caption("Label sentimen berasal dari pelabelan hybrid (leksikon InSet + rating); lihat halaman Performa Algoritma untuk kualitas model.")

def _isi_tahun():
    t = st.session_state.get("f_tahun"); m = meta()   # dibatasi pada rentang tanggal data
    st.session_state["f_dari"] = max(datetime.date(t, 1, 1), m["mn"]) if t else None
    st.session_state["f_sampai"] = min(datetime.date(t, 12, 31), m["mx"]) if t else None

def _reset_filter():
    st.session_state.update(f_app="Semua aplikasi", f_tahun=None, f_dari=None, f_sampai=None, f_sumber="Hasil pelabelan (semua ulasan)")

def halaman_sentimen():
    st.header("Perbandingan Sentimen")
    m = meta(); nama_app = dict((n, i) for i, n in m["apps"]); nama_model = dict((n, i) for i, n in m["models"])
    f = st.columns(4)
    app_pilih = f[0].selectbox("Aplikasi", ["Semua aplikasi"] + list(nama_app), key="f_app")
    f[1].selectbox("Tahun", [None] + m["tahun"], format_func=lambda x: "Semua tahun" if x is None else str(x), key="f_tahun", on_change=_isi_tahun)
    dari = f[2].date_input("Dari tanggal", value=None, min_value=m["mn"], max_value=m["mx"], key="f_dari")
    sampai = f[3].date_input("Sampai tanggal", value=None, min_value=m["mn"], max_value=m["mx"], key="f_sampai")
    f2 = st.columns([2, 2, 1])
    sumber = f2[0].selectbox("Sumber label", ["Hasil pelabelan (semua ulasan)", "Prediksi model (data uji)"], key="f_sumber")
    mod = f2[1].selectbox("Algoritma", list(nama_model), key="f_model", disabled=not sumber.startswith("Prediksi"))
    f2[2].write(""); f2[2].button("Atur ulang", on_click=_reset_filter, width="stretch")
    akt = sumber.startswith("Hasil")
    df = data_sentimen(nama_app.get(app_pilih), dari, sampai, "aktual" if akt else "prediksi", 1 if akt else nama_model[mod])
    if df.empty: st.info("Data tidak tersedia untuk filter ini."); return
    dist = df.pivot_table(index="aplikasi", columns="sentimen", values="n", aggfunc="sum", fill_value=0).reset_index()
    for k in ("Positif", "Negatif"):
        if k not in dist: dist[k] = 0
    dist["Total"] = dist["Positif"] + dist["Negatif"]; dist["% Positif"] = (dist["Positif"] / dist["Total"] * 100).round(1)
    per = f"{dari or 'awal'} s.d. {sampai or 'akhir'}" if (dari or sampai) else "seluruh periode"
    if len(dist) > 1:
        u = dist.sort_values("% Positif", ascending=False); a, z = u.iloc[0], u.iloc[-1]
        st.markdown(f"<div class='hl'><b>Pada {per}</b>, sentimen positif tertinggi ada pada <b style='color:{APPCOL.get(a.aplikasi, '#1a5276')}'>{a.aplikasi}</b> "
                    f"({str(a['% Positif']).replace('.', ',')}%), sedangkan terendah <b>{z.aplikasi}</b> ({str(z['% Positif']).replace('.', ',')}%). "
                    f"Selisih {str(round(a['% Positif'] - z['% Positif'], 1)).replace('.', ',')} poin.</div>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Proporsi Sentimen Positif vs Negatif")
        p = df.groupby(["aplikasi", "sentimen"], as_index=False)["n"].sum()
        ch = alt.Chart(p).mark_bar().encode(x=alt.X("aplikasi:N", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("n:Q", stack="normalize", axis=alt.Axis(format="%"), title=None),
              color=alt.Color("sentimen:N", scale=alt.Scale(domain=["Positif", "Negatif"], range=[POS, NEG]), legend=alt.Legend(orient="top", title=None)),
              order=alt.Order("sentimen:N", sort="descending"), tooltip=["aplikasi", "sentimen", "n"]).properties(height=330)
        st.altair_chart(ch, width="stretch")
    with g2:
        st.subheader("Tren Jumlah Ulasan per Bulan")
        t = df.copy(); t["bulan_"] = t["tahun"].astype(str) + "-" + t["bulan"].astype(int).astype(str).str.zfill(2); t["seri"] = t["aplikasi"] + " - " + t["sentimen"]
        t = t.groupby(["bulan_", "aplikasi", "sentimen", "seri"], as_index=False)["n"].sum()
        ch = alt.Chart(t).mark_line(point=True).encode(x=alt.X("bulan_:O", title=None), y=alt.Y("n:Q", title=None),
              color=alt.Color("aplikasi:N", scale=alt.Scale(domain=list(APPCOL), range=list(APPCOL.values())), legend=alt.Legend(orient="bottom", title=None)),
              strokeDash=alt.StrokeDash("sentimen:N", scale=alt.Scale(domain=["Positif", "Negatif"], range=[[1, 0], [5, 4]]), legend=alt.Legend(orient="bottom", title=None)),
              detail="seri:N", tooltip=["bulan_", "seri", "n"]).properties(height=330)
        st.altair_chart(ch, width="stretch")
    st.subheader("Rincian")
    tbl = dist[["aplikasi", "Positif", "Negatif", "Total", "% Positif"]].rename(columns={"aplikasi": "Aplikasi"})
    st.dataframe(tbl, hide_index=True, width="stretch",
                 column_config={k: st.column_config.NumberColumn(format="%d") for k in ("Positif", "Negatif", "Total")} | {"% Positif": st.column_config.NumberColumn(format="%.1f%%")})
    st.caption("Menghitung seluruh ulasan berdasarkan label hasil pelabelan hybrid." if akt else "Menghitung data uji berdasarkan prediksi model terpilih.")

def halaman_performa():
    st.header("Perbandingan Performa Algoritma")
    d = data_performa()
    if d.empty: st.warning("Data evaluasi belum dimuat."); return
    f = st.columns(2)
    pa = f[0].selectbox("Aplikasi", ["Semua aplikasi"] + sorted(d.Aplikasi.unique()))
    pm = f[1].selectbox("Algoritma", ["Semua algoritma"] + sorted(d.Algoritma.unique()))
    v = d[(d.Aplikasi == pa) | (pa == "Semua aplikasi")]; v = v[(v.Algoritma == pm) | (pm == "Semua algoritma")]
    st.subheader("Tabel Perbandingan Metrik Evaluasi (data uji)")
    t = v[["Aplikasi", "Algoritma", "Accuracy", "Precision", "Recall", "F1", "MacroF1", "Waktu", "Terbaik"]].copy()
    t["Algoritma"] = t.apply(lambda r: r.Algoritma + (" ★" if r.Terbaik else ""), axis=1)
    sty = t.drop(columns="Terbaik").style.format({k: "{:.4f}" for k in ("Accuracy", "Precision", "Recall", "F1", "MacroF1")} | {"Waktu": "{:.1f}"}).apply(
        lambda r: ["background-color:#eaf6ec;font-weight:600" if "★" in r["Algoritma"] else "" for _ in r], axis=1)
    st.dataframe(sty, hide_index=True, width="stretch", column_config={"MacroF1": "Macro-F1", "Waktu": "Waktu latih (detik)"})
    st.caption("Model terbaik ditentukan berdasarkan macro-F1; selisih kurang dari 0,01 dianggap setara. Precision, recall, dan F1 dihitung untuk kelas positif.")
    BIRU = ["#2b7bd6", "#1b4f8a"]
    algs = sorted(d.Algoritma.unique())
    vc = d[(d.Aplikasi == pa) | (pa == "Semua aplikasi")]      # grafik selalu menampilkan kedua algoritma
    g1, g2 = st.columns([3, 2])
    with g1:
        st.subheader("Grafik Macro-F1 per Aplikasi")
        base = alt.Chart(vc).encode(x=alt.X("Aplikasi:N", title=None, axis=alt.Axis(labelAngle=0)), xOffset=alt.XOffset("Algoritma:N", sort=algs),
              y=alt.Y("MacroF1:Q", scale=alt.Scale(domain=[0, 1]), title="Macro-F1"))
        bars = base.mark_bar().encode(color=alt.Color("Algoritma:N", scale=alt.Scale(domain=algs, range=BIRU), legend=alt.Legend(orient="bottom", title=None)),
              tooltip=["Aplikasi", "Algoritma", alt.Tooltip("MacroF1:Q", format=".4f")])
        lbl = base.mark_text(dy=-8, fontSize=12).encode(text=alt.Text("MacroF1:Q", format=".4f"))
        st.altair_chart((bars + lbl).properties(height=320), width="stretch")
    with g2:
        st.subheader("Rekomendasi Algoritma")
        for ap in sorted(d.Aplikasi.unique()):
            u = d[d.Aplikasi == ap].sort_values("MacroF1", ascending=False)
            if len(u) < 2: continue
            sel = u.iloc[0].MacroF1 - u.iloc[1].MacroF1
            if sel < 0.01: st.markdown(f"**{ap}:** Setara. Selisih macro-F1 {sel:.4f} (< 0,01): kedua model dianggap setara.")
            else: st.markdown(f"**{ap}:** {u.iloc[0].Algoritma}  \n<small>macro-F1 {u.iloc[0].MacroF1:.4f} vs {u.iloc[1].MacroF1:.4f}, selisih {sel:.4f}.</small>", unsafe_allow_html=True)
    st.subheader("Confusion Matrix")
    isvm = next((i for i, n in enumerate(algs) if "SVM" in n), 0)
    pcm = st.selectbox("Algoritma untuk confusion matrix", algs, index=isvm, key="cm_alg")
    st.caption(f"Confusion matrix model {pcm} pada data uji. Baris = label aktual, kolom = hasil prediksi.")
    daftar = [a for a in sorted(d.Aplikasi.unique()) if pa in ("Semua aplikasi", a)]
    kol = st.columns(len(daftar))
    for k, ap in zip(kol, daftar):
        z = d[(d.Aplikasi == ap) & (d.Algoritma == pcm)]
        if z.empty: continue
        r = z.iloc[0]
        cm = pd.DataFrame([["Positif", "Positif", r.tp], ["Positif", "Negatif", r.fn], ["Negatif", "Positif", r.fp], ["Negatif", "Negatif", r.tn]], columns=["Aktual", "Prediksi", "n"])
        cm["lbl"] = cm.n.map(lambda v: f"{int(v):,}".replace(",", "."))
        mx = cm.n.max()
        bs = alt.Chart(cm).encode(x=alt.X("Prediksi:N", sort=["Positif", "Negatif"], axis=alt.Axis(labelAngle=0, orient="bottom")),
                                  y=alt.Y("Aktual:N", sort=["Positif", "Negatif"], axis=alt.Axis(labelAngle=-90, labelAlign="center", labelBaseline="middle")))
        hm = bs.mark_rect().encode(color=alt.Color("n:Q", legend=None, scale=alt.Scale(scheme="blues", domain=[0, mx])), tooltip=["Aktual", "Prediksi", "n"])
        tx = bs.mark_text(fontSize=18, fontWeight="bold").encode(text="lbl:N", color=alt.condition(alt.datum.n > mx * 0.5, alt.value("white"), alt.value("#111")))
        with k:
            st.markdown(f"**{ap}**")
            st.altair_chart((hm + tx).properties(height=240), width="stretch")

def halaman_admin():
    st.header("Halaman Admin")
    st.subheader("Unggah Data Ulasan Baru")
    col = st.columns([1, 2])
    m = meta(); app_pilih = col[0].selectbox("Aplikasi target", [n for _, n in m["apps"]], key="up_app")
    berkas = col[1].file_uploader("Berkas ulasan (.csv atau .xlsx; kolom wajib: content, score, at)", type=["csv", "xlsx"])
    if berkas is not None and st.button("Unggah dan validasi"):
        def catat(status, baris, cat):
            with db.engine.begin() as c:
                c.execute(insert(rp).values(waktu=datetime.datetime.now(), id_user=st.session_state["uid"], aplikasi=app_pilih, berkas=berkas.name, jumlah_baris=baris, status=status, catatan=cat))
        try: df = pd.read_csv(berkas) if berkas.name.lower().endswith(".csv") else pd.read_excel(berkas)
        except Exception: catat("Ditolak", 0, "Berkas tidak dapat dibaca"); st.error("Berkas tidak dapat dibaca.")
        else:
            kurang = {"content", "score", "at"} - set(df.columns)
            if kurang: catat("Ditolak", len(df), "Kolom kurang: " + ", ".join(sorted(kurang))); st.error("Kolom wajib tidak ditemukan: " + ", ".join(sorted(kurang)))
            else:
                try: os.makedirs(UPLOAD_DIR, exist_ok=True); df.to_csv(os.path.join(UPLOAD_DIR, f"{app_pilih}_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv"), index=False)
                except Exception: pass
                catat("Diterima", len(df), "Menunggu pemrosesan pipeline"); st.success(f"{len(df)} baris diterima. Langkah pelatihan ulang dijalankan melalui pipeline.")
    st.subheader("Riwayat Unggahan")
    with db.engine.connect() as c:
        rs = c.execute(select(rp, us.c.username).join(us, us.c.id_user == rp.c.id_user, isouter=True).order_by(rp.c.id.desc()).limit(20)).all()
    st.dataframe(pd.DataFrame([dict(Waktu=r.waktu.strftime("%d %b %Y %H:%M"), Pengguna=r.username, Aplikasi=r.aplikasi, Berkas=r.berkas, Baris=r.jumlah_baris, Status=r.status, Catatan=r.catatan) for r in rs]),
                 hide_index=True, width="stretch")
    st.subheader("Kelola Pengguna")
    with db.engine.connect() as c:
        akun = c.execute(select(us).order_by(us.c.id_user)).all()
    st.dataframe(pd.DataFrame([dict(ID=r.id_user, Username=r.username, Peran=r.role) for r in akun]), hide_index=True, width="stretch")
    t1, t2, t3 = st.tabs(["Tambah akun", "Ubah password / peran", "Hapus akun"])
    with t1, st.form("f_tambah", clear_on_submit=True):
        u = st.text_input("Username"); p = st.text_input("Password (minimal 6 karakter)", type="password"); r = st.selectbox("Peran", ROLES, index=1)
        if st.form_submit_button("Tambah"):
            e = cek_user(u.strip(), p, r, min_pw=6)
            if e: st.error(e)
            else:
                with db.engine.begin() as c:
                    if c.execute(select(us.c.id_user).where(us.c.username == u.strip())).first(): st.error("Username sudah dipakai.")
                    else: c.execute(insert(us).values(username=u.strip(), password_hash=generate_password_hash(p), role=r)); st.success(f"Akun {u.strip()} dibuat."); st.rerun()
    pilih = {r.username: r for r in akun}
    with t2, st.form("f_ubah"):
        u = st.selectbox("Akun", list(pilih)); p = st.text_input("Password baru (kosongkan bila tidak diganti)", type="password"); r = st.selectbox("Peran", ROLES)
        if st.form_submit_button("Simpan"):
            e = cek_user(u, p, r, wajib_password=False, min_pw=6)
            with db.engine.begin() as c:
                n_admin = c.execute(select(func.count()).select_from(us).where(us.c.role == "Admin")).scalar()
                if e: st.error(e)
                elif pilih[u].role == "Admin" and r != "Admin" and n_admin <= 1: st.error("Tidak bisa menurunkan Admin terakhir.")
                else:
                    vals = {"role": r} | ({"password_hash": generate_password_hash(p)} if p else {})
                    c.execute(update(us).where(us.c.username == u).values(**vals)); st.success(f"Akun {u} diperbarui.")
                    if pilih[u].id_user == st.session_state["uid"]: st.session_state["role"] = r
    with t3, st.form("f_hapus"):
        u = st.selectbox("Akun yang dihapus", list(pilih))
        if st.form_submit_button("Hapus"):
            with db.engine.begin() as c:
                n_admin = c.execute(select(func.count()).select_from(us).where(us.c.role == "Admin")).scalar()
                if pilih[u].id_user == st.session_state["uid"]: st.error("Tidak bisa menghapus akun yang sedang dipakai.")
                elif pilih[u].role == "Admin" and n_admin <= 1: st.error("Tidak bisa menghapus Admin terakhir.")
                else:
                    c.execute(update(rp).where(rp.c.id_user == pilih[u].id_user).values(id_user=None)); c.execute(delete(us).where(us.c.id_user == pilih[u].id_user))
                    st.success(f"Akun {u} dihapus."); st.rerun()

# ---------------------------------------------------------------- utama
def utama():
    try: db.init_db()
    except Exception as e: st.error(f"Tidak dapat terhubung ke database: {e}"); st.stop()
    if "user" not in st.session_state: halaman_login(); return
    menu = ["Ringkasan", "Perbandingan Sentimen", "Performa Algoritma"] + (["Admin"] if st.session_state["role"] == "Admin" else [])
    with st.sidebar:
        st.markdown("### 📊 Dashboard Analisis Sentimen")
        hal = st.radio("Menu", menu, label_visibility="collapsed")
        st.divider(); st.caption(f"Masuk sebagai **{st.session_state['user']}** ({st.session_state['role']})")
        if st.button("Keluar", width="stretch"):
            for k in list(st.session_state): del st.session_state[k]
            st.rerun()
    {"Ringkasan": halaman_ringkasan, "Perbandingan Sentimen": halaman_sentimen, "Performa Algoritma": halaman_performa, "Admin": halaman_admin}[hal]()

utama()
