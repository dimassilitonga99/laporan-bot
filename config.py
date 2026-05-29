import os
from dotenv import load_dotenv

load_dotenv()

# =============================================
# KONFIGURASI BOT - ISI SESUAI KEBUTUHAN ANDA
# =============================================

# Token Bot Telegram (dari @BotFather)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Google Gemini API Key (GRATIS dari https://aistudio.google.com)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Daftar Toko
TOKO_LIST = {
    "1": {
        "nama": "Toko Central Perabot Alak",
        "kode": "central_alak",
        "format": "central_alak",
        "jumlah_kassa": 4,
        "ada_ecer_grosir": True,
        "ada_kasir_promo": True,
        "ada_parkir": True,
    },
    "2": {
        "nama": "Toko Nasional Kitchen",
        "kode": "nasional_kitchen",
        "format": "nasional_kitchen",
        "jumlah_kassa": 2,
        "ada_ecer_grosir": True,
        "ada_kasir_promo": False,
        "ada_parkir": False,
    },
    "3": {
        "nama": "Toko Perabot Mama Oesapa",
        "kode": "mama_oesapa",
        "format": "mama_simple",
        "jumlah_kassa": 2,
        "ada_ecer_grosir": False,
        "ada_kasir_promo": False,
        "ada_parkir": False,
    },
    "4": {
        "nama": "Toko Perabot Mama TDM",
        "kode": "mama_tdm",
        "format": "mama_simple",
        "jumlah_kassa": 2,
        "ada_ecer_grosir": False,
        "ada_kasir_promo": False,
        "ada_parkir": False,
    },
    "5": {
        "nama": "Toko Perabot MamaKU Kefamenanu",
        "kode": "mamaku_kefa",
        "format": "mama_simple",
        "jumlah_kassa": 2,
        "ada_ecer_grosir": False,
        "ada_kasir_promo": False,
        "ada_parkir": False,
    },
}

# Nama kasir per kassa untuk Toko Central Perabot Alak
KASIR_CENTRAL = {
    1: "Yuni-Salsa",
    2: "Nanda-Umi-Marselina",
    3: "Febri-Jien-Tika",
    4: "Delfi-Tirsa",
}
