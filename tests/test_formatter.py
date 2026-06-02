import pytest
import discord
from app.formatter import make_deal_embed, make_history_embed

def test_embed_is_gold_when_historical_low():
    game = {
        "app_id": 1,
        "name": "Test Game",
        "price_original": 1000,
        "price_final": 500,
        "discount_percent": 50,
        "currency": "USD",
        "url": "http://store",
        "is_historical_low": True,
        "historical_low": None
    }
    
    embed = make_deal_embed(game)
    assert embed.color == discord.Color.gold()
    assert embed.title.startswith("🏆")
    assert embed.author.name == "Steam"
    assert "Steam_icon_logo" in embed.author.icon_url

def test_embed_is_steam_blue_for_discount():
    game = {
        "app_id": 1,
        "name": "Test Game",
        "price_original": 1000,
        "price_final": 250,
        "discount_percent": 75,
        "currency": "USD",
        "url": "http://store",
        "is_historical_low": False,
        "historical_low": {"price_final": 100, "recorded_at": "2026-01-01 00:00:00"}
    }
    
    embed = make_deal_embed(game)
    assert embed.color == discord.Color.from_rgb(102, 192, 244)
    assert embed.title.startswith("🔥")

def test_history_field_no_history():
    game = {
        "app_id": 1, "name": "Test Game", "price_original": 1000, "price_final": 500,
        "discount_percent": 50, "currency": "USD", "url": "http://store",
        "is_historical_low": True, "historical_low": None
    }
    embed = make_deal_embed(game)
    assert embed.fields[2].value == "📊 Primer registro — sin historial previo"

def test_history_field_historical_low():
    game = {
        "app_id": 1, "name": "Test Game", "price_original": 1000, "price_final": 500,
        "discount_percent": 50, "currency": "USD", "url": "http://store",
        "is_historical_low": True, "historical_low": {"price_final": 500, "recorded_at": "2026-01-01 00:00:00"}
    }
    embed = make_deal_embed(game)
    assert embed.fields[2].value == "🏆 ¡Precio mínimo histórico registrado!"

def test_history_field_not_historical_low():
    game = {
        "app_id": 1, "name": "Test Game", "price_original": 1000, "price_final": 500,
        "discount_percent": 50, "currency": "USD", "url": "http://store",
        "is_historical_low": False, "historical_low": {"price_final": 200, "recorded_at": "2026-01-01 00:00:00"}
    }
    embed = make_deal_embed(game)
    assert "Mínimo registrado" in embed.fields[2].value

def test_make_history_embed_empty():
    embed = make_history_embed("Game", [])
    assert len(embed.fields) == 1
    assert embed.fields[0].value == "Sin historial registrado aún"

def test_make_epic_deal_embed():
    from app.formatter import make_epic_deal_embed
    game = {
        "title": "Epic Game",
        "slug": "epic-game",
        "original_price": 2000,
        "final_price": 1000,
        "discount_percent": 50,
        "currency": "USD",
        "is_historical_low": False,
        "historical_low": None
    }
    embed = make_epic_deal_embed(game)
    assert embed.color.value == 0x9b59b6
    assert embed.title == "🟣 Epic Game"
    assert embed.fields[0].name == "Precio Original"
    assert embed.fields[0].value == "~~$20.00 USD~~"
    assert embed.fields[1].name == "Precio Final"
    assert embed.fields[1].value == "$10.00 USD (-50%)"
    assert embed.author.name == "Epic Games Store"
    assert "Epic_Games_logo" in embed.author.icon_url

def test_make_epic_free_embed():
    from app.formatter import make_epic_free_embed
    current = [{"title": "Free Now", "slug": "free-now", "end_date": "2026-06-10T17:00:00.000Z"}]
    upcoming = [{"title": "Free Later", "slug": "free-later", "start_date": "2026-06-17T17:00:00.000Z"}]
    embed = make_epic_free_embed(current, upcoming)
    assert embed.title == "🎁 Juegos Gratis — Epic Games"
    assert embed.author.name == "Epic Games Store"
    assert "Epic_Games_logo" in embed.author.icon_url
    assert len(embed.fields) == 2
    assert "Free Now" in embed.fields[0].value
    assert "Free Later" in embed.fields[1].value

def test_make_comparison_embed():
    from app.formatter import make_comparison_embed
    steam = {
        "app_id": 123,
        "price_original": 2000,
        "price_final": 1000,
        "discount_percent": 50,
        "currency": "USD",
        "url": "http://steam"
    }
    epic = {
        "slug": "compare-game",
        "original_price": 2000,
        "final_price": 800,
        "discount_percent": 60,
        "currency": "USD"
    }
    embed = make_comparison_embed("Compare Game", steam, epic, [], [])
    assert embed.title == "⚖️ Comparación de precios — Compare Game"
    assert embed.fields[0].name == "🟦 Steam"
    assert embed.fields[1].name == "🟣 Epic Games"
    assert "Epic" in embed.footer.text  # Epic is cheaper ($8 vs $10)

def test_deal_view_initialization():
    from app.formatter import DealView
    view = DealView(
        store_url="https://store.url",
        app_id="12345",
        game_name="Test Game",
        epic_slug="test-slug",
        locale="es"
    )
    assert len(view.children) == 2
    # Verify link button
    assert view.children[0].label == "Ver Oferta"
    assert view.children[0].url == "https://store.url"
    assert view.children[0].style == discord.ButtonStyle.link
    # Verify watchlist button
    assert view.children[1].label == "Añadir a Deseados"
    assert view.children[1].style == discord.ButtonStyle.secondary
    assert view.children[1].custom_id == "track_12345"

@pytest.mark.asyncio
async def test_deal_view_callback_admin_success(mocker):
    from app.formatter import DealView
    from unittest.mock import AsyncMock, MagicMock
    mock_add = mocker.patch("app.database.add_to_watchlist", new_callable=AsyncMock, return_value=True)
    
    view = DealView(
        store_url="https://store.url",
        app_id="12345",
        game_name="Test Game",
        epic_slug="test-slug",
        locale="es"
    )
    
    # Mock interaction
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = MagicMock()
    interaction.guild.id = 9999
    # User has admin permission
    interaction.user.guild_permissions.administrator = True
    interaction.response.send_message = AsyncMock()
    
    await view.track_callback(interaction)
    
    mock_add.assert_called_once_with("9999", "12345", "Test Game", "test-slug")
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "añadió" in args[0]
    assert kwargs.get("ephemeral") is True

@pytest.mark.asyncio
async def test_deal_view_callback_no_admin(mocker):
    from app.formatter import DealView
    from unittest.mock import AsyncMock, MagicMock
    mock_add = mocker.patch("app.database.add_to_watchlist", new_callable=AsyncMock)
    
    view = DealView(
        store_url="https://store.url",
        app_id="12345",
        game_name="Test Game",
        epic_slug="test-slug",
        locale="es"
    )
    
    # Mock interaction
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = MagicMock()
    interaction.guild.id = 9999
    # User does NOT have admin permission
    interaction.user.guild_permissions.administrator = False
    interaction.response.send_message = AsyncMock()
    
    await view.track_callback(interaction)
    
    mock_add.assert_not_called()
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "Solo los administradores" in args[0]
    assert kwargs.get("ephemeral") is True

