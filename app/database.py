import os
import sqlite3
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "steam_deals.db"
DEFAULT_MIN_DISCOUNT = int(os.getenv("DEFAULT_MIN_DISCOUNT", "50"))

_test_db_path = None
_db_uri = False

def get_db_path():
    return _test_db_path if _test_db_path else DB_FILE

async def connect_db():
    return aiosqlite.connect(get_db_path(), uri=_db_uri)

async def init_db() -> None:
    async with await connect_db() as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id TEXT NOT NULL,
                app_id INTEGER NOT NULL,
                game_name TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_id, app_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS server_config (
                server_id TEXT PRIMARY KEY,
                channel_id TEXT,
                min_discount INTEGER DEFAULT 50,
                language TEXT DEFAULT 'es'
            )
        ''')
        
        # Add column if upgrading from older version
        try:
            await db.execute("ALTER TABLE server_config ADD COLUMN language TEXT DEFAULT 'es'")
        except sqlite3.OperationalError:
            pass
            
        try:
            await db.execute("ALTER TABLE server_config ADD COLUMN is_dm BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError:
            pass
            
        try:
            await db.execute("ALTER TABLE server_config ADD COLUMN country TEXT DEFAULT 'cl'")
        except sqlite3.OperationalError:
            pass

        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS notified_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id TEXT NOT NULL,
                app_id INTEGER NOT NULL,
                notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_id, app_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                game_name TEXT NOT NULL,
                price_final INTEGER NOT NULL,
                price_original INTEGER NOT NULL,
                discount_percent INTEGER NOT NULL,
                currency TEXT NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

# Watchlist Functions
async def add_to_watchlist(server_id: str, app_id: int, game_name: str) -> bool:
    try:
        async with await connect_db() as db:
            await db.execute(
                "INSERT INTO watchlist (server_id, app_id, game_name) VALUES (?, ?, ?)",
                (server_id, app_id, game_name)
            )
            await db.commit()
            return True
    except sqlite3.IntegrityError:
        return False

async def remove_from_watchlist(server_id: str, app_id: int) -> bool:
    async with await connect_db() as db:
        cursor = await db.execute(
            "DELETE FROM watchlist WHERE server_id = ? AND app_id = ?",
            (server_id, app_id)
        )
        await db.commit()
        return cursor.rowcount > 0

async def get_watchlist(server_id: str) -> list[dict]:
    async with await connect_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT app_id, game_name, added_at FROM watchlist WHERE server_id = ?",
            (server_id,)
        )
        rows = await cursor.fetchall()
        return [{"app_id": row["app_id"], "game_name": row["game_name"], "added_at": row["added_at"]} for row in rows]

async def get_all_configured_servers() -> list[str]:
    # Deprecated: use get_all_configured_targets
    async with await connect_db() as db:
        cursor = await db.execute("SELECT server_id FROM server_config WHERE channel_id IS NOT NULL")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def get_all_configured_targets() -> list[dict]:
    async with await connect_db() as db:
        cursor = await db.execute("SELECT server_id, channel_id, is_dm, language, country FROM server_config WHERE channel_id IS NOT NULL")
        rows = await cursor.fetchall()
        return [{
            "target_id": row[0], 
            "channel_id": row[1], 
            "is_dm": bool(row[2]),
            "language": row[3] if row[3] else "es",
            "country": row[4] if row[4] else "cl"
        } for row in rows]

# Config Functions
async def set_channel(server_id: str, channel_id: str, is_dm: bool = False) -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO server_config (server_id, channel_id, is_dm) VALUES (?, ?, ?)
               ON CONFLICT(server_id) DO UPDATE SET channel_id = excluded.channel_id, is_dm = excluded.is_dm""",
            (server_id, channel_id, is_dm)
        )
        await db.commit()

async def stop_notifications(server_id: str) -> None:
    async with await connect_db() as db:
        await db.execute("DELETE FROM server_config WHERE server_id = ?", (server_id,))
        await db.execute("DELETE FROM watchlist WHERE server_id = ?", (server_id,))
        await db.commit()

async def get_channel(server_id: str) -> str | None:
    async with await connect_db() as db:
        cursor = await db.execute("SELECT channel_id FROM server_config WHERE server_id = ?", (server_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] else None

async def set_min_discount(server_id: str, discount: int) -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO server_config (server_id, min_discount) VALUES (?, ?)
               ON CONFLICT(server_id) DO UPDATE SET min_discount = excluded.min_discount""",
            (server_id, discount)
        )
        await db.commit()

async def get_min_discount(server_id: str) -> int:
    async with await connect_db() as db:
        cursor = await db.execute("SELECT min_discount FROM server_config WHERE server_id = ?", (server_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] is not None else DEFAULT_MIN_DISCOUNT

async def set_language(server_id: str, language: str) -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO server_config (server_id, language) VALUES (?, ?)
               ON CONFLICT(server_id) DO UPDATE SET language = excluded.language""",
            (server_id, language)
        )
        await db.commit()

async def get_language(server_id: str) -> str:
    async with await connect_db() as db:
        cursor = await db.execute("SELECT language FROM server_config WHERE server_id = ?", (server_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] is not None else "es"

async def set_country(server_id: str, country: str) -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO server_config (server_id, country) VALUES (?, ?)
               ON CONFLICT(server_id) DO UPDATE SET country = excluded.country""",
            (server_id, country)
        )
        await db.commit()

async def get_country(server_id: str) -> str:
    async with await connect_db() as db:
        cursor = await db.execute("SELECT country FROM server_config WHERE server_id = ?", (server_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] is not None else "cl"

# Notifications Functions
async def mark_as_notified(server_id: str, app_id: int) -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO notified_deals (server_id, app_id, notified_at) VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(server_id, app_id) DO UPDATE SET notified_at = CURRENT_TIMESTAMP""",
            (server_id, app_id)
        )
        await db.commit()

async def was_notified_today(server_id: str, app_id: int) -> bool:
    async with await connect_db() as db:
        cursor = await db.execute(
            """SELECT notified_at FROM notified_deals 
               WHERE server_id = ? AND app_id = ? AND notified_at >= datetime('now', '-1 day')""",
            (server_id, app_id)
        )
        row = await cursor.fetchone()
        return row is not None

async def clear_old_notifications() -> None:
    async with await connect_db() as db:
        await db.execute("DELETE FROM notified_deals WHERE notified_at < datetime('now', '-1 day')")
        await db.commit()

# Price History Functions
async def save_price_snapshot(app_id: int, game_name: str, price_final: int, price_original: int, discount_percent: int, currency: str) -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO price_history 
               (app_id, game_name, price_final, price_original, discount_percent, currency) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (app_id, game_name, price_final, price_original, discount_percent, currency)
        )
        await db.commit()

async def get_historical_low(app_id: int, currency: str) -> dict | None:
    async with await connect_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT price_final, discount_percent, recorded_at 
               FROM price_history WHERE app_id = ? AND currency = ? ORDER BY price_final ASC LIMIT 1""",
            (app_id, currency)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "price_final": row["price_final"],
                "discount_percent": row["discount_percent"],
                "recorded_at": row["recorded_at"]
            }
        return None

async def get_price_history(app_id: int, currency: str, limit: int = 10) -> list[dict]:
    async with await connect_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT price_final, price_original, discount_percent, recorded_at 
               FROM price_history WHERE app_id = ? AND currency = ? ORDER BY recorded_at DESC LIMIT ?""",
            (app_id, currency, limit)
        )
        rows = await cursor.fetchall()
        return [{
            "price_final": row["price_final"],
            "price_original": row["price_original"],
            "discount_percent": row["discount_percent"],
            "recorded_at": row["recorded_at"]
        } for row in rows]
