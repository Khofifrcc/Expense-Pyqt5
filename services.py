import os
import re
import cv2
from datetime import datetime
import json
from database import get_transactions

def get_gemini_client():
    try:
        from google import genai
    except Exception:
        raise Exception(
            "Library google-genai belum terinstall. "
            "Jalankan: python -m pip install -U google-genai"
        )

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise Exception(
            "GEMINI_API_KEY belum diatur. "
            "Jalankan di terminal: $env:GEMINI_API_KEY='API_KEY_KAMU'"
        )

    return genai.Client(api_key=api_key)

try:
    import easyocr
except Exception:
    easyocr = None

_reader = None


def get_reader():
    global _reader
    if easyocr is None:
        return None
    if _reader is None:
        _reader = easyocr.Reader(["en", "tr"], gpu=False)
    return _reader


def preprocess_receipt_image(filepath):
    image = cv2.imread(filepath)
    if image is None:
        return filepath

    h, w = image.shape[:2]

    # Receipt text is often too small from webcam. Upscale first, but do not make it huge.
    target_width = 1400
    if w < target_width:
        scale = target_width / w
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    elif w > 1800:
        scale = 1800 / w
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Sharpen + adaptive threshold helps Turkish receipt text.
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    sharp = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)
    processed = cv2.adaptiveThreshold(
        sharp,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9,
    )

    processed_path = os.path.join(
        os.path.dirname(filepath),
        "processed_" + os.path.basename(filepath),
    )
    cv2.imwrite(processed_path, processed)
    return processed_path


def normalize_text(value):
    value = value.lower()
    replacements = {
        "ı": "i",
        "İ": "i",
        "ö": "o",
        "ü": "u",
        "ş": "s",
        "ğ": "g",
        "ç": "c",
        "@": "o",
        "0": "o",
        "€": "e",
        "$": "s",
        "|": "i",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def clean_display_name(value):
    value = value.strip()
    value = value.replace("@", "O")
    value = re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü0-9\s&.'-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def is_bad_store_candidate(line):
    raw = line.strip()
    norm = normalize_text(raw)

    if len(norm) < 3:
        return True

    # Do not use receipt labels / product / payment rows as store name.
    blocked_words = [
        "fis", "fisi", "no", "masa", "paket", "tutar", "toplam", "tahsilat",
        "nakit", "kart", "kdv", "urun", "adet", "fiyat", "tavuk", "durum",
        "ayran", "tesekkur", "ederiz", "tesekkurler", "kasiyer", "saat",
        "tarih", "telefon", "tel", "vergi", "sube",
    ]
    if any(word in norm.split() for word in blocked_words):
        return True

    if re.search(r"\d{2}[./-]\d{2}", raw):
        return True

    if re.search(r"\d+[.,]\d{2}", raw):
        return True

    # OCR garbage like P@Nebve should not be accepted as store.
    weird_count = len(re.findall(r"[^A-Za-zÇĞİÖŞÜçğıöşü0-9\s&.'-]", raw))
    if weird_count >= 1 and len(raw) <= 12:
        return True

    # Mostly numbers/symbols = bad.
    letters = len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", raw))
    if letters < 3:
        return True

    return False


def extract_store_name(text_lines):
    joined_norm = normalize_text(" ".join(text_lines))

    # Strong merchant detection first.
    known_store_map = {
        "migros": "Migros",
        "sok": "ŞOK",
        "a101": "A101",
        "bim": "BİM",
        "carrefour": "Carrefour",
        "starbucks": "Starbucks",
        "mcdonald": "McDonald's",
        "burger king": "Burger King",
        "kfc": "KFC",
        "dominos": "Domino's",
    }

    for key, display in known_store_map.items():
        if key in joined_norm:
            return display

    # Current receipt/food receipt detection. OCR may read ÖNÖ as QNO/ONO/0NO.
    doner_clues = [
        "doner", "d ner", "tavuk durum", "durum", "ayran", "masa no paket",
        "ono doner", "qno doner", "ono doner", "oncu doner", "oncu",
        # OCR variants from webcam scans, e.g. ÖNÖ DÖNER can become @NGO / P@NER / PONER.
        "ngo", "poner", "p ner", "knori",
    ]
    if any(clue in joined_norm for clue in doner_clues):
        if any(clue in joined_norm for clue in ["ono", "qno", "oncu", "doner", "ngo", "poner", "p ner"]):
            return "ÖNÖ DÖNER"
        return "Döner Restaurant"

    # Look at upper receipt lines only and select a clean title-looking line.
    candidates = []
    for line in text_lines[:10]:
        if is_bad_store_candidate(line):
            continue

        cleaned = clean_display_name(line)
        norm = normalize_text(cleaned)

        score = 0
        if len(cleaned) >= 4:
            score += 1
        if cleaned.isupper():
            score += 1
        if any(word in norm for word in ["market", "cafe", "restoran", "restaurant", "doner", "döner"]):
            score += 3
        if len(cleaned.split()) <= 4:
            score += 1

        candidates.append((score, cleaned))

    if candidates:
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1].title()

    return "Unknown Store"


