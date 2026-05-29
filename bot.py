import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
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

STATE_PILIH_TOKO, STATE_PILIH_TANGGAL, STATE_SCAN_GAMBAR = range(3)

def get_alur_scan(toko_config):
    fmt = toko_config["format"]
    alur = []
    if fmt == "central_alak":
        alur.append({"label": "Kirim gambar KASSA 1", "tipe": "kassa", "sub_key": 1})
        alur.append({"label": "Kirim gambar KASSA 2", "tipe": "kassa", "sub_key": 2})
        alur.append({"label": "Kirim gambar KASSA 3", "tipe": "kassa", "sub_key": 3})
        alur.append({"label": "Kirim gambar KASSA 4", "tipe": "kassa", "sub_key": 4})
        alur.append({"label": "Kirim gambar REKAP UTAMA", "tipe": "rekap_utama", "sub_key": None})
        alur.append({"label": "Kirim gambar ECER", "tipe": "ecer", "sub_key": None})
        alur.append({"label": "Kirim gambar GROSIR", "tipe": "grosir", "sub_key": None})
        alur.append({"label": "Kirim gambar KASIR PROMO", "tipe": "kasir_promo", "sub_key": None})
        alur.append({"label": "Kirim gambar LAPORAN PARKIR", "tipe": "parkir", "sub_key": None})
    elif fmt == "nasional_kitchen":
        alur.append({"label": "Kirim gambar KASSA 1", "tipe": "kassa", "sub_key": 1})
        alur.append({"label": "Kirim gambar KASSA 2", "tipe": "kassa", "sub_key": 2})
        alur.append({"label": "Kirim gambar REKAP UTAMA", "tipe": "rekap_utama", "sub_key": None})
        alur.append({"label": "Kirim gambar ECER", "tipe": "ecer", "sub_key": None})
        alur.append({"label": "Kirim gambar GROSIR", "tipe": "grosir", "sub_key": None})
    else:
        alur.append({"label": "Kirim gambar KASSA 1", "tipe": "kassa", "sub_key": 1})
        alur.append({"label": "Kirim gambar KASSA 2", "tipe": "kassa", "sub_key": 2})
        alur.append({"label": "Kirim gambar REKAP UTAMA", "tipe": "rekap_utama", "sub_key": None})
    return alur

def simpan_hasil(user_data, langkah, hasil):
    tipe = langkah["tipe"]
    sub_key = langkah["sub_key"]
    d = user_data.setdefault("laporan_data", {})
    if tipe == "kassa":
        d.setdefault("kassa", {})[sub_key] = hasil.get("total_transaksi", "-")
    elif tipe == "rekap_utama":
        d["total_penjualan"] = hasil.get("total_transaksi", "-")
        d["tunai"] = hasil.get("tunai", "-")
        d["debit"] = hasil.get("debit", "-")
        d["kredit"] = hasil.get("kredit", "")
    elif tipe == "ecer":
        d["ecer"] = hasil.get("total_transaksi", "-")
    elif tipe == "grosir":
        d["grosir"] = hasil.get("total_transaksi", "-")
    elif tipe == "kasir_promo":
        d["kasir_promo"] = {
            "total": hasil.get("total", "-"),
            "tunai": hasil.get("tunai", "-"),
            "debit": hasil.get("debit", ""),
            "kredit": hasil.get("kredit", ""),
        }
    elif tipe == "parkir":
        d["parkir"] = {
            "parkir_komputer": hasil.get("parkir_komputer", ""),
            "parkir_stor_luar": hasil.get("parkir_stor_luar", "-"),
            "total_parkir": hasil.get("total_parkir", "-"),
        }

def format_konfirmasi(langkah, hasil):
    tipe = langkah["tipe"]
    sub = langkah["sub_key"]
    if tipe == "kassa":
        return "Kassa {}: Rp. {}".format(sub, hasil.get("total_transaksi", "-"))
    elif tipe == "rekap_utama":
        return "Total: Rp. {}
Tunai: Rp. {}
Debit: Rp. {}
Kredit: Rp. {}".format(
            hasil.get("total_transaksi", "-"),
            hasil.get("tunai", "-"),
            hasil.get("debit", "-"),
            hasil.get("kredit", "-") or "-"
        )
    elif tipe == "ecer":
        return "Ecer: Rp. {}".format(hasil.get("total_transaksi", "-"))
    elif tipe == "grosir":
        return "Grosir: Rp. {}".format(hasil.get("total_transaksi", "-"))
    elif tipe == "kasir_promo":
        return "Promo Total: Rp. {}
Tunai: Rp. {}".format(
            hasil.get("total", "-"), hasil.get("tunai", "-")
        )
    elif tipe == "parkir":
        return "Total Parkir: Rp. {}".format(hasil.get("total_parkir", "-"))
    return ""

