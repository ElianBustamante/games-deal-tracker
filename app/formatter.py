import discord
from datetime import datetime
import app.steam as steam

def format_price(cents: int, currency: str) -> str:
    if currency.upper() == "CLP":
        # Divide by 1 and format with dot as thousands separator
        formatted = f"{cents:,}".replace(",", ".")
        return f"${formatted} CLP"
    elif currency.upper() == "USD":
        # Divide by 100
        formatted = f"{cents / 100:.2f}"
        return f"${formatted} USD"
    else:
        # Fallback
        return f"{cents} {currency}"

def make_deal_embed(game: dict) -> discord.Embed:
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
        title=f"{emoji} {game.get('name', 'Juego Desconocido')}",
        url=game.get("url"),
        color=color
    )
    
    price_orig = format_price(game["price_original"], game["currency"])
    price_fin = format_price(game["price_final"], game["currency"])
    
    embed.add_field(name="Precio", value=f"~~{price_orig}~~ → **{price_fin}**", inline=True)
    embed.add_field(name="Descuento", value=f"-{game['discount_percent']}%", inline=True)
    
    # History
    historical_low = game.get("historical_low")
    if not historical_low:
        history_text = "📊 Primer registro — sin historial previo"
    elif game.get("is_historical_low"):
        history_text = "🏆 ¡Precio mínimo histórico registrado!"
    else:
        hist_price = format_price(historical_low["price_final"], game["currency"])
        try:
            # Parse recorded_at
            # SQLite CURRENT_TIMESTAMP format is 'YYYY-MM-DD HH:MM:SS'
            from datetime import UTC
            recorded_at = datetime.strptime(historical_low["recorded_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            days_ago = (datetime.now(UTC) - recorded_at).days
            history_text = f"⚠️ Mínimo registrado: {hist_price} ({days_ago} días atrás)"
        except Exception:
            history_text = f"⚠️ Mínimo registrado: {hist_price}"
            
    embed.add_field(name="Historial", value=history_text, inline=False)
    
    embed.set_thumbnail(url=steam.get_header_image_url(game["app_id"]))
    embed.set_footer(text=f"Steam Deals Bot • {datetime.now().strftime('%d/%m/%Y')}")
    
    return embed

def make_history_embed(app_id: int, game_name: str, history: list[dict], currency: str = "USD") -> discord.Embed:
    embed = discord.Embed(
        title=f"📈 Historial de precios — {game_name}",
        color=discord.Color.blurple()
    )
    
    if not history:
        embed.add_field(name="Sin registros", value="Sin historial registrado aún", inline=False)
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
