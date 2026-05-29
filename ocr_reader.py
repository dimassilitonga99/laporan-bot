"""
ocr_reader.py
Membaca gambar laporan kasir menggunakan Google Gemini Vision (GRATIS)
dan mengekstrak angka yang dibutuhkan.
"""

import re
import google.generativeai as genai
from config import GEMINI_API_KEY

# Inisialisasi Gemini - lazy init
_model = None

def get_model():
    global _model
    if _model is None:
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
    return _model

def _clean_number(text: str) -> str:
    """Bersihkan string angka: hapus titik pemisah ribuan, spasi, dsb."""
    if not text:
        return "0"
    cleaned = re.sub(r"[^\d,]", "", text.replace(".", ""))
    cleaned = cleaned.replace(",", ".")
    return cleaned if cleaned else "0"

def _format_rupiah(value: str) -> str:
    """Format angka menjadi format Rupiah: 1.234.500"""
    try:
        num = float(value)
        if num == int(num):
            num = int(num)
            return f"{num:,}".replace(",", ".")
        else:
            return f"{num:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return value

def scan_gambar(image_bytes: bytes, tipe_scan: str) -> dict:
    import PIL.Image
    import io

    image = PIL.Image.open(io.BytesIO(image_bytes))

    if tipe_scan in ("kassa", "ecer", "grosir"):
        prompt = """
Lihat gambar laporan penjualan harian ini dengan seksama.
Cari baris yang bertuliskan "TOTAL :" atau "Total" pada tabel.
Ambil angka pada kolom "Total Transaksi" dari baris TOTAL tersebut.
Jika ada beberapa baris, ambil dari baris TOTAL paling bawah.

Jawab HANYA dengan format JSON seperti ini (tanpa teks lain):
{"total_transaksi": "15741500"}

Angka tanpa titik, tanpa koma, tanpa spasi, hanya digit.
"""
        response = model.generate_content([prompt, image])
        data = _parse_json_response(response.text)
        return {
            "total_transaksi": _format_rupiah(_clean_number(data.get("total_transaksi", "0")))
        }

    elif tipe_scan == "rekap_utama":
        prompt = """
Lihat gambar laporan penjualan harian ini dengan seksama.
Tabel memiliki kolom: Tanggal, Jml Trs, Total Transaksi, Jml Bayar Tunai, Jml Bayar Kredit, Jml Bayar K.Debit, Jml Bayar K.Kredit

Cari baris yang bertuliskan "TOTAL :" dan ambil angka dari kolom-kolom berikut:
1. Total Transaksi
2. Jml Bayar Tunai
3. Jml Bayar K.Debit (atau Jml Bayar Debit)
4. Jml Bayar K.Kredit (atau Jml Bayar Kredit) - jika ada, jika tidak ada isi 0

Jawab HANYA dengan format JSON seperti ini (tanpa teks lain):
{
  "total_transaksi": "15741500",
  "tunai": "11714500",
  "debit": "4016000",
  "kredit": "0"
}

Semua angka tanpa titik, tanpa koma, tanpa spasi, hanya digit murni.
Jika suatu kolom tidak ada atau kosong, isi "0".
"""
        response = model.generate_content([prompt, image])
        data = _parse_json_response(response.text)
        return {
            "total_transaksi": _format_rupiah(_clean_number(data.get("total_transaksi", "0"))),
            "tunai": _format_rupiah(_clean_number(data.get("tunai", "0"))),
            "debit": _format_rupiah(_clean_number(data.get("debit", "0"))),
            "kredit": _format_rupiah(_clean_number(data.get("kredit", "0"))),
        }

    elif tipe_scan == "kasir_promo":
        prompt = """
Lihat gambar ini. Ini adalah laporan kasir promo.
Cari total penjualan keseluruhan, dan rincian pembayaran tunai, debit, kredit.

Jawab HANYA dengan format JSON seperti ini:
{
  "total": "1675000",
  "tunai": "1675000",
  "debit": "0",
  "kredit": "0"
}

Angka tanpa titik, tanpa koma, hanya digit. Jika tidak ada isi "0".
"""
        response = model.generate_content([prompt, image])
        data = _parse_json_response(response.text)
        return {
            "total": _format_rupiah(_clean_number(data.get("total", "0"))),
            "tunai": _format_rupiah(_clean_number(data.get("tunai", "0"))),
            "debit": _format_rupiah(_clean_number(data.get("debit", "0"))),
            "kredit": _format_rupiah(_clean_number(data.get("kredit", "0"))),
        }

    elif tipe_scan == "parkir":
        prompt = """
Lihat gambar ini. Ini adalah laporan parkir.
Cari angka untuk:
1. Parkir di Komputer
2. Parkir Stor Luar
3. Total Parkir

Jawab HANYA dengan format JSON seperti ini:
{
  "parkir_komputer": "0",
  "parkir_stor_luar": "369500",
  "total_parkir": "369500"
}

Angka tanpa titik, tanpa koma, hanya digit. Jika tidak ada atau kosong isi "0".
"""
        response = model.generate_content([prompt, image])
        data = _parse_json_response(response.text)
        return {
            "parkir_komputer": _format_rupiah(_clean_number(data.get("parkir_komputer", "0"))),
            "parkir_stor_luar": _format_rupiah(_clean_number(data.get("parkir_stor_luar", "0"))),
            "total_parkir": _format_rupiah(_clean_number(data.get("total_parkir", "0"))),
        }

    else:
        return {}

def _parse_json_response(text: str) -> dict:
    """Parse respons JSON dari Gemini dengan aman."""
    import json
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text.strip())
    except Exception:
        return {}
