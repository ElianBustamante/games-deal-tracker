import pytest
from unittest.mock import AsyncMock
from app.checker import save_and_enrich, check_watchlist, check_general_deals

@pytest.fixture
def mock_db(mocker):
    return {
        "get_historical_low": mocker.patch("app.database.get_historical_low", new_callable=AsyncMock),
        "save_price_snapshot": mocker.patch("app.database.save_price_snapshot", new_callable=AsyncMock),
        "get_watchlist": mocker.patch("app.database.get_watchlist", new_callable=AsyncMock),
        "was_notified_today": mocker.patch("app.database.was_notified_today", new_callable=AsyncMock),
        "get_min_discount": mocker.patch("app.database.get_min_discount", new_callable=AsyncMock),
        "clear_old_notifications": mocker.patch("app.database.clear_old_notifications", new_callable=AsyncMock),
        "get_all_configured_servers": mocker.patch("app.database.get_all_configured_servers", new_callable=AsyncMock),
        "get_channel": mocker.patch("app.database.get_channel", new_callable=AsyncMock),
        "mark_as_notified": mocker.patch("app.database.mark_as_notified", new_callable=AsyncMock),
    }

@pytest.fixture
def mock_steam(mocker):
    return {
        "get_game_price": mocker.patch("app.steam.get_game_price", new_callable=AsyncMock),
        "get_featured_deals": mocker.patch("app.steam.get_featured_deals", new_callable=AsyncMock),
        "get_store_url": mocker.patch("app.steam.get_store_url", return_value="http://store.url")
    }

@pytest.mark.asyncio
async def test_save_and_enrich_no_history(mock_db, mock_steam):
    mock_db["get_historical_low"].return_value = None
    
    price = {
        "app_id": 1,
        "name": "Game",
        "price_final": 500,
        "price_original": 1000,
        "discount_percent": 50,
        "currency": "USD"
    }
    
    result = await save_and_enrich(price)
    
    assert result["is_historical_low"] is True
    assert result["historical_low"] is None
    assert result["url"] == "http://store.url"
    mock_db["save_price_snapshot"].assert_called_once()

@pytest.mark.asyncio
async def test_save_and_enrich_current_price_is_lower(mock_db, mock_steam):
    mock_db["get_historical_low"].return_value = {"price_final": 600}
    
    price = {
        "app_id": 1,
        "name": "Game",
        "price_final": 500,
        "price_original": 1000,
        "discount_percent": 50,
        "currency": "USD"
    }
    
    result = await save_and_enrich(price)
    
    assert result["is_historical_low"] is True

@pytest.mark.asyncio
async def test_save_and_enrich_current_price_is_higher(mock_db, mock_steam):
    mock_db["get_historical_low"].return_value = {"price_final": 400}
    
    price = {
        "app_id": 1,
        "name": "Game",
        "price_final": 500,
        "price_original": 1000,
        "discount_percent": 50,
        "currency": "USD"
    }
    
    result = await save_and_enrich(price)
    
    assert result["is_historical_low"] is False

@pytest.mark.asyncio
async def test_check_watchlist_skips_notified(mock_db, mock_steam):
    mock_db["get_watchlist"].return_value = [{"app_id": 1}]
    mock_steam["get_game_price"].return_value = {
        "app_id": 1, "name": "Game", "price_final": 500, 
        "price_original": 1000, "discount_percent": 50, "currency": "USD"
    }
    mock_db["was_notified_today"].return_value = True
    
    result = await check_watchlist("server1", "us")
    
    assert len(result) == 0

@pytest.mark.asyncio
async def test_check_general_deals_filters_min_discount(mock_db, mock_steam):
    deals = [
        {"app_id": 1, "name": "Game 1", "price_final": 500, "price_original": 1000, "discount_percent": 50, "currency": "USD"},
        {"app_id": 2, "name": "Game 2", "price_final": 800, "price_original": 1000, "discount_percent": 20, "currency": "USD"}
    ]
    mock_db["get_min_discount"].return_value = 40
    mock_db["was_notified_today"].return_value = False
    mock_db["get_historical_low"].return_value = None
    # get_game_price returns the validated deal (not adult content)
    mock_steam["get_game_price"].return_value = {
        "app_id": 1, "name": "Game 1", "price_final": 500,
        "price_original": 1000, "discount_percent": 50, "currency": "USD"
    }

    result = await check_general_deals("server1", deals, "us")

    assert len(result) == 1
    assert result[0]["app_id"] == 1

