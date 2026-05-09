import uuid
import pytest
import aiosqlite
import pytest_asyncio
import app.database as database

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Use a unique shared in-memory DB per test to ensure clean state
    db_name = f"file:memdb_{uuid.uuid4().hex}?mode=memory&cache=shared"
    database._test_db_path = db_name
    database._db_uri = True
    
    # Keep one connection open to keep the shared in-memory DB alive during the test
    conn = await aiosqlite.connect(db_name, uri=True)
    
    await database.init_db()
    
    yield
    
    await conn.close()

@pytest.mark.asyncio
async def test_add_to_watchlist_returns_false_on_duplicate():
    server_id = "server1"
    app_id = 1091500
    game_name = "Cyberpunk 2077"
    
    # First insert should be True
    res1 = await database.add_to_watchlist(server_id, app_id, game_name)
    assert res1 is True
    
    # Second insert should be False (duplicate)
    res2 = await database.add_to_watchlist(server_id, app_id, game_name)
    assert res2 is False

@pytest.mark.asyncio
async def test_was_notified_today_within_24h_window():
    server_id = "server1"
    app_id = 111
    
    # Should not be notified yet
    assert await database.was_notified_today(server_id, app_id) is False
    
    # Mark as notified
    await database.mark_as_notified(server_id, app_id)
    
    # Should be notified now
    assert await database.was_notified_today(server_id, app_id) is True

@pytest.mark.asyncio
async def test_save_price_snapshot_inserts_multiple_rows():
    import asyncio
    app_id = 222
    game_name = "Test Game"
    
    await database.save_price_snapshot(app_id, game_name, 1000, 2000, 50, "USD")
    await asyncio.sleep(1) # Ensure CURRENT_TIMESTAMP changes between inserts
    await database.save_price_snapshot(app_id, game_name, 500, 2000, 75, "USD")
    
    history = await database.get_price_history(app_id, "USD")
    assert len(history) == 2
    assert history[0]["price_final"] == 500  # Ordered by DESC recorded_at so latest is first
    assert history[1]["price_final"] == 1000

@pytest.mark.asyncio
async def test_get_historical_low_returns_lowest_price():
    app_id = 333
    game_name = "Low Game"
    
    await database.save_price_snapshot(app_id, game_name, 1500, 2000, 25, "CLP")
    await database.save_price_snapshot(app_id, game_name, 500, 2000, 75, "CLP")
    await database.save_price_snapshot(app_id, game_name, 1000, 2000, 50, "CLP")
    
    low = await database.get_historical_low(app_id, "CLP")
    assert low is not None
    assert low["price_final"] == 500
    assert low["discount_percent"] == 75

@pytest.mark.asyncio
async def test_get_historical_low_returns_none_when_no_history():
    app_id = 444
    low = await database.get_historical_low(app_id, "CLP")
    assert low is None
