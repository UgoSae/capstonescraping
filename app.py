# app.py
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
from pymongo import MongoClient
import re
import string
import nltk
from nltk.corpus import stopwords

nltk.download('stopwords')

# ----------------------------
# Konfigurasi MongoDB Atlas
# ----------------------------
mongo_uri = st.secrets["mongo"]["uri"]
client = MongoClient(mongo_uri)
db = client["scrapingbig"]
col = db["users"]

# ----------------------------
# Fungsi Pembersih Teks
# ----------------------------
filler_words_list = ['eh', 'hmm', 'em', 'gitu', 'apa ya', 'gimana ya', 'kayak', 'anu']

def clean_text(text):
    text = text.lower()
    text = re.sub(r'\d+', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

def remove_stopwords(words):
    stop_words = set(stopwords.words('indonesian'))
    return [word for word in words if word not in stop_words and len(word) > 1]

def detect_filler_words(words):
    return {word: words.count(word) for word in filler_words_list if word in words}

def get_sentiment(text):
    # Dummy sentiment detection based on keywords (you can replace this later)
    if any(word in text for word in ['bagus', 'senang', 'baik']):
        return 'positif'
    elif any(word in text for word in ['jelek', 'buruk', 'sedih']):
        return 'negatif'
    else:
        return 'netral'

# ----------------------------
# Scraping Transkrip
# ----------------------------
@st.cache_data(show_spinner=True)
def ambil_transkrip(video_id):
    data = YouTubeTranscriptApi.get_transcript(video_id, languages=['id', 'en'])
    hasil = []
    for segmen in data:
        teks = clean_text(segmen['text'])
        kata = teks.split()
        kata_bersih = remove_stopwords(kata)
        filler_dict = detect_filler_words(kata)
        hasil.append({
            "video_id": video_id,
            "start": segmen['start'],
            "duration": segmen['duration'],
            "teks": segmen['text'],
            "kata_bersih": kata_bersih,
            "filler_words": filler_dict,
            "sentimen": get_sentiment(teks)
        })
    return hasil

# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="TalkTrainer App", layout="wide")
st.title("🎤 Analisis Transkrip Public Speaking dari YouTube")

video_id = st.text_input("Masukkan ID video YouTube:", value="eZy8ESSjbrQ")

if st.button("Mulai Analisis"):
    with st.spinner("Mengambil dan memproses transkrip..."):
        hasil = ambil_transkrip(video_id)

        # Simpan ke MongoDB
        col.delete_many({"video_id": video_id})  # hapus data lama
        col.insert_many(hasil)

        st.success("Data berhasil diambil dan disimpan!")

# ----------------------------
# Visualisasi Data
# ----------------------------
segmen = list(col.find({"video_id": video_id}))
if segmen:
    st.header("📊 Hasil Analisis")

    kata_bersih = []
    filler_counter = Counter()
    sentimen_counter = Counter()

    for s in segmen:
        kata_bersih.extend(s["kata_bersih"])
        filler_counter.update(s["filler_words"])
        sentimen_counter[s["sentimen"]] += 1

    kata_freq = Counter(kata_bersih).most_common(20)

    # Wordcloud
    st.subheader("☁️ WordCloud")
    if kata_bersih:
        teks = " ".join(kata_bersih)
        wc = WordCloud(width=800, height=400, background_color='white').generate(teks)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.info("Tidak ada kata yang bisa digunakan untuk membuat WordCloud.")

    # Chart kata populer
    st.subheader("📈 20 Kata Paling Sering Muncul")
    if kata_freq:
        kata, jumlah = zip(*kata_freq)
        fig, ax = plt.subplots()
        ax.barh(kata, jumlah, color='skyblue')
        ax.invert_yaxis()
        st.pyplot(fig)

    # Chart filler word
    st.subheader("🗣️ Analisis Filler Word")
    if filler_counter:
        kata, jumlah = zip(*filler_counter.most_common())
        fig, ax = plt.subplots()
        ax.bar(kata, jumlah, color='orange')
        st.pyplot(fig)

    # Chart sentimen
    st.subheader("😊 Analisis Sentimen")
    if sentimen_counter:
        label, jumlah = zip(*sentimen_counter.items())
        fig, ax = plt.subplots()
        ax.barh(label, jumlah, color='lightgreen')
        st.pyplot(fig)

    # Tampilkan segmen
    st.subheader("📄 Contoh Segmen Transkrip")
    for s in segmen[:5]:
        st.markdown(f"**Waktu: {round(s['start'], 2)} detik**")
        st.text(s["teks"])