@pytest.mark.asyncio
async def test_check_epic_and_notify(mocker):
    # Mock database
    mock_targets = [{"target_id": "server1", "channel_id": "67890", "epic_channel_id": "12345", "is_dm": False, "language": "es", "country": "cl"}]
    mocker.patch("app.database.get_all_configured_targets", new_callable=AsyncMock, return_value=mock_targets)
    mocker.patch("app.database.get_min_discount", new_callable=AsyncMock, return_value=50)
    mocker.patch("app.database.was_notified_today", new_callable=AsyncMock, return_value=False)
    mocker.patch("app.database.get_historical_low", new_callable=AsyncMock, return_value=None)
    mocker.patch("app.database.save_price_snapshot", new_callable=AsyncMock)
    mocker.patch("app.database.mark_as_notified", new_callable=AsyncMock)
    mocker.patch("app.database.get_language", new_callable=AsyncMock, return_value="es")
    mocker.patch("app.database.clear_old_notifications", new_callable=AsyncMock)

    # Mock epic.get_deals
    mock_deals = [{"title": "Epic Deal", "slug": "epic-deal", "original_price": 2000, "final_price": 800, "discount_percent": 60, "currency": "USD", "end_date": None, "thumbnail": None}]
    mocker.patch("app.epic.get_deals", new_callable=AsyncMock, return_value=mock_deals)
    
    # Mock bot
    class MockChannel:
        def __init__(self):
            self.sent = []
        async def send(self, embed):
            self.sent.append(embed)
            
    mock_ch = MockChannel()
    class MockBot:
        def get_channel(self, channel_id):
            assert channel_id == 12345
            return mock_ch
            
    bot = MockBot()
    
    from app.checker import check_epic_and_notify
    stats = await check_epic_and_notify(bot)
    
    assert stats["targets_checked"] == 1
    assert stats["total_deals_sent"] == 1
    assert len(mock_ch.sent) == 1
    assert mock_ch.sent[0].title == "🏆 Epic Deal"

@pytest.mark.asyncio
async def test_check_epic_free_games(mocker):
    # Mock database
    mock_targets = [{"target_id": "server1", "channel_id": "67890", "epic_channel_id": None, "is_dm": False, "language": "es", "country": "cl"}]
    mocker.patch("app.database.get_all_configured_targets", new_callable=AsyncMock, return_value=mock_targets)
    mocker.patch("app.database.was_notified_today", new_callable=AsyncMock, return_value=False)
    mocker.patch("app.database.mark_as_notified", new_callable=AsyncMock)
    mocker.patch("app.database.get_language", new_callable=AsyncMock, return_value="es")

    # Mock epic.get_free_games
    mock_free = {
        "current": [{"title": "Free Now", "slug": "free-now", "end_date": "2026-06-10T17:00:00.000Z", "thumbnail": None}],
        "upcoming": []
    }
    mocker.patch("app.epic.get_free_games", new_callable=AsyncMock, return_value=mock_free)

    # Mock bot
    class MockChannel:
        def __init__(self):
            self.sent = []
        async def send(self, embed):
            self.sent.append(embed)
            
    mock_ch = MockChannel()
    class MockBot:
        def get_channel(self, channel_id):
            assert channel_id == 67890  # falls back to channel_id because epic_channel_id is None
            return mock_ch
            
    bot = MockBot()
    
    from app.checker import check_epic_free_games
    stats = await check_epic_free_games(bot)
    
    assert stats["targets_checked"] == 1
    assert stats["total_deals_sent"] == 1
    assert len(mock_ch.sent) == 1
    assert mock_ch.sent[0].title == "🎁 Juegos Gratis — Epic Games"