def extract_date(text_lines):
    joined = " ".join(text_lines)

    # Examples: 28.03.2026, 28/03/2026, 28-03-26, OCR may read dots as commas: 20,03,2020.
    patterns = [
        r"(\d{1,2})\s*[,./-]\s*(\d{1,2})\s*[,./-]\s*(\d{4})",
        r"(\d{1,2})\s*[,./-]\s*(\d{1,2})\s*[,./-]\s*(\d{2})",
    ]

    current_year = datetime.today().year

    for pattern in patterns:
        for match in re.finditer(pattern, joined):
            day, month, year = match.groups()
            day = day.zfill(2)
            month = month.zfill(2)
            if len(year) == 2:
                year = "20" + year

            try:
                year_int = int(year)

                # Webcam OCR often reads the last digit of the year incorrectly.
                # For demo/current receipts, avoid returning very old years like 2020 when the app is used in 2026.
                if year_int < current_year - 3:
                    year = str(current_year)
                elif year_int > current_year + 1:
                    year = str(current_year)

                return datetime.strptime(f"{day}.{month}.{year}", "%d.%m.%Y").strftime("%Y-%m-%d")
            except ValueError:
                pass

    return datetime.today().strftime("%Y-%m-%d")


def parse_price(value):
    value = value.strip().replace(" ", "")
    value = value.replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def extract_total(text_lines):
    lines = [line.strip() for line in text_lines if line.strip()]
    joined = " ".join(lines)

    # Prefer payment/total labels common in Turkish receipts.
    total_keywords = [
        "tahsilat", "toplam", "genel toplam", "tutar", "ara toplam",
        "nakit", "kredi", "kart", "total", "amount",
    ]

    keyword_prices = []
    for line in lines:
        norm = normalize_text(line)
        if any(key in norm for key in total_keywords):
            prices = re.findall(r"(\d{1,6}[.,]\d{2})", line)
            for price in prices:
                parsed = parse_price(price)
                if parsed is not None:
                    keyword_prices.append(parsed)

            # OCR sometimes splits 130.00 into 130 00
            split_match = re.search(r"(\d{1,6})\s+(\d{2})", line)
            if split_match:
                parsed = parse_price(f"{split_match.group(1)}.{split_match.group(2)}")
                if parsed is not None:
                    keyword_prices.append(parsed)

    if keyword_prices:
        return max(keyword_prices)

    all_prices = []
    for price in re.findall(r"(\d{1,6}[.,]\d{2})", joined):
        parsed = parse_price(price)
        if parsed is not None:
            all_prices.append(parsed)

    if all_prices:
        # Usually total is the biggest price on a small receipt.
        return max(all_prices)

    return 0.0


def suggest_category(store_name, note=""):
    text = normalize_text(f"{store_name} {note}")

    if any(x in text for x in ["sok", "a101", "bim", "migros", "carrefour", "market", "grocery"]):
        return "Grocery"
    if any(x in text for x in [
        "cafe", "kahve", "coffee", "restaurant", "restoran", "burger",
        "pizza", "food", "yemek", "doner", "durum", "tavuk", "ayran",
        "mcdonald", "kfc", "starbucks",
    ]):
        return "Food"
    if any(x in text for x in ["otobus", "metro", "taksi", "taxi", "transport", "ulasim", "bus"]):
        return "Transport"
    if any(x in text for x in ["burs", "scholarship", "allowance"]):
        return "Allowance"
    if any(x in text for x in ["salary", "maas", "gaji"]):
        return "Salary"
    if any(x in text for x in ["shop", "shopping", "alisveris"]):
        return "Shopping"

    return "Other"


