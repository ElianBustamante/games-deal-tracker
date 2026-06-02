import os
import sqlite3
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "steam_epic_deals.db"
DEFAULT_MIN_DISCOUNT = int(os.getenv("DEFAULT_MIN_DISCOUNT", "50"))

_test_db_path = None
_db_uri = False

def get_db_path():
    return _test_db_path if _test_db_path else DB_FILE

async def connect_db():
    return aiosqlite.connect(get_db_path(), uri=_db_uri)

async def init_db() -> None:
    async with await connect_db() as db:
        # Recreate notified_deals if upgrading from an older version without store column
        try:
            cursor = await db.execute("PRAGMA table_info(notified_deals)")
            columns = await cursor.fetchall()
            has_store = any(col[1] == 'store' for col in columns)
            if columns and not has_store:
                await db.execute("DROP TABLE IF EXISTS notified_deals")
        except sqlite3.OperationalError:
            pass

        await db.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id TEXT NOT NULL,
                app_id TEXT NOT NULL,
                game_name TEXT NOT NULL,
                epic_slug TEXT DEFAULT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_id, app_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS server_config (
                server_id TEXT PRIMARY KEY,
                channel_id TEXT,
                epic_channel_id TEXT DEFAULT NULL,
                min_discount INTEGER DEFAULT 50,
                language TEXT DEFAULT 'es',
                is_dm BOOLEAN DEFAULT 0,
                country TEXT DEFAULT 'cl',
                failed_dm_attempts INTEGER DEFAULT 0
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS notified_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id TEXT NOT NULL,
                app_id TEXT NOT NULL,
                store TEXT NOT NULL DEFAULT 'steam',
                notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_id, app_id, store)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL,
                game_name TEXT NOT NULL,
                price_final INTEGER NOT NULL,
                price_original INTEGER NOT NULL,
                discount_percent INTEGER NOT NULL,
                currency TEXT NOT NULL,
                store TEXT NOT NULL DEFAULT 'steam',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Migrations for existing databases: Add columns if they do not exist
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

        try:
            await db.execute("ALTER TABLE server_config ADD COLUMN failed_dm_attempts INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            await db.execute("ALTER TABLE server_config ADD COLUMN epic_channel_id TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass

        try:
            await db.execute("ALTER TABLE watchlist ADD COLUMN epic_slug TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass

        try:
            await db.execute("ALTER TABLE price_history ADD COLUMN store TEXT NOT NULL DEFAULT 'steam'")
        except sqlite3.OperationalError:
            pass

        await db.commit()

# Watchlist Functions
async def add_to_watchlist(server_id: str, app_id: int | str, game_name: str, epic_slug: str = None) -> bool:
    try:
        async with await connect_db() as db:
            await db.execute(
                "INSERT INTO watchlist (server_id, app_id, game_name, epic_slug) VALUES (?, ?, ?, ?)",
                (server_id, str(app_id), game_name, epic_slug)
            )
            await db.commit()
            return True
    except sqlite3.IntegrityError:
        return False

async def remove_from_watchlist(server_id: str, app_id: int | str) -> bool:
    async with await connect_db() as db:
        cursor = await db.execute(
            "DELETE FROM watchlist WHERE server_id = ? AND app_id = ?",
            (server_id, str(app_id))
        )
        await db.commit()
        return cursor.rowcount > 0

async def update_epic_slug(server_id: str, app_id: int | str, epic_slug: str) -> None:
    async with await connect_db() as db:
        await db.execute(
            "UPDATE watchlist SET epic_slug = ? WHERE server_id = ? AND app_id = ?",
            (epic_slug, server_id, str(app_id))
        )
        await db.commit()

async def get_watchlist(server_id: str) -> list[dict]:
    async with await connect_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT app_id, game_name, epic_slug, added_at FROM watchlist WHERE server_id = ?",
            (server_id,)
        )
        rows = await cursor.fetchall()
        # Convert app_id back to int if it looks like one, to keep compatibility
        result = []
        for row in rows:
            app_id_val = row["app_id"]
            if app_id_val.isdigit():
                app_id_val = int(app_id_val)
            result.append({
                "app_id": app_id_val,
                "game_name": row["game_name"],
                "epic_slug": row["epic_slug"],
                "added_at": row["added_at"]
            })
        return result

async def get_all_configured_servers() -> list[str]:
    # Deprecated: use get_all_configured_targets
    async with await connect_db() as db:
        cursor = await db.execute("SELECT server_id FROM server_config WHERE channel_id IS NOT NULL")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def get_all_configured_targets() -> list[dict]:
    async with await connect_db() as db:
        cursor = await db.execute("SELECT server_id, channel_id, epic_channel_id, is_dm, language, country FROM server_config WHERE channel_id IS NOT NULL")
        rows = await cursor.fetchall()
        return [{
            "target_id": row[0], 
            "channel_id": row[1], 
            "epic_channel_id": row[2],
            "is_dm": bool(row[3]),
            "language": row[4] if row[4] else "es",
            "country": row[5] if row[5] else "cl"
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

async def set_epic_channel(server_id: str, channel_id: str | None) -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO server_config (server_id, epic_channel_id) VALUES (?, ?)
               ON CONFLICT(server_id) DO UPDATE SET epic_channel_id = excluded.epic_channel_id""",
            (server_id, channel_id)
        )
        await db.commit()

async def get_effective_epic_channel(server_id: str) -> str | None:
    async with await connect_db() as db:
        cursor = await db.execute("SELECT channel_id, epic_channel_id FROM server_config WHERE server_id = ?", (server_id,))
        row = await cursor.fetchone()
        if row:
            # If epic_channel_id is set, return it. Otherwise, fallback to Steam channel_id.
            return row[1] if row[1] is not None else row[0]
        return None

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
async def mark_as_notified(server_id: str, app_id: int | str, store: str = 'steam') -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO notified_deals (server_id, app_id, store, notified_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(server_id, app_id, store) DO UPDATE SET notified_at = CURRENT_TIMESTAMP""",
            (server_id, str(app_id), store)
        )
        await db.commit()

async def was_notified_today(server_id: str, app_id: int | str, store: str = 'steam') -> bool:
    async with await connect_db() as db:
        cursor = await db.execute(
            """SELECT notified_at FROM notified_deals 
               WHERE server_id = ? AND app_id = ? AND store = ? AND notified_at >= datetime('now', '-1 day')""",
            (server_id, str(app_id), store)
        )
        row = await cursor.fetchone()
        return row is not None

async def clear_old_notifications() -> None:
    async with await connect_db() as db:
        await db.execute("DELETE FROM notified_deals WHERE notified_at < datetime('now', '-1 day')")
        await db.commit()

# Price History Functions
async def save_price_snapshot(app_id: int | str, game_name: str, price_final: int, price_original: int, discount_percent: int, currency: str, store: str = 'steam') -> None:
    async with await connect_db() as db:
        await db.execute(
            """INSERT INTO price_history 
               (app_id, game_name, price_final, price_original, discount_percent, currency, store) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(app_id), game_name, price_final, price_original, discount_percent, currency, store)
        )
        await db.commit()

async def get_historical_low(app_id: int | str, currency: str, store: str = 'steam') -> dict | None:
    async with await connect_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT price_final, discount_percent, recorded_at 
               FROM price_history WHERE app_id = ? AND currency = ? AND store = ? ORDER BY price_final ASC LIMIT 1""",
            (str(app_id), currency, store)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "price_final": row["price_final"],
                "discount_percent": row["discount_percent"],
                "recorded_at": row["recorded_at"]
            }
        return None

async def get_price_history(app_id: int | str, currency: str, limit: int = 10, store: str = 'steam') -> list[dict]:
    async with await connect_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT price_final, price_original, discount_percent, recorded_at 
               FROM price_history WHERE app_id = ? AND currency = ? AND store = ? ORDER BY recorded_at DESC LIMIT ?""",
            (str(app_id), currency, store, limit)
        )
        rows = await cursor.fetchall()
        return [{
            "price_final": row["price_final"],
            "price_original": row["price_original"],
            "discount_percent": row["discount_percent"],
            "recorded_at": row["recorded_at"]
        } for row in rows]

async def increment_failed_dm_attempts(target_id: str) -> int:
    async with await connect_db() as db:
        await db.execute(
            "UPDATE server_config SET failed_dm_attempts = failed_dm_attempts + 1 WHERE server_id = ?",
            (target_id,)
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT failed_dm_attempts FROM server_config WHERE server_id = ?",
            (target_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

async def reset_failed_dm_attempts(target_id: str) -> None:
    async with await connect_db() as db:
        await db.execute(
            "UPDATE server_config SET failed_dm_attempts = 0 WHERE server_id = ?",
            (target_id,)
        )
        await db.commit()
