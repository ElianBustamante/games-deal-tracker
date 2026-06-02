import pytest
from app.epic import (
    search_game, get_deals, get_free_games, get_game_price, get_store_url,
    normalize_epic_price, deals_cache, search_cache, price_cache
)

@pytest.fixture(autouse=True)
def clear_caches():
    deals_cache.clear()
    search_cache.clear()
    price_cache.clear()

class SharedState:

    def __init__(self):
        self._json = {}
        self._status = 200

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, val):
        self._status = val

    @property
    def status_code(self):
        return self._status

    @status_code.setter
    def status_code(self, val):
        self._status = val

class MockAioHttpResponse:
    def __init__(self, state):
        self.state = state

    @property
    def status(self):
        return self.state.status

    async def json(self):
        return self.state._json

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

class MockAiohttpSession:
    def __init__(self, response):
        self.response = response

    def get(self, url, **kwargs):
        return self.response

    def post(self, url, **kwargs):
        return self.response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

class MockCurlCffiResponse:
    def __init__(self, state):
        self.state = state

    @property
    def status_code(self):
        return self.state.status

    def json(self):
        return self.state._json

class MockCurlCffiSession:
    def __init__(self, response):
        self.response = response

    async def post(self, url, **kwargs):
        return self.response

    async def get(self, url, **kwargs):
        return self.response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.fixture
def mock_aiohttp_session(mocker):
    state = SharedState()
    
    # Mock aiohttp
    aiohttp_resp = MockAioHttpResponse(state)
    aiohttp_sess = MockAiohttpSession(aiohttp_resp)
    mocker.patch("app.epic.aiohttp.ClientSession", return_value=aiohttp_sess)
    
    # Mock curl-cffi
    curl_resp = MockCurlCffiResponse(state)
    curl_sess = MockCurlCffiSession(curl_resp)
    mocker.patch("app.epic.AsyncSession", return_value=curl_sess)
    
    return state


