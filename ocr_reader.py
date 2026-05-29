import re
import io
import json

import google.generativeai as genai
import PIL.Image

from config import GEMINI_API_KEY

def _get_model():
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-1.5-flash")

def _clean_number(text: str) -> str:
    if not text:
        return "0"
    cleaned = re.sub(r"[^\d]", "", str(text))
    return cleaned if cleaned else "0"

def _format_rupiah(value: str) -> str:
    try:
        num = int(value)
        return f"{num:,}".replace(",", ".")
    except Exception:
        return value

def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}

def scan_gambar(image_bytes: bytes, tipe_scan: str) -> dict:
    image = PIL.Image.open(io.BytesIO(image_bytes))
    model = _get_model()

    if tipe_scan in ("kassa", "ecer", "grosir"):
        prompt = (
            "Lihat gambar laporan penjualan harian ini.
"
            "Cari baris TOTAL pada tabel.
"
            "Ambil angka kolom Total Transaksi dari baris TOTAL.

"
            "Balas HANYA JSON ini:
"
            '{"total_transaksi": "15741500"}

'
            "Angka hanya digit tanpa titik atau koma."
        )
        resp = model.generate_content([prompt, image])
        data = _parse_json(resp.text)
        return {
            "total_transaksi": _format_rupiah(
                _clean_number(data.get("total_transaksi", "0"))
            )
        }

    elif tipe_scan == "rekap_utama":
        prompt = (
            "Lihat gambar laporan penjualan harian ini.
"
            "Cari baris TOTAL pada tabel.
"
            "Ambil angka dari kolom:
"
            "1. Total Transaksi
"
            "2. Jml Bayar Tunai
"
            "3. Jml Bayar K.Debit
"
            "4. Jml Bayar K.Kredit (isi 0 jika tidak ada)

"
            "Balas HANYA JSON ini:
"
            '{"total_transaksi":"15741500","tunai":"11714500",'
            '"debit":"4016000","kredit":"0"}

'
            "Angka hanya digit tanpa titik atau koma. Jika kosong isi 0."
        )
        resp = model.generate_content([prompt, image])
        data = _parse_json(resp.text)
        return {
            "total_transaksi": _format_rupiah(
                _clean_number(data.get("total_transaksi", "0"))
            ),
            "tunai": _format_rupiah(_clean_number(data.get("tunai", "0"))),
            "debit": _format_rupiah(_clean_number(data.get("debit", "0"))),
            "kredit": _format_rupiah(_clean_number(data.get("kredit", "0"))),
        }

    elif tipe_scan == "kasir_promo":
        prompt = (
            "Lihat gambar laporan kasir promo ini.
"
            "Ambil total penjualan, tunai, debit, kredit.

"
            "Balas HANYA JSON ini:
"
            '{"total":"1675000","tunai":"1675000","debit":"0","kredit":"0"}

'
            "Angka hanya digit. Jika tidak ada isi 0."
        )
        resp = model.generate_content([prompt, image])
        data = _parse_json(resp.text)
        return {
            "total": _format_rupiah(_clean_number(data.get("total", "0"))),
            "tunai": _format_rupiah(_clean_number(data.get("tunai", "0"))),
            "debit": _format_rupiah(_clean_number(data.get("debit", "0"))),
            "kredit": _format_rupiah(_clean_number(data.get("kredit", "0"))),
        }

    elif tipe_scan == "parkir":
        prompt = (
            "Lihat gambar laporan parkir ini.
"
            "Ambil: Parkir di Komputer, Parkir Stor Luar, Total Parkir.

"
            "Balas HANYA JSON ini:
"
            '{"parkir_komputer":"0","parkir_stor_luar":"369500",'
            '"total_parkir":"369500"}

'
            "Angka hanya digit. Jika tidak ada isi 0."
        )
        resp = model.generate_content([prompt, image])
        data = _parse_json(resp.text)
        return {
            "parkir_komputer": _format_rupiah(
                _clean_number(data.get("parkir_komputer", "0"))
            ),
            "parkir_stor_luar": _format_rupiah(
                _clean_number(data.get("parkir_stor_luar", "0"))
            ),
            "total_parkir": _format_rupiah(
                _clean_number(data.get("total_parkir", "0"))
            ),
        }

    return {}