def scan_receipt(filepath):
    reader = get_reader()
    if reader is None:
        return {
            "store_name": "Unknown Store",
            "date": datetime.today().strftime("%Y-%m-%d"),
            "amount": 0.0,
            "category": "Other",
            "ocr_text": "EasyOCR/Torch belum aktif. Isi data manual dulu.",
        }

    processed = preprocess_receipt_image(filepath)

    try:
        results = reader.readtext(processed, detail=0, paragraph=False)
    except TypeError:
        results = reader.readtext(processed, detail=0)

    lines = [str(x).strip() for x in results if str(x).strip()]

    store_name = extract_store_name(lines)
    date = extract_date(lines)
    amount = extract_total(lines)

    # Use OCR text too for category because product line can reveal category.
    category = suggest_category(store_name, " ".join(lines))

    return {
        "store_name": store_name,
        "date": date,
        "amount": amount,
        "category": category,
        "ocr_text": "\n".join(lines),
    }


def advisor_reply(summary, message):
    try:
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            return (
                "AI Advisor belum tersambung. "
                "GEMINI_API_KEY belum diatur di terminal."
            )

        client = genai.Client(api_key=api_key)

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
You are an AI financial advisor for the Quick Expense Tracker app.

Answer the user's question based on the transaction data.
Detect the language of the user's question and reply only in the same language.

Language rules:
- If the user asks in English, reply only in English.
- If the user asks in Indonesian, reply only in Indonesian.
- If the user asks in Turkish, reply only in Turkish.
- Do not use Indonesian unless the user's question is in Indonesian.

Currency rules:
- All money amounts in this app are in Turkish Lira.
- Always display money using TL or ₺.
- Example: write ₺580 or 580 TL, not $580.
- Never use dollars, USD, or $ unless the user explicitly asks for it.


Keep the answer short, clear, natural, and realistic.

User question:
{message}

Data summary:
{json.dumps(summary, indent=2, ensure_ascii=False)}

Data transaksi:
{json.dumps(transactions, indent=2, ensure_ascii=False)}
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"AI Advisor error: {str(e)}"
    
def parse_voice_transaction(text: str):
    text_lower = normalize_text(text)

    trans_type = "expense"
    if any(word in text_lower for word in ["income", "salary", "gaji", "maas"]):
        trans_type = "income"

    amount = None
    amount_match = re.search(r"(\d+[.,]?\d{0,2})", text_lower)
    if amount_match:
        try:
            amount = float(amount_match.group(1).replace(",", "."))
        except ValueError:
            amount = None

    category = "AUTO"
    if any(word in text_lower for word in ["market", "migros", "bim", "a101", "sok", "grocery"]):
        category = "Grocery"
    elif any(word in text_lower for word in ["coffee", "kahve", "cafe", "burger", "pizza", "food", "yemek", "doner", "durum"]):
        category = "Food"
    elif any(word in text_lower for word in ["bus", "metro", "taxi", "transport", "ulasim", "otobus"]):
        category = "Transport"
    elif any(word in text_lower for word in ["shop", "shopping", "alisveris"]):
        category = "Shopping"
    elif any(word in text_lower for word in ["allowance", "burs", "scholarship"]):
        category = "Allowance"
    elif any(word in text_lower for word in ["salary", "gaji", "maas"]):
        category = "Salary"

    store = ""
    note = text.strip()

    store_keywords = [
        "migros", "bim", "a101", "sok", "carrefour", "starbucks",
        "burger king", "mcdonalds", "oncu doner", "ono doner", "doner",
    ]

    for keyword in store_keywords:
        if keyword in text_lower:
            if keyword == "sok":
                store = "ŞOK"
            elif keyword in ["ono doner", "oncu doner", "doner"]:
                store = "ÖNÖ DÖNER"
            else:
                store = keyword.title()
            break

    if not store and "from " in text.lower():
        try:
            store = text.split("from", 1)[1].strip().split()[0].title()
        except Exception:
            pass

    return {
        "type": trans_type,
        "amount": amount,
        "category": category,
        "store": store,
        "note": note,
    }
