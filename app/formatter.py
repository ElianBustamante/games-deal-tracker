import discord
from datetime import datetime
import app.steam as steam
from app.i18n import get_text

def format_price(cents: int, currency: str) -> str:
    if currency.upper() == "CLP":
        # Steam API always returns prices in cents, so we divide by 100 first
        val = int(cents / 100)
        formatted = f"{val:,}".replace(",", ".")
        return f"CLP$ {formatted}"
    elif currency.upper() == "USD":
        # Divide by 100
        formatted = f"{cents / 100:.2f}"
        return f"${formatted} USD"
    else:
        # Fallback
        return f"{cents} {currency}"

def make_deal_embed(game: dict, locale: str = "es") -> discord.Embed:
    # Colors and emojis
    if game.get("is_historical_low"):
        emoji = "🏆"
        color = discord.Color.gold()
    elif game.get("discount_percent", 0) >= 75:
        emoji = "🔥"
        color = discord.Color.green()
    elif game.get("discount_percent", 0) >= 50:
        emoji = "🎮"
        color = discord.Color.yellow()
    else:
        emoji = "🎮"
        color = discord.Color.orange()
        
    embed = discord.Embed(
        title=f"{emoji} {game.get('name', get_text('unknown_game', locale))}",
        url=game.get("url"),
        color=color
    )
    
    price_orig = format_price(game["price_original"], game["currency"])
    price_fin = format_price(game["price_final"], game["currency"])
    
    embed.add_field(name=get_text("price", locale), value=f"~~{price_orig}~~ → **{price_fin}**", inline=True)
    embed.add_field(name=get_text("discount", locale), value=f"-{game['discount_percent']}%", inline=True)
    
    # History
    historical_low = game.get("historical_low")
    if not historical_low:
        history_text = get_text("no_history", locale)
    elif game.get("is_historical_low"):
        history_text = get_text("historical_low_alert", locale)
    else:
        hist_price = format_price(historical_low["price_final"], game["currency"])
        try:
            # Parse recorded_at
            # SQLite CURRENT_TIMESTAMP format is 'YYYY-MM-DD HH:MM:SS'
            from datetime import UTC
            recorded_at = datetime.strptime(historical_low["recorded_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            days_ago = (datetime.now(UTC) - recorded_at).days
            history_text = get_text("historical_low", locale, price=hist_price, days=days_ago)
        except Exception:
            history_text = get_text("historical_low_no_date", locale, price=hist_price)
            
    embed.add_field(name=get_text("history", locale), value=history_text, inline=False)
    
    embed.set_thumbnail(url=steam.get_header_image_url(game["app_id"]))
    embed.set_footer(text=f"Steam Deals Bot • {datetime.now().strftime('%d/%m/%Y')}")
    
    return embed

def make_history_embed(game_name: str, history: list[dict], currency: str = "USD", locale: str = "es") -> discord.Embed:
    embed = discord.Embed(
        title=get_text("history_title", locale, game_name=game_name),
        color=discord.Color.blurple()
    )
    
    if not history:
        embed.add_field(name=get_text("no_records", locale), value=get_text("no_records_yet", locale), inline=False)
    else:
        for entry in history:
            price = format_price(entry["price_final"], currency)
            try:
                date_str = datetime.strptime(entry["recorded_at"], "%Y-%m-%d %H:%M:%S").strftime('%d/%m/%Y')
            except Exception:
                date_str = entry["recorded_at"]
            
            embed.add_field(
                name=f"{date_str}", 
                value=f"**{price}** (-{entry['discount_percent']}%)", 
                inline=False
            )
            
    return embed
