import pytest
import logging
from unittest.mock import AsyncMock, MagicMock
from app.logger import setup_logging, LOG_FILE
import app.steam as steam
import app.epic as epic
import app.bot as bot
import discord
from discord import app_commands

@pytest.mark.asyncio
async def test_logging_configuration():
    # Force setup by temporarily clearing pytest's default handlers
    root_logger = logging.getLogger()
    old_handlers = root_logger.handlers.copy()
    root_logger.handlers.clear()
    
    try:
        setup_logging()
        assert len(root_logger.handlers) >= 2
        handler_names = [type(h).__name__ for h in root_logger.handlers]
        assert "StreamHandler" in handler_names
        assert "RotatingFileHandler" in handler_names
    finally:
        # Restore handlers for pytest log capture
        root_logger.handlers = old_handlers

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

@pytest.mark.asyncio
async def test_steam_fetch_url_retries_and_succeeds(mocker):
    # Mocking sequential behaviors: fail twice, then succeed
    fail_resp = MockResponse(status=500)
    success_resp = MockResponse(json_data={"items": [{"id": 123, "name": "Test Game"}]}, status=200)
    
    # We patch ClientSession to return different sessions or mock the get call
    mocker.patch("app.steam.asyncio.sleep", return_value=None)  # skip sleep delay
    
    responses = [fail_resp, fail_resp, success_resp]
    
    class MockSession:
        def __init__(self):
            self.idx = 0
            
        def get(self, url, **kwargs):
            resp = responses[self.idx]
            self.idx += 1
            return resp

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

    mocker.patch("app.steam.aiohttp.ClientSession", return_value=MockSession())
    
    # Trigger get_game_price search_game which uses _fetch_url under the hood
    res = await steam.search_game("Test Game")
    assert res is not None
    assert res["app_id"] == 123
    assert res["name"] == "Test Game"

@pytest.mark.asyncio
async def test_steam_fetch_url_fails_all_attempts(mocker):
    fail_resp = MockResponse(status=500)
    mocker.patch("app.steam.asyncio.sleep", return_value=None)
    
    class MockSession:
        def get(self, url, **kwargs):
            return fail_resp

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

    mocker.patch("app.steam.aiohttp.ClientSession", return_value=MockSession())
    
    res = await steam.search_game("Test Game")
    assert res is None

class MockCurlResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code

    def json(self):
        return self._json

@pytest.mark.asyncio
async def test_epic_post_graphql_retries_and_succeeds(mocker):
    # Setup curl_cffi mock with productSlug to pass resolve_epic_slug
    fail_resp = MockCurlResponse(status_code=500)
    success_resp = MockCurlResponse(
        json_data={
            "data": {
                "Catalog": {
                    "searchStore": {
                        "elements": [
                            {
                                "title": "Epic Game",
                                "id": "123",
                                "productSlug": "epic-game"
                            }
                        ]
                    }
                }
            }
        },
        status_code=200
    )
    
    mocker.patch("app.epic.asyncio.sleep", return_value=None)
    
    responses = [fail_resp, fail_resp, success_resp]
    idx = 0
    
    async def mock_post(url, headers, json, timeout):
        nonlocal idx
        resp = responses[idx]
        idx += 1
        return resp
        
    mock_session_inst = MagicMock()
    mock_session_inst.post = AsyncMock(side_effect=mock_post)
    
    class MockSessionContext:
        def __init__(self, impersonate):
            pass
        async def __aenter__(self):
            return mock_session_inst
        async def __aexit__(self, exc_type, exc, tb):
            pass
            
    mocker.patch("app.epic.AsyncSession", side_effect=MockSessionContext)
    
    res = await epic.search_game("Epic Game")
    assert res is not None
    assert res["title"] == "Epic Game"
    assert res["slug"] == "epic-game"

@pytest.mark.asyncio
async def test_tree_error_handler_user_feedback(mocker):
    # Mock interaction
    interaction = MagicMock(spec=discord.Interaction)
    interaction.command = MagicMock()
    interaction.command.name = "compare"
    interaction.locale = discord.Locale.american_english
    
    # Mock interaction response state
    interaction.response = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    
    error = app_commands.AppCommandError("Some API issue")
    
    # Invoke the handler
    await bot.on_app_command_error(interaction, error)
    
    # Assert send_message was called with the unexpected error text
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "unexpected error" in args[0].lower()
    assert kwargs.get("ephemeral") is True
