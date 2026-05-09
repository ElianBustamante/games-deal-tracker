from app.i18n import get_text
import discord

def test_get_text_spanish_by_default():
    assert get_text("price", "unknown") == "Precio"

def test_get_text_spanish_locale():
    # discord.Locale.spain_spanish is 'es-ES'
    assert get_text("price", "es-ES") == "Precio"
    assert get_text("price", discord.Locale.latin_american_spanish) == "Precio"

def test_get_text_english_locale():
    assert get_text("price", "en-US") == "Price"
    assert get_text("price", discord.Locale.american_english) == "Price"

def test_get_text_with_kwargs():
    # Spanish
    assert get_text("discount_set", "es-ES", percent=50) == "✅ Alertas generales configuradas a mínimo **50%** de descuento."
    # English
    assert get_text("discount_set", "en-US", percent=75) == "✅ General alerts configured for a minimum of **75%** off."

def test_get_text_fallback_key():
    assert get_text("missing_key", "es-ES") == "missing_key"
