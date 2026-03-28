import os
import re
import cv2
import easyocr
from datetime import datetime

reader = easyocr.Reader(["en", "tr"], gpu=False)

def preprocess_receipt_image(filepath):
    image = cv2.imread(filepath)
    if image is None:
        return filepath

    h, w = image.shape[:2]
    max_width = 900
    if w > max_width:
        scale = max_width / w
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    processed_path = os.path.join(os.path.dirname(filepath), "processed_" + os.path.basename(filepath))
    cv2.imwrite(processed_path, gray)
    return processed_path

def extract_store_name(text_lines):
    known_stores = ["şok", "sok", "migros", "a101", "bim", "carrefour"]

    for line in text_lines[:8]:
        lower = line.lower()
        for store in known_stores:
            if store in lower:
                return store.upper()

    for line in text_lines[:5]:
        cleaned = line.strip()
        if len(cleaned) > 3 and not re.search(r"\d", cleaned):
            return cleaned.title()

    return "Unknown Store"

def extract_date(text_lines):
    for line in text_lines:
        match = re.search(r"(\d{2}[./-]\d{2}[./-]\d{4})", line)
        if match:
            raw = match.group(1)
            for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    pass
    return datetime.today().strftime("%Y-%m-%d")

def extract_total(text_lines):
    joined = " ".join(text_lines)

    patterns = [
        r"TOPLAM\s*[*+]?\s*(\d+[.,]\d{2})",
        r"TOPLAM\s+(\d+)\s+(\d{2})",
    ]

    for p in patterns:
        match = re.search(p, joined, re.IGNORECASE)
        if match:
            if len(match.groups()) == 1:
                return float(match.group(1).replace(",", "."))
            if len(match.groups()) == 2:
                return float(f"{match.group(1)}.{match.group(2)}")

    all_prices = re.findall(r"(\d+[.,]\d{2})", joined)
    if all_prices:
        return float(all_prices[-1].replace(",", "."))

    return 0.0

def suggest_category(store_name, note=""):
    text = f"{store_name} {note}".lower()

    if any(x in text for x in ["şok", "sok", "a101", "bim", "migros", "carrefour", "market"]):
        return "Grocery"
    if any(x in text for x in ["cafe", "kahve", "coffee", "restaurant", "burger", "pizza"]):
        return "Food"
    if any(x in text for x in ["otobüs", "otobus", "metro", "taksi", "taxi", "transport"]):
        return "Transport"
    if any(x in text for x in ["burs", "scholarship", "allowance"]):
        return "Allowance"
    if any(x in text for x in ["salary", "maaş", "maas"]):
        return "Salary"

    return "Other"

def scan_receipt(filepath):
    processed = preprocess_receipt_image(filepath)
    results = reader.readtext(processed, detail=0)
    lines = [x.strip() for x in results if x.strip()]

    store_name = extract_store_name(lines)
    date = extract_date(lines)
    amount = extract_total(lines)
    category = suggest_category(store_name)

    return {
        "store_name": store_name,
        "date": date,
        "amount": amount,
        "category": category,
        "ocr_text": "\n".join(lines),
    }

def advisor_reply(summary, message):
    text = message.lower()

    if "biggest" in text or "expense" in text:
        return f"Your highest expense category is {summary['top_category']}."

    if "balance" in text:
        return f"Your current balance is ₺{summary['balance']:.2f}."

    if "income" in text:
        return f"Your total income is ₺{summary['income']:.2f}."

    if "tips" in text or "budget" in text:
        if summary["expense"] > summary["income"]:
            return "Your expenses are higher than your income. Try reducing non-essential spending."
        return "Your financial condition looks stable. Keep tracking expenses regularly."

    return "I can help with balance, biggest expense, income, and budget tips."
def parse_voice_transaction(text: str):
    text_lower = text.lower()

    trans_type = "expense"
    if any(word in text_lower for word in ["income", "salary", "gaji", "maaş", "maas"]):
        trans_type = "income"

    amount = None
    amount_match = re.search(r"(\d+[.,]?\d{0,2})", text_lower)
    if amount_match:
        try:
            amount = float(amount_match.group(1).replace(",", "."))
        except ValueError:
            amount = None

    category = "AUTO"
    if any(word in text_lower for word in ["market", "migros", "bim", "a101", "şok", "sok", "grocery"]):
        category = "Grocery"
    elif any(word in text_lower for word in ["coffee", "kahve", "cafe", "burger", "pizza", "food", "yemek", "döner", "doner"]):
        category = "Food"
    elif any(word in text_lower for word in ["bus", "metro", "taxi", "transport", "ulaşım", "ulasim", "otobüs", "otobus"]):
        category = "Transport"
    elif any(word in text_lower for word in ["shop", "shopping", "alışveriş", "alisveris"]):
        category = "Shopping"
    elif any(word in text_lower for word in ["allowance", "burs", "scholarship"]):
        category = "Allowance"
    elif any(word in text_lower for word in ["salary", "gaji", "maaş", "maas"]):
        category = "Salary"

    store = ""
    note = text.strip()

    store_keywords = [
        "migros", "bim", "a101", "şok", "sok", "carrefour",
        "starbucks", "burger king", "mcdonalds", "oncu doner", "öncü döner"
    ]
    for keyword in store_keywords:
        if keyword in text_lower:
            store = keyword.title()
            break

    if not store:
        if "from " in text_lower:
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