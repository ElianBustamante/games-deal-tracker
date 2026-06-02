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
    assert embed.author.name == "Steam Deals"
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
    assert embed.fields[0].name == "Precio"
    assert embed.fields[0].value == "~~$20.00 USD~~ → **$10.00 USD**"
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

