import os
import json
import mimetypes
from datetime import date

from google import genai
from google.genai import types

from database import get_transactions, get_summary, add_transaction


MODEL_NAME = "gemini-3-flash-preview"


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise Exception(
            "GEMINI_API_KEY belum diatur. "
            "Jalankan dulu di terminal: $env:GEMINI_API_KEY='API_KEY_KAMU'"
        )

    return genai.Client(api_key=api_key)


def ai_spending_advice():
    client = get_gemini_client()

    summary = get_summary()
    rows = list(get_transactions())[:50]

    transactions = []

    for row in rows:
        transactions.append({
            "date": row["date"],
            "type": row["type"],
            "store_name": row["store_name"],
            "amount": row["amount"],
            "category": row["category"],
            "note": row["note"],
        })

    prompt = f"""
Kamu adalah AI financial assistant untuk aplikasi expense tracker.

Tugas:
1. Analisis kebiasaan pengeluaran user.
2. Jelaskan total income, expense, dan balance.
3. Jelaskan kategori pengeluaran terbesar.
4. Beri saran hemat yang realistis.
5. Kalau expense lebih besar dari income, beri warning.
6. Jawab dalam bahasa Indonesia.
7. Jawaban singkat tapi jelas.

Data summary:
{json.dumps(summary, indent=2, ensure_ascii=False)}

Data transaksi:
{json.dumps(transactions, indent=2, ensure_ascii=False)}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


def ai_read_receipt(image_path):
    client = get_gemini_client()

    mime_type, _ = mimetypes.guess_type(image_path)

    if mime_type is None:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as file:
        image_bytes = file.read()

    prompt = f"""
Baca gambar struk ini dan ambil data transaksi.

Balas hanya JSON valid seperti format ini:
{{
  "store_name": "nama toko",
  "amount": 0,
  "category": "Food",
  "note": "ringkasan singkat",
  "date": "YYYY-MM-DD",
  "type": "expense"
}}

Aturan:
- amount harus angka total pembayaran.
- category pilih salah satu:
  Food, Transport, Shopping, Bills, Health, Entertainment, Education, Other.
- Kalau tanggal tidak terbaca, gunakan tanggal hari ini: {date.today().isoformat()}.
- type selalu "expense".
- Jangan kasih penjelasan tambahan di luar JSON.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
        ],
        config={
            "response_mime_type": "application/json"
        }
    )

    data = json.loads(response.text)

    if not data.get("store_name"):
        data["store_name"] = "Unknown Store"

    if not data.get("amount"):
        data["amount"] = 0

    if not data.get("category"):
        data["category"] = "Other"

    if not data.get("note"):
        data["note"] = "Added by AI receipt scanner"

    if not data.get("date"):
        data["date"] = date.today().isoformat()

    data["type"] = "expense"

    return data


def ai_add_receipt_to_database(image_path):
    data = ai_read_receipt(image_path)

    add_transaction(
        store_name=data["store_name"],
        amount=float(data["amount"]),
        category=data["category"],
        note=data["note"],
        date=data["date"],
        trans_type=data["type"],
        receipt_image=image_path
    )

    return data