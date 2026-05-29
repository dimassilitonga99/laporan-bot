import logging
import asyncio
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, TOKO_LIST
from ocr_reader import scan_gambar
from report_generator import generate_laporan

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

(
    STATE_PILIH_TOKO,
    STATE_PILIH_TANGGAL,
    STATE_SCAN_GAMBAR,
) = range(3)

def get_alur_scan(toko_config: dict) -> list:
    fmt = toko_config["format"]
    alur = []
    if fmt == "central_alak":
        alur.append({"label": "📷 Kirim gambar laporan KASSA 1", "tipe": "kassa", "key": "kassa", "sub_key": 1})
        alur.append({"label": "📷 Kirim gambar laporan KASSA 2", "tipe": "kassa", "key": "kassa", "sub_key": 2})
        alur.append({"label": "📷 Kirim gambar laporan KASSA 3", "tipe": "kassa", "key": "kassa", "sub_key": 3})
        alur.append({"label": "📷 Kirim gambar laporan KASSA 4", "tipe": "kassa", "key": "kassa", "sub_key": 4})
        alur.append({"label": "📷 Kirim gambar REKAP UTAMA
(Total Penjualan + Tunai + Debit + Kredit)", "tipe": "rekap_utama", "key": "rekap_utama", "sub_key": None})
        alur.append({"label": "📷 Kirim gambar laporan ECER
(ambil Total Transaksi → Ecer)", "tipe": "ecer", "key": "ecer", "sub_key": None})
        alur.append({"label": "📷 Kirim gambar laporan GROSIR
(ambil Total Transaksi → Grosir)", "tipe": "grosir", "key": "grosir", "sub_key": None})
        alur.append({"label": "📷 Kirim gambar KASIR PROMO
(Total + Tunai + Debit + Kredit)", "tipe": "kasir_promo", "key": "kasir_promo", "sub_key": None})
        alur.append({"label": "📷 Kirim gambar LAPORAN PARKIR
(Parkir Komputer + Stor Luar + Total)", "tipe": "parkir", "key": "parkir", "sub_key": None})
    elif fmt == "nasional_kitchen":
        alur.append({"label": "📷 Kirim gambar laporan KASSA 1", "tipe": "kassa", "key": "kassa", "sub_key": 1})
        alur.append({"label": "📷 Kirim gambar laporan KASSA 2", "tipe": "kassa", "key": "kassa", "sub_key": 2})
        alur.append({"label": "📷 Kirim gambar REKAP UTAMA
(Total Penjualan + Tunai + Debit + Kredit)", "tipe": "rekap_utama", "key": "rekap_utama", "sub_key": None})
        alur.append({"label": "📷 Kirim gambar laporan ECER
(ambil Total Transaksi → Ecer)", "tipe": "ecer", "key": "ecer", "sub_key": None})
        alur.append({"label": "📷 Kirim gambar laporan GROSIR
(ambil Total Transaksi → Grosir)", "tipe": "grosir", "key": "grosir", "sub_key": None})
    else:
        alur.append({"label": "📷 Kirim gambar laporan KASSA 1", "tipe": "kassa", "key": "kassa", "sub_key": 1})
        alur.append({"label": "📷 Kirim gambar laporan KASSA 2", "tipe": "kassa", "key": "kassa", "sub_key": 2})
        alur.append({"label": "📷 Kirim gambar REKAP UTAMA
(Total Penjualan + Tunai + Debit + Kredit)", "tipe": "rekap_utama", "key": "rekap_utama", "sub_key": None})
    return alur

def simpan_hasil_scan(user_data: dict, langkah: dict, hasil: dict):
    tipe = langkah["tipe"]
    sub_key = langkah["sub_key"]
    if tipe == "kassa":
        if "kassa" not in user_data["laporan_data"]:
            user_data["laporan_data"]["kassa"] = {}
        user_data["laporan_data"]["kassa"][sub_key] = hasil.get("total_transaksi", "-")
    elif tipe == "rekap_utama":
        user_data["laporan_data"]["total_penjualan"] = hasil.get("total_transaksi", "-")
        user_data["laporan_data"]["tunai"] = hasil.get("tunai", "-")
        user_data["laporan_data"]["debit"] = hasil.get("debit", "-")
        user_data["laporan_data"]["kredit"] = hasil.get("kredit", "")
    elif tipe == "ecer":
        user_data["laporan_data"]["ecer"] = hasil.get("total_transaksi", "-")
    elif tipe == "grosir":
        user_data["laporan_data"]["grosir"] = hasil.get("total_transaksi", "-")
    elif tipe == "kasir_promo":
        user_data["laporan_data"]["kasir_promo"] = {
            "total": hasil.get("total", "-"),
            "tunai": hasil.get("tunai", "-"),
            "debit": hasil.get("debit", ""),
            "kredit": hasil.get("kredit", ""),
        }
    elif tipe == "parkir":
        user_data["laporan_data"]["parkir"] = {
            "parkir_komputer": hasil.get("parkir_komputer", ""),
            "parkir_stor_luar": hasil.get("parkir_stor_luar", "-"),
            "total_parkir": hasil.get("total_parkir", "-"),
        }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = []
    for nomor, toko in TOKO_LIST.items():
        keyboard.append([InlineKeyboardButton(f"{nomor}. {toko['nama']}", callback_data=f"toko_{nomor}")])
    keyboard.append([InlineKeyboardButton("✗ Batal", callback_data="batal")])
    await update.message.reply_text(
        "🏪 *REKAP LAPORAN PENJUALAN*

Pilih toko yang ingin dibuat laporannya:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return STATE_PILIH_TOKO

async def pilih_toko(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "batal":
        await query.edit_message_text("✗ Dibatalkan. Ketik /start untuk memulai lagi.")
        return ConversationHandler.END
    nomor_toko = query.data.replace("toko_", "")
    toko = TOKO_LIST.get(nomor_toko)
    if not toko:
        await query.edit_message_text("Toko tidak ditemukan. Ketik /start untuk memulai.")
        return ConversationHandler.END
    context.user_data["toko_nomor"] = nomor_toko
    context.user_data["toko_config"] = toko
    context.user_data["laporan_data"] = {}
    context.user_data["alur"] = get_alur_scan(toko)
    context.user_data["langkah_index"] = 0
    await query.edit_message_text(
        f"✓ Toko dipilih: *{toko['nama']}*

"
        f"Sekarang masukkan *tanggal laporan*.
"
        f"Format: `DD Bulan YYYY` (contoh: `26 Mei 2026`)

"
        f"Atau ketik `hari ini` untuk tanggal hari ini.",
        parse_mode="Markdown"
    )
    return STATE_PILIH_TANGGAL

async def pilih_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    teks = update.message.text.strip()
    if teks.lower() in ("hari ini", "today"):
        bulan_id = {1:"Januari",2:"Februari",3:"Maret",4:"April",5:"Mei",6:"Juni",
                    7:"Juli",8:"Agustus",9:"September",10:"Oktober",11:"November",12:"Desember"}
        now = datetime.now()
        tanggal = f"{now.day} {bulan_id[now.month]} {now.year}"
    else:
        tanggal = teks
    context.user_data["tanggal"] = tanggal
    toko = context.user_data["toko_config"]
    alur = context.user_data["alur"]
    total_langkah = len(alur)
    await update.message.reply_text(
        f"📅 Tanggal: *{tanggal}*
🏪 Toko: *{toko['nama']}*

"
        f"Siap! Anda akan mengirim *{total_langkah} gambar* secara berurutan.

"
        f"━━━━━━━━━━━━━━━━━━━━━
"
        f"📌 Langkah 1 dari {total_langkah}:
{alur[0]['label']}

⬇️ Kirim gambarnya sekarang...",
        parse_mode="Markdown"
    )
    return STATE_SCAN_GAMBAR

async def terima_gambar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    alur = context.user_data["alur"]
    index = context.user_data["langkah_index"]
    total = len(alur)
    langkah = alur[index]
    toko = context.user_data["toko_config"]
    tanggal = context.user_data["tanggal"]
    proses_msg = await update.message.reply_text(
        f"⏳ Memproses gambar {index + 1}/{total}...
"
        f"🔍 Sedang scan: _{langkah['label'].replace('📷 Kirim gambar ', '')}_",
        parse_mode="Markdown"
    )
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        hasil = scan_gambar(bytes(image_bytes), langkah["tipe"])
        simpan_hasil_scan(context.user_data, langkah, hasil)
        konfirmasi = _format_konfirmasi(langkah, hasil)
        await proses_msg.edit_text(
            f"✓ *Gambar {index + 1}/{total} berhasil di-scan!*

{konfirmasi}",
            parse_mode="Markdown"
        )
        index += 1
        context.user_data["langkah_index"] = index
        if index < total:
            langkah_berikut = alur[index]
            await update.message.reply_text(
                f"━━━━━━━━━━━━━━━━━━━━━
"
                f"📌 Langkah *{index + 1} dari {total}*:
{langkah_berikut['label']}

⬇️ Kirim gambarnya sekarang...",
                parse_mode="Markdown"
            )
            return STATE_SCAN_GAMBAR
        else:
            await update.message.reply_text("⏳ Membuat laporan...")
            laporan_text = generate_laporan(toko, context.user_data["laporan_data"], tanggal)
            await update.message.reply_text(
                f"🎉 *LAPORAN SELESAI!*
━━━━━━━━━━━━━━━━━━━━━
                parse_mode="Markdown"
            )
            keyboard = [
                [InlineKeyboardButton("🔄 Buat Laporan Toko Lain", callback_data="ulang")],
                [InlineKeyboardButton("✓ Selesai", callback_data="selesai")],
            ]
            await update.message.reply_text("Laporan sudah dibuat! Apa selanjutnya?",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
            return STATE_PILIH_TOKO
    except Exception as e:
        logger.error(f"Error saat scan gambar: {e}")
        await proses_msg.edit_text(
            f"✗ *Gagal memproses gambar.*

Error: `{str(e)}`

Silakan kirim ulang gambar yang sama.",
            parse_mode="Markdown"
        )
        return STATE_SCAN_GAMBAR

def _format_konfirmasi(langkah: dict, hasil: dict) -> str:
    tipe = langkah["tipe"]
    sub = langkah["sub_key"]
    lines = []
    if tipe == "kassa":
        lines.append(f"💰 Kassa {sub}: Rp. {hasil.get('total_transaksi', '-')}")
    elif tipe == "rekap_utama":
        lines.append(f"💰 Total Penjualan : Rp. {hasil.get('total_transaksi', '-')}")
        lines.append(f"💵 Tunai           : Rp. {hasil.get('tunai', '-')}")
        lines.append(f"💳 Debit           : Rp. {hasil.get('debit', '-')}")
        lines.append(f"💳 Kredit          : Rp. {hasil.get('kredit', '-') or '-'}")
    elif tipe == "ecer":
        lines.append(f"🛒 Ecer: Rp. {hasil.get('total_transaksi', '-')}")
    elif tipe == "grosir":
        lines.append(f"📦 Grosir: Rp. {hasil.get('total_transaksi', '-')}")
    elif tipe == "kasir_promo":
        lines.append(f"🎁 Total Promo : Rp. {hasil.get('total', '-')}")
        lines.append(f"💵 Tunai       : Rp. {hasil.get('tunai', '-')}")
        lines.append(f"💳 Debit       : Rp. {hasil.get('debit', '-') or '-'}")
        lines.append(f"💳 Kredit      : Rp. {hasil.get('kredit', '-') or '-'}")
    elif tipe == "parkir":
        lines.append(f"🅿️ Parkir Komputer  : Rp. {hasil.get('parkir_komputer', '-') or '-'}")
        lines.append(f"🅿️ Parkir Stor Luar : Rp. {hasil.get('parkir_stor_luar', '-')}")
        lines.append(f"🅿️ Total Parkir     : Rp. {hasil.get('total_parkir', '-')}")
    return "
".join(lines)

async def callback_ulang_selesai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "ulang":
        keyboard = []
        for nomor, toko in TOKO_LIST.items():
            keyboard.append([InlineKeyboardButton(f"{nomor}. {toko['nama']}", callback_data=f"toko_{nomor}")])
        keyboard.append([InlineKeyboardButton("✗ Batal", callback_data="batal")])
        await query.edit_message_text(
            "🏪 *REKAP LAPORAN PENJUALAN*

Pilih toko yang ingin dibuat laporannya:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return STATE_PILIH_TOKO
    else:
        await query.edit_message_text("✓ Terima kasih! Ketik /start untuk membuat laporan baru.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("✗ Sesi dibatalkan.
Ketik /start untuk memulai lagi.",
                                    reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *PANDUAN PENGGUNAAN BOT LAPORAN*

"
        "1️⃣ Ketik /start untuk mulai
"
        "2️⃣ Pilih nama toko dari daftar
"
        "3️⃣ Masukkan tanggal laporan
"
        "4️⃣ Kirim gambar satu per satu sesuai instruksi bot
"
        "5️⃣ Bot akan otomatis scan & buat laporan

"
        "✗ Ketik /cancel untuk membatalkan sesi.",
        parse_mode="Markdown"
    )

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("✗ TELEGRAM_BOT_TOKEN belum diisi di file .env!")
    if not GEMINI_API_KEY:
        raise ValueError("✗ GEMINI_API_KEY belum diisi di file .env!")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_PILIH_TOKO: [
                CallbackQueryHandler(pilih_toko, pattern=r"^toko_\d+$"),
                CallbackQueryHandler(callback_ulang_selesai, pattern=r"^(ulang|selesai|batal)$"),
            ],
            STATE_PILIH_TANGGAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_tanggal)],
            STATE_SCAN_GAMBAR: [MessageHandler(filters.PHOTO, terima_gambar)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("bantuan", bantuan))
    app.add_handler(CommandHandler("help", bantuan))
    logger.info("🤖 Bot Laporan Penjualan mulai berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

