import pytest
import aiosqlite
import pytest_asyncio
import uuid
import app.database as database
from app.database import set_channel, get_all_configured_targets, stop_notifications

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    db_name = f"file:memdb_dm_{uuid.uuid4().hex}?mode=memory&cache=shared"
    database._test_db_path = db_name
    database._db_uri = True
    
    conn = await aiosqlite.connect(db_name, uri=True)
    await database.init_db()
    
    yield
    
    await conn.close()

@pytest.mark.asyncio
async def test_set_channel_guild():
    # Simulate a guild setup
    await set_channel("guild_123", "channel_456", is_dm=False)
    targets = await get_all_configured_targets()
    
    assert len(targets) == 1
    assert targets[0]["target_id"] == "guild_123"
    assert targets[0]["channel_id"] == "channel_456"
    assert targets[0]["is_dm"] is False

@pytest.mark.asyncio
async def test_set_channel_dm():
    # Simulate a direct message setup
    await set_channel("user_999", "user_999", is_dm=True)
    targets = await get_all_configured_targets()
    
    assert len(targets) == 1
    assert targets[0]["target_id"] == "user_999"
    assert targets[0]["channel_id"] == "user_999"
    assert targets[0]["is_dm"] is True

@pytest.mark.asyncio
async def test_stop_notifications():
    # Setup mixed environment
    await set_channel("guild_123", "channel_456", is_dm=False)
    await set_channel("user_999", "user_999", is_dm=True)
    
    targets_before = await get_all_configured_targets()
    assert len(targets_before) == 2
    
    # User calls /stop
    await stop_notifications("user_999")
    
    targets_after = await get_all_configured_targets()
    assert len(targets_after) == 1
    assert targets_after[0]["target_id"] == "guild_123"
