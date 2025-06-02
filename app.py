import streamlit as st
from pymongo import MongoClient
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from youtube_transcript_api import YouTubeTranscriptApi
import re

# ------------------------
# MongoDB Setup (Atlas via Streamlit Secrets)
# ------------------------
client = MongoClient(st.secrets["MONGO_URI"])
db = client["capstonescraping"]
col = db["users"]

# ------------------------
# Stopwords & Filler Words
# ------------------------
stopwords_id = {
    'yang', 'dan', 'di', 'ke', 'dari', 'pada', 'untuk', 'dengan', 'akan',
    'ini', 'itu', 'adalah', 'atau', 'juga', 'karena', 'sudah', 'sebagai',
    'oleh', 'tidak', 'dalam', 'lebih', 'bisa', 'agar', 'namun', 'bagi',
    'tersebut', 'saat', 'masih', 'telah', 'bahwa', 'hanya', 'saja', 'mereka',
    'kami', 'kita', 'anda', 'saya', 'dia', 'ia', 'apa', 'siapa', 'mengapa',
    'bagaimana', 'kapan', 'dimana', 'jadi', 'lagi', 'lah', 'pun', 'nah',
    'ya', 'oh', 'eh', 'hmm', 'huh', 'wow', 'wah', 'uh', 'ehh', 'ohh', 'yaa',
    'nahh', 'pun', 'pula', 'lagi', 'lah', 'kah', 'tuh', 'deh', 'dong', 'sih',
    'toh', 'kok', 'kan', 'nya', 'ku', 'mu', 'kau', 'gua', 'gue', 'elo', 'lu',
    'loe', 'loh', 'lho', 'nih'
}
filler_words = {"eh", "hmm", "gitu", "apa", "ya", "kayak", "jadi", "nah", "anu", "gini"}

# ------------------------
# Fungsi Pemrosesan Teks
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
        st.info("Data untuk video ini sudah ada di database.")
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

        st.success("✅ Scraping dan penyimpanan selesai.")
    except Exception as e:
        st.error(f"Gagal scraping: {e}")

# ------------------------
# Scraping satu video saja (hanya jika belum ada)
# ------------------------
video_id = "eZy8ESSjbrQ"
judul = "Public Speaking Training"

if not col.find_one({"video_id": video_id}):
    scrap_dan_simpan(video_id, judul)

# ------------------------
# Streamlit Layout
# ------------------------
st.set_page_config(page_title="Present APP", layout="wide")
st.title("🎤 Analisis Public Speaking dari Video YouTube")

segmen = list(col.find({"video_id": video_id}))

kata_bersih = []
filler_counter = Counter()
sentimen_counter = Counter()

for s in segmen:
    kata_bersih.extend(s.get("kata_bersih", []))
    filler_counter.update(s.get("filler_words", {}))
    sentimen_counter[s.get("sentimen", "netral")] += 1

kata_freq = Counter(kata_bersih).most_common(20)

# ------------------------
# Wordcloud
# ------------------------
st.subheader("☁️ WordCloud dari Transkrip")
def tampilkan_wordcloud(kata):
    wc = WordCloud(width=800, height=400, background_color='white').generate(" ".join(kata))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis("off")
    st.pyplot(fig)

tampilkan_wordcloud(kata_bersih)

# ------------------------
# Trending Topic
# ------------------------
st.subheader("📈 20 Kata Paling Sering Muncul")
def tampilkan_chart(kata_freq):
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
