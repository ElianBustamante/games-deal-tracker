import pytest
from app.steam import search_game, get_game_price, get_featured_deals, get_store_url, get_header_image_url, search_game_autocomplete, autocomplete_cache

class MockResponse:
    def __init__(self, json_data=None, status=200):
        self._json = json_data or {}
        self.status = status

    async def json(self):
        return self._json

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

class MockSession:
    def __init__(self, response):
        self.response = response

    def get(self, url, **kwargs):
        return self.response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.fixture
def mock_aiohttp_session(mocker):
    mock_response = MockResponse()
    mock_session = MockSession(mock_response)
    mocker.patch("app.steam.aiohttp.ClientSession", return_value=mock_session)
    return mock_response

@pytest.mark.asyncio
async def test_search_game_success(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "items": [
            {"id": 1091500, "name": "Cyberpunk 2077"}
        ]
    }
    
    result = await search_game("Cyberpunk 2077")
    
    assert result is not None
    assert result["app_id"] == 1091500
    assert result["name"] == "Cyberpunk 2077"

@pytest.mark.asyncio
async def test_search_game_empty(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {"items": []}
    
    result = await search_game("Unknown Game")
    
    assert result is None

@pytest.mark.asyncio
async def test_get_game_price_success(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "1091500": {
            "success": True,
            "data": {
                "name": "Cyberpunk 2077",
                "price_overview": {
                    "initial": 3999900,
                    "final": 1999900,
                    "discount_percent": 50,
                    "currency": "CLP"
                }
            }
        }
    }
    
    result = await get_game_price(1091500)
    
    assert result is not None
    assert result["app_id"] == 1091500
    assert result["name"] == "Cyberpunk 2077"
    assert result["price_original"] == 3999900
    assert result["price_final"] == 1999900
    assert result["discount_percent"] == 50
    assert result["currency"] == "CLP"

@pytest.mark.asyncio
async def test_get_game_price_free(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "12345": {
            "success": True,
            "data": {
                "name": "Free Game",
                "is_free": True
                # No price_overview for free games
            }
        }
    }
    
    result = await get_game_price(12345)
    
    assert result is None

@pytest.mark.asyncio
async def test_get_featured_deals_success(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "specials": {
            "items": [
                {
                    "id": 111,
                    "name": "Deal Game",
                    "original_price": 1000,
                    "final_price": 500,
                    "discount_percent": 50,
                    "discounted": True
                }
            ]
        }
    }
    
    result = await get_featured_deals()
    
    assert len(result) == 1
    assert result[0]["app_id"] == 111
    assert result[0]["name"] == "Deal Game"
    assert result[0]["price_original"] == 1000
    assert result[0]["price_final"] == 500
    assert result[0]["discount_percent"] == 50

@pytest.mark.asyncio
async def test_get_featured_deals_missing_specials(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "status": 1
        # No specials key
    }
    
    result = await get_featured_deals()
    
    assert result == []

@pytest.mark.asyncio
async def test_search_game_autocomplete_success(mock_aiohttp_session):
    autocomplete_cache.clear()
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "items": [
            {"id": 1091500, "name": "Cyberpunk 2077"},
            {"id": 2000, "name": "Cyberpunk 2077 Deluxe"}
        ]
    }
    
    result = await search_game_autocomplete("cyber")
    
    assert len(result) == 2
    assert result[0]["app_id"] == 1091500
    assert result[1]["name"] == "Cyberpunk 2077 Deluxe"
    
@pytest.mark.asyncio
async def test_search_game_autocomplete_short_term(mock_aiohttp_session):
    autocomplete_cache.clear()
    result = await search_game_autocomplete("ab")
    assert result == []

@pytest.mark.asyncio
async def test_search_game_autocomplete_caching(mock_aiohttp_session):
    autocomplete_cache.clear()
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "items": [{"id": 1, "name": "Cached Game"}]
    }
    
    # First call hits "API"
    result1 = await search_game_autocomplete("cachetest")
    assert len(result1) == 1
    assert result1[0]["name"] == "Cached Game"
    
    # Change the mock response
    mock_aiohttp_session._json = {
        "items": [{"id": 2, "name": "Different Game"}]
    }
    
    # Second call should return cached data, not the new API data
    result2 = await search_game_autocomplete("cachetest")
    assert len(result2) == 1
    assert result2[0]["name"] == "Cached Game"

def test_get_store_url():
    assert get_store_url(1091500) == "https://store.steampowered.com/app/1091500/"

def test_get_header_image_url():
    assert get_header_image_url(1091500) == "https://cdn.cloudflare.steamstatic.com/steam/apps/1091500/header.jpg"