@pytest.mark.asyncio
async def test_get_free_games_success(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "title": "Free Game 1",
                            "urlSlug": "free-game-1",
                            "keyImages": [{"type": "Thumbnail", "url": "thumb1.jpg"}],
                            "promotions": {
                                "promotionalOffers": [
                                    {
                                        "promotionalOffers": [
                                            {
                                                "endDate": "2026-06-10T17:00:00.000Z",
                                                "discountSetting": {"discountPercentage": 0}
                                            }
                                        ]
                                    }
                                ],
                                "upcomingPromotionalOffers": []
                            }
                        },
                        {
                            "title": "Upcoming Game 1",
                            "productSlug": "upcoming-game-1",
                            "keyImages": [{"type": "Thumbnail", "url": "thumb2.jpg"}],
                            "promotions": {
                                "promotionalOffers": [],
                                "upcomingPromotionalOffers": [
                                    {
                                        "promotionalOffers": [
                                            {
                                                "startDate": "2026-06-10T17:00:00.000Z",
                                                "discountSetting": {"discountPercentage": 0}
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }
    
    result = await get_free_games()
    
    assert len(result["current"]) == 1
    assert result["current"][0]["title"] == "Free Game 1"
    assert result["current"][0]["slug"] == "free-game-1"
    assert result["current"][0]["end_date"] == "2026-06-10T17:00:00.000Z"
    assert result["current"][0]["thumbnail"] == "thumb1.jpg"
    
    assert len(result["upcoming"]) == 1
    assert result["upcoming"][0]["title"] == "Upcoming Game 1"
    assert result["upcoming"][0]["slug"] == "upcoming-game-1"
    assert result["upcoming"][0]["start_date"] == "2026-06-10T17:00:00.000Z"

@pytest.mark.asyncio
async def test_get_free_games_filters_truly_free(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "title": "Discounted Game (Not Free)",
                            "urlSlug": "discounted-game",
                            "promotions": {
                                "promotionalOffers": [
                                    {
                                        "promotionalOffers": [
                                            {
                                                "endDate": "2026-06-10T17:00:00.000Z",
                                                "discountSetting": {"discountPercentage": 50}
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }
    
    result = await get_free_games()
    
    assert len(result["current"]) == 0
    assert len(result["upcoming"]) == 0

@pytest.mark.asyncio
async def test_get_deals_success(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "title": "Deals Game 1",
                            "urlSlug": "deals-game-1",
                            "keyImages": [{"type": "Thumbnail", "url": "deals1.jpg"}],
                            "price": {
                                "totalPrice": {
                                    "originalPrice": 1000,
                                    "discountPrice": 300,
                                    "discount": 700,
                                    "currencyCode": "USD"
                                }
                            },
                            "promotions": {
                                "promotionalOffers": [
                                    {
                                        "promotionalOffers": [
                                            {
                                                "endDate": "2026-06-15T17:00:00.000Z",
                                                "discountSetting": {"discountPercentage": 70}
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }
    
    result = await get_deals(min_discount=50)
    
    assert len(result) == 1
    assert result[0]["title"] == "Deals Game 1"
    assert result[0]["slug"] == "deals-game-1"
    assert result[0]["original_price"] == 1000
    assert result[0]["final_price"] == 300
    assert result[0]["discount_percent"] == 70
    assert result[0]["currency"] == "USD"
    assert result[0]["end_date"] == "2026-06-15T17:00:00.000Z"
    assert result[0]["thumbnail"] == "deals1.jpg"

@pytest.mark.asyncio
async def test_get_deals_filters_by_min_discount(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "title": "Low Discount Game",
                            "urlSlug": "low-discount",
                            "price": {
                                "totalPrice": {
                                    "originalPrice": 1000,
                                    "discountPrice": 800,
                                    "discount": 200,
                                    "currencyCode": "USD"
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
    
    result = await get_deals(min_discount=50)
    assert len(result) == 0

@pytest.mark.asyncio
async def test_search_game_success(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "title": "Cyberpunk 2077",
                            "id": "egs-cp-id",
                            "namespace": "egs-cp-ns",
                            "urlSlug": "cyberpunk-2077"
                        }
                    ]
                }
            }
        }
    }
    
    result = await search_game("Cyberpunk 2077")
    
    assert result is not None
    assert result["title"] == "Cyberpunk 2077"
    assert result["slug"] == "cyberpunk-2077"
    assert result["epic_id"] == "egs-cp-id"
    assert result["namespace"] == "egs-cp-ns"

@pytest.mark.asyncio
async def test_search_game_empty(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": []
                }
            }
        }
    }
    
    result = await search_game("Unknown Game")
    assert result is None

@pytest.mark.asyncio
async def test_get_game_price_success(mock_aiohttp_session):
    mock_aiohttp_session.status = 200
    mock_aiohttp_session._json = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "title": "Cyberpunk 2077",
                            "urlSlug": "cyberpunk-2077",
                            "price": {
                                "totalPrice": {
                                    "originalPrice": 5999,
                                    "discountPrice": 5999,
                                    "discount": 0,
                                    "currencyCode": "USD"
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
    
    result = await get_game_price("cyberpunk-2077")
    
    assert result is not None
    assert result["title"] == "Cyberpunk 2077"
    assert result["slug"] == "cyberpunk-2077"
    assert result["original_price"] == 5999
    assert result["final_price"] == 5999
    assert result["discount_percent"] == 0
    assert result["currency"] == "USD"

def test_get_store_url():
    assert get_store_url("cyberpunk-2077") == "https://store.epicgames.com/p/cyberpunk-2077"

def test_normalize_epic_price():
    # USD (2 decimals, should not be multiplied)
    assert normalize_epic_price(1999, "USD") == 1999
    # CLP (EGS returns CLP with 2 decimals, so it shouldn't be multiplied)
    assert normalize_epic_price(999000, "CLP") == 999000
    # JPY (0 decimals on EGS, should be multiplied by 100 to match Steam cents convention)
    assert normalize_epic_price(5000, "JPY") == 500000
    # None handling
    assert normalize_epic_price(None, "USD") == 0

