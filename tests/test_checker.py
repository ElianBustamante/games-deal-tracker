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
    
    result = await check_watchlist("server1")
    
    assert len(result) == 0

@pytest.mark.asyncio
async def test_check_general_deals_filters_min_discount(mock_db, mock_steam):
    mock_steam["get_featured_deals"].return_value = [
        {"app_id": 1, "name": "Game 1", "price_final": 500, "price_original": 1000, "discount_percent": 50, "currency": "USD"},
        {"app_id": 2, "name": "Game 2", "price_final": 800, "price_original": 1000, "discount_percent": 20, "currency": "USD"}
    ]
    mock_db["get_min_discount"].return_value = 40
    mock_db["was_notified_today"].return_value = False
    mock_db["get_historical_low"].return_value = None
    
    result = await check_general_deals("server1")
    
    assert len(result) == 1
    assert result[0]["app_id"] == 1
