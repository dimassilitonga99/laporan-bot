"""
report_generator.py
Menghasilkan teks laporan berformat siap pakai untuk setiap toko.
"""

from datetime import datetime
from config import KASIR_CENTRAL

def _rp(nilai: str) -> str:
    if not nilai or nilai == "0":
        return ""
    return nilai

def generate_laporan_central_alak(data: dict, tanggal: str) -> str:
    kassa = data.get("kassa", {})
    promo = data.get("kasir_promo", {})
    parkir = data.get("parkir", {})

    kassa_lines = []
    for i in range(1, 5):
        nama_kasir = KASIR_CENTRAL.get(i, f"Kasir {i}")
        nilai = kassa.get(i, "")
        kassa_lines.append(f"Kassa {i} ({nama_kasir}) Rp. {nilai}" if nilai else f"Kassa {i} ({nama_kasir}) Rp. -")

    lap = f"""Laporan Penjualan Toko Central Perabot {tanggal}

{chr(10).join(kassa_lines)}

Total Penjualan Keseluruhan: Rp.{data.get('total_penjualan', '-')}
--------------------------------------------

Tunai  Rp. {data.get('tunai', '-')}
Debit  Rp.{data.get('debit', '-')}
Credit Rp. {data.get('kredit', '') or '-'}
--------------------------------------------
--------------------------------------------

Ecer: Rp. {data.get('ecer', '-')}
Grosir : Rp. {data.get('grosir', '-')}

--------------------------------------------

Laporan Penjualan Kasir Promo
Periode {tanggal}

Total Penjualan Keseluruhan: Rp. {promo.get('total', '-')}
--------------------------------------------

Tunai  Rp. {promo.get('tunai', '-')}
Debit  Rp. {promo.get('debit', '') or '-'}
Credit Rp. {promo.get('kredit', '') or '-'}

--------------------------------------------

Laporan Parkir
Periode {tanggal}

Parkir di Komputer : Rp. {parkir.get('parkir_komputer', '') or '-'}
Parkir Stor Luar : Rp.{parkir.get('parkir_stor_luar', '-')}
--------------------------------------------

Total Parkir  Rp. {parkir.get('total_parkir', '-')}

--------------------------------------------"""
    return lap

def generate_laporan_nasional_kitchen(data: dict, tanggal: str) -> str:
    kassa = data.get("kassa", {})
    lap = f"""Laporan Penjualan
Toko Nasional Kitchen
Periode {tanggal}

Kassa 1 Rp. {kassa.get(1, '-')}
Kassa 2 Rp. {kassa.get(2, '-')}

Total Penjualan Keseluruhan
Rp. {data.get('total_penjualan', '-')}
--------------------------------------------

Tunai Rp. {data.get('tunai', '-')}
Debit  Rp. {data.get('debit', '-')}
Credit Rp. {data.get('kredit', '') or '-'}

Ecer : {data.get('ecer', '-')}
Grosir : {data.get('grosir', '-')}"""
    return lap

def generate_laporan_mama_simple(data: dict, nama_toko: str, tanggal: str) -> str:
    kassa = data.get("kassa", {})
    lap = f"""Laporan Penjualan
{nama_toko}
Periode {tanggal}

Kassa 1 Rp. {kassa.get(1, '-')}
Kassa 2 Rp. {kassa.get(2, '-')}

Total Penjualan Keseluruhan
Rp. {data.get('total_penjualan', '-')}
--------------------------------------------

Tunai  Rp. {data.get('tunai', '-')}
Debit  Rp. {data.get('debit', '-')}
Credit Rp. {data.get('kredit', '') or '-'}"""
    return lap

def generate_laporan(toko_config: dict, data: dict, tanggal: str) -> str:
    fmt = toko_config.get("format", "mama_simple")
    nama = toko_config.get("nama", "Toko")
    if fmt == "central_alak":
        return generate_laporan_central_alak(data, tanggal)
    elif fmt == "nasional_kitchen":
        return generate_laporan_nasional_kitchen(data, tanggal)
    else:
        return generate_laporan_mama_simple(data, nama, tanggal)
