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

def test_embed_is_green_for_75_percent_discount():
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
    assert embed.color == discord.Color.green()
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
    embed = make_history_embed(1, "Game", [])
    assert len(embed.fields) == 1
    assert embed.fields[0].value == "Sin historial registrado aún"
