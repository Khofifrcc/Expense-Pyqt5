import re

def parse_voice_transaction(text):
    text = text.lower()
    result = {
        "type": "expense",
        "store": None,
        "amount": None,
        "category": "Other",
        "note": ""
    }

    # 1. Deteksi Angka (Amount)
    amounts = re.findall(r'\d+', text)
    if amounts:
        result["amount"] = float(amounts[0])

    # 2. Deteksi Toko (Store)
    # Mencari kata setelah 'di', 'ke', atau 'at'
    store_match = re.search(r'(?:di|ke|at)\s+([a-zA-Z0-9]+)', text)
    if store_match:
        result["store"] = store_match.group(1).capitalize()
    else:
        # Alternatif: Ambil kata pertama yang bukan angka dan bukan kata umum
        words = text.split()
        potential = [w for w in words if not w.isdigit() and len(w) > 2]
        if potential:
            result["store"] = potential[0].capitalize()

    # 3. Deteksi Tipe
    if any(word in text for word in ["income", "gaji", "masuk", "pemasukan"]):
        result["type"] = "income"

    return result