'''Save and read price history in a SQLite database'''

import sqlite3

DEFAULT_DB_PATH = "prices.db"

_SCHEMA = '''
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_url TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP -- UTC
);
CREATE INDEX IF NOT EXISTS idx_price_history_url
    ON price_history (product_url, id);
'''


def init_db(path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    '''Open the database at ``path``, creating the table if it does not exist.'''
    conn = sqlite3.connect(path)
    with conn:
        conn.executescript(_SCHEMA)
    return conn


def save_price(conn: sqlite3.Connection, url: str, title: str, price: float) -> None:
    '''Record one price reading for ```url```.'''
    with conn:
        conn.execute(
            'INSERT INTO price_history (product_url, title, price) VALUES (?, ?, ?)',
            (url, title, price)
        )
        

def get_last_price(conn: sqlite3.Connection, url: str) -> float | None:
    '''Return the most recently saved price for ```url```, or None if there is none.'''
    row = conn.execute(
        'SELECT price FROM price_history WHERE product_url = ? ORDER BY id DESC LIMIT 1',
        (url,),
    ).fetchone()
    return row[0] if row else None