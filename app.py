# app.py
import streamlit as st
from pymongo import MongoClient
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ------------------------
# MongoDB Setup
# ------------------------
mongo_uri = st.secrets["mongo"]["uri"]
client = MongoClient(mongo_uri)
db = client["scrapingbig"]
col = db["users"]

# ------------------------
# Konfigurasi Streamlit
# ------------------------
st.set_page_config(page_title="Present APP", layout="wide")
st.title("🎤 Analisis Public Speaking dari Video YouTube Berjudul Contoh Latihan Public Speaking (https://www.youtube.com/watch?v=eZy8ESSjbrQ)")

# ------------------------
# Ambil Data dari MongoDB
# ------------------------
video_id = "eZy8ESSjbrQ"
segmen = list(col.find({"video_id": video_id}))
if not segmen:
    st.error(f"Tidak ditemukan data untuk video_id: {video_id}")
    st.stop()

# ------------------------
# Analisis Kata, Filler, Sentimen
# ------------------------
kata_bersih = []
filler_counter = Counter()
sentimen_counter = Counter()

for s in segmen:
    kata_bersih.extend(s.get("kata_bersih", []))
    filler_counter.update(s.get("filler_words", {}))
    sentimen_counter[s.get("sentimen", "netral")] += 1

kata_freq = Counter(kata_bersih).most_common(20)

# Debugging output
st.write("🛠️ Jumlah total kata bersih:", len(kata_bersih))
st.write("🛠️ Contoh 10 kata bersih:", kata_bersih[:10])
st.write("🛠️ Hasil join kata:", repr(" ".join(kata_bersih)))

# ------------------------
# Wordcloud
# ------------------------
st.subheader("☁️ WordCloud dari Transkrip")

def tampilkan_wordcloud(kata):
    # Validasi kata yang benar-benar bersih
    kata_valid = [k for k in kata if isinstance(k, str) and k.strip()]
    if not kata_valid:
        st.warning("❗Data kata kosong atau tidak valid. Tidak bisa membuat WordCloud.")
        return

    teks = " ".join(kata_valid).strip()
    if not teks:
        st.warning("❗Setelah digabung, teks kosong. Tidak bisa membuat WordCloud.")
        return

    try:
        wc = WordCloud(width=800, height=400, background_color='white').generate(teks)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    except ValueError as e:
        st.error(f"Terjadi error saat membuat WordCloud: {e}")

tampilkan_wordcloud(kata_bersih)

# ------------------------
# Trending Topic
# ------------------------
st.subheader("📈 20 Kata Paling Sering Muncul")

def tampilkan_chart(kata_freq):
    if not kata_freq:
        st.warning("Tidak ada kata untuk ditampilkan.")
        return
    kata, jumlah = zip(*kata_freq)
    fig, ax = plt.subplots()
    ax.barh(kata, jumlah, color='skyblue')
    ax.invert_yaxis()
    st.pyplot(fig)

tampilkan_chart(kata_freq)

# ------------------------
# Filler Word Analysis
# ------------------------
st.subheader("🎤 Analisis Filler Words")
if filler_counter:
    kata, jumlah = zip(*filler_counter.most_common())
    fig, ax = plt.subplots()
    ax.bar(kata, jumlah, color='orange')
    ax.set_title("Jumlah Kemunculan Filler Words")
    st.pyplot(fig)
else:
    st.info("Tidak ditemukan filler word.")

# ------------------------
# Emotional Sentiment Chart
# ------------------------
st.subheader("😊 Analisis Sentimen Emosional")
if sentimen_counter:
    labels, counts = zip(*sentimen_counter.items())
    fig, ax = plt.subplots()
    ax.barh(labels, counts, color='lightcoral')
    ax.set_xlabel("Jumlah Segmen")
    ax.set_title("Distribusi Sentimen Emosional")
    st.pyplot(fig)
else:
    st.info("Tidak ditemukan analisis sentimen.")

# ------------------------
# Contoh Segmen
# ------------------------
st.subheader("🧾 Contoh Segmen Transkrip")
for s in segmen[:5]:
    st.markdown(f"**Waktu: {round(s['start'], 2)} detik**")
    st.text(s["teks"])
