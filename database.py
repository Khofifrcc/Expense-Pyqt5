import sqlite3

DB_NAME = "receipts.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            receipt_image TEXT
        )
    """)

    conn.commit()
    conn.close()

def add_transaction(store_name, amount, category, note, date, trans_type, receipt_image=None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO transactions (store_name, amount, category, note, date, type, receipt_image)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (store_name, amount, category, note, date, trans_type, receipt_image))
    conn.commit()
    conn.close()

def update_transaction(tx_id, store_name, amount, category, note, date, trans_type):
    conn = get_connection()
    conn.execute("""
        UPDATE transactions
        SET store_name=?, amount=?, category=?, note=?, date=?, type=?
        WHERE id=?
    """, (store_name, amount, category, note, date, trans_type, tx_id))
    conn.commit()
    conn.close()

def delete_transaction(tx_id):
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()

def get_transactions(search="", trans_type="", category=""):
    conn = get_connection()
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if search:
        query += " AND (LOWER(store_name) LIKE ? OR LOWER(COALESCE(note,'')) LIKE ?)"
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])

    if trans_type and trans_type != "All":
        query += " AND type = ?"
        params.append(trans_type.lower())

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY date DESC, id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows

def get_summary():
    conn = get_connection()

    total_income = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income'"
    ).fetchone()[0]

    total_expense = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense'"
    ).fetchone()[0]

    total_count = conn.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    top_category_row = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE type='expense'
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    return {
        "income": float(total_income),
        "expense": float(total_expense),
        "balance": float(total_income) - float(total_expense),
        "count": total_count,
        "top_category": top_category_row["category"] if top_category_row else "-"
    }
def update_transaction(tx_id, store_name, amount, category, note, date, trans_type):
    conn = get_connection()
    conn.execute("""
        UPDATE transactions
        SET store_name=?, amount=?, category=?, note=?, date=?, type=?
        WHERE id=?
    """, (store_name, amount, category, note, date, trans_type, tx_id))
    conn.commit()
    conn.close()
def get_expense_by_category():
    conn = get_connection()
    rows = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE type='expense'
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()
    conn.close()
    return rows


def get_income_vs_expense():
    conn = get_connection()

    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type='income'
    """).fetchone()[0]

    expense = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type='expense'
    """).fetchone()[0]

    conn.close()
    return {"income": float(income), "expense": float(expense)}


def get_daily_expense_trend():
    conn = get_connection()
    rows = conn.execute("""
        SELECT date, SUM(amount) as total
        FROM transactions
        WHERE type='expense'
        GROUP BY date
        ORDER BY date ASC
        LIMIT 10
    """).fetchall()
    conn.close()
    return rows