def menu_toko():
    kb = []
    for n, t in TOKO_LIST.items():
        kb.append([InlineKeyboardButton("{}. {}".format(n, t["nama"]), callback_data="toko_{}".format(n))])
    kb.append([InlineKeyboardButton("Batal", callback_data="batal")])
    return InlineKeyboardMarkup(kb)

async def start(update, context):
    context.user_data.clear()
    await update.message.reply_text(
        "REKAP LAPORAN PENJUALAN

Pilih toko:",
        reply_markup=menu_toko()
    )
    return STATE_PILIH_TOKO

async def pilih_toko(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "batal":
        await q.edit_message_text("Dibatalkan. Ketik /start untuk mulai lagi.")
        return ConversationHandler.END
    nomor = q.data.replace("toko_", "")
    toko = TOKO_LIST.get(nomor)
    if not toko:
        await q.edit_message_text("Toko tidak ditemukan.")
        return ConversationHandler.END
    context.user_data["toko_config"] = toko
    context.user_data["laporan_data"] = {}
    context.user_data["alur"] = get_alur_scan(toko)
    context.user_data["langkah_index"] = 0
    await q.edit_message_text(
        "Toko: {}

Masukkan tanggal laporan.
Contoh: 29 Mei 2026
Atau ketik: hari ini".format(
            toko["nama"]
        )
    )
    return STATE_PILIH_TANGGAL

async def pilih_tanggal(update, context):
    teks = update.message.text.strip()
    bulan = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    if teks.lower() in ("hari ini", "today"):
        now = datetime.now()
        tanggal = "{} {} {}".format(now.day, bulan[now.month], now.year)
    else:
        tanggal = teks
    context.user_data["tanggal"] = tanggal
    alur = context.user_data["alur"]
    toko = context.user_data["toko_config"]
    await update.message.reply_text(
        "Tanggal: {}
Toko: {}

Total {} gambar yang perlu dikirim.

Langkah 1 dari {}:
{}

Kirim gambarnya sekarang...".format(
            tanggal, toko["nama"], len(alur), len(alur), alur[0]["label"]
        )
    )
    return STATE_SCAN_GAMBAR

async def terima_gambar(update, context):
    alur = context.user_data["alur"]
    index = context.user_data["langkah_index"]
    total = len(alur)
    langkah = alur[index]
    msg = await update.message.reply_text(
        "Memproses gambar {}/{}...".format(index + 1, total)
    )
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())
        hasil = scan_gambar(image_bytes, langkah["tipe"])
        simpan_hasil(context.user_data, langkah, hasil)
        await msg.edit_text(
            "Gambar {}/{} berhasil!

{}".format(
                index + 1, total, format_konfirmasi(langkah, hasil)
            )
        )
        index += 1
        context.user_data["langkah_index"] = index
        if index < total:
            await update.message.reply_text(
                "Langkah {} dari {}:
{}

Kirim gambarnya...".format(
                    index + 1, total, alur[index]["label"]
                )
            )
            return STATE_SCAN_GAMBAR
        else:
            await update.message.reply_text("Membuat laporan...")
            laporan = generate_laporan(
                context.user_data["toko_config"],
                context.user_data["laporan_data"],
                context.user_data["tanggal"]
            )
            await update.message.reply_text(
                "LAPORAN SELESAI!

{}".format(laporan)
            )
            kb = [
                [InlineKeyboardButton("Buat Laporan Toko Lain", callback_data="ulang")],
                [InlineKeyboardButton("Selesai", callback_data="selesai")],
            ]
            await update.message.reply_text(
                "Apa selanjutnya?",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            return STATE_PILIH_TOKO
    except Exception as e:
        logger.error("Error: {}".format(e), exc_info=True)
        await msg.edit_text(
            "Gagal memproses gambar.
Error: {}

Coba kirim ulang gambar yang sama.".format(str(e))
        )
        return STATE_SCAN_GAMBAR

async def callback_setelah_laporan(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "ulang":
        context.user_data.clear()
        await q.edit_message_text("Pilih toko:", reply_markup=menu_toko())
        return STATE_PILIH_TOKO
    await q.edit_message_text("Selesai! Ketik /start untuk laporan baru.")
    return ConversationHandler.END

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text(
        "Dibatalkan. Ketik /start untuk mulai lagi.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def bantuan(update, context):
    await update.message.reply_text(
        "/start - Buat laporan baru
/cancel - Batalkan sesi
/bantuan - Panduan ini"
    )

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_PILIH_TOKO: [
                CallbackQueryHandler(pilih_toko, pattern=r"^toko_\d+$"),
                CallbackQueryHandler(callback_setelah_laporan, pattern=r"^(ulang|selesai|batal)$"),
            ],
            STATE_PILIH_TANGGAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_tanggal)
            ],
            STATE_SCAN_GAMBAR: [
                MessageHandler(filters.PHOTO, terima_gambar)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("bantuan", bantuan))
    app.add_handler(CommandHandler("help", bantuan))
    logger.info("Bot mulai berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
