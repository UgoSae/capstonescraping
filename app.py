import streamlit as st
from pymongo import MongoClient
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from youtube_transcript_api import YouTubeTranscriptApi
import re

from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# ------------------------
# Stopwords & Filler
# ------------------------
factory = StopWordRemoverFactory()
stopwords_id = set(factory.get_stop_words())
filler_words = {"eh", "hmm", "gitu", "apa", "ya", "kayak", "jadi", "nah", "anu", "gini"}
stopwords_id.update(filler_words)

# ------------------------
# MongoDB
# ------------------------
client = MongoClient(st.secrets["MONGODB_URI"])
db = client["scrapingbig"]
col = db["users"]

# ------------------------
# Fungsi Pemrosesan
# ------------------------
def bersihkan_teks(teks):
    teks = re.sub(r'[^a-zA-Z\s]', '', teks).lower()
    kata = teks.split()
    return [k for k in kata if k not in stopwords_id and len(k) > 2]

def hitung_filler(teks):
    teks = teks.lower()
    return {fw: teks.split().count(fw) for fw in filler_words if fw in teks}

def dummy_sentimen(teks):
    if "senang" in teks or "bagus" in teks:
        return "positif"
    elif "buruk" in teks or "jelek" in teks:
        return "negatif"
    else:
        return "netral"

def scrap_dan_simpan(video_id, judul):
    if col.find_one({"video_id": video_id}):
        return

    try:
        transkrip = YouTubeTranscriptApi.get_transcript(video_id, languages=['id'])
        for seg in transkrip:
            teks = seg["text"]
            kata_bersih = bersihkan_teks(teks)
            filler = hitung_filler(teks)
            sentimen = dummy_sentimen(teks)

            doc = {
                "video_id": video_id,
                "judul": judul,
                "start": seg["start"],
                "duration": seg["duration"],
                "teks": teks,
                "kata_bersih": kata_bersih,
                "filler_words": filler,
                "sentimen": sentimen
            }
            col.insert_one(doc)
    except Exception as e:
        st.error(f"Gagal scraping: {e}")

# ------------------------
# Video
# ------------------------
video_id = "eZy8ESSjbrQ"
judul = "Contoh Latihan Public Speaking"

st.set_page_config(page_title="Present APP", layout="wide")
st.title("🎤 Analisis Public Speaking dari Video YouTube")
st.markdown(f"**Video:** [{judul}](https://www.youtube.com/watch?v={video_id})")

# ------------------------
# Scraping Jika Belum Ada
# ------------------------
if not col.find_one({"video_id": video_id}):
    with st.spinner("Sedang mengambil dan memproses transkrip..."):
        scrap_dan_simpan(video_id, judul)
    st.success("✅ Data berhasil disiapkan.")

# ------------------------
# Ambil Data
# ------------------------
segmen = list(col.find({"video_id": video_id}))
if not segmen:
    st.warning("Tidak ada data transkrip.")
    st.stop()

# ------------------------
# Sidebar Filter (Dropdown)
# ------------------------
st.sidebar.header("🎛️ Filter Transkrip")

opsi_sentimen = ["semua", "positif", "netral", "negatif"]
sentimen_terpilih = st.sidebar.selectbox("Pilih sentimen:", opsi_sentimen)

# Ambil semua kata bersih unik dari semua segmen
semua_kata = set()
for s in segmen:
    semua_kata.update(s.get("kata_bersih", []))
daftar_kata = sorted(list(semua_kata))
kata_terpilih = st.sidebar.selectbox("Pilih kata:", ["(semua)"] + daftar_kata)

# ------------------------
# Terapkan Filter
# ------------------------
segmen_terfilter = segmen

if sentimen_terpilih != "semua":
    segmen_terfilter = [s for s in segmen_terfilter if s.get("sentimen") == sentimen_terpilih]

if kata_terpilih != "(semua)":
    segmen_terfilter = [s for s in segmen_terfilter if kata_terpilih in s.get("kata_bersih", [])]

if not segmen_terfilter:
    st.warning("Tidak ada segmen yang cocok dengan filter.")
    st.stop()

# ------------------------
# Analisis
# ------------------------
kata_bersih = []
filler_counter = Counter()
sentimen_counter = Counter()

for s in segmen_terfilter:
    kata_bersih.extend(s.get("kata_bersih", []))
    filler_counter.update(s.get("filler_words", {}))
    sentimen_counter[s.get("sentimen", "netral")] += 1

kata_freq = Counter(kata_bersih).most_common(20)

# ------------------------
# Visualisasi
# ------------------------
st.subheader("☁️ WordCloud dari Transkrip")
wc = WordCloud(width=800, height=400, background_color='white').generate(" ".join(kata_bersih))
fig, ax = plt.subplots(figsize=(10, 5))
ax.imshow(wc, interpolation='bilinear')
ax.axis("off")
st.pyplot(fig)

st.subheader("📈 20 Kata Paling Sering Muncul")
if kata_freq:
    kata, jumlah = zip(*kata_freq)
    fig, ax = plt.subplots()
    ax.barh(kata, jumlah, color='skyblue')
    ax.invert_yaxis()
    st.pyplot(fig)
else:
    st.info("Tidak ada kata dominan pada hasil filter.")

st.subheader("🎤 Analisis Filler Words")
if filler_counter:
    kata, jumlah = zip(*filler_counter.most_common())
    fig, ax = plt.subplots()
    ax.bar(kata, jumlah, color='orange')
    ax.set_title("Jumlah Kemunculan Filler Words")
    st.pyplot(fig)
else:
    st.info("Tidak ditemukan filler word.")

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
for s in segmen_terfilter[:5]:
    st.markdown(f"**Waktu: {round(s['start'], 2)} detik**")
    st.text(s["teks"])
