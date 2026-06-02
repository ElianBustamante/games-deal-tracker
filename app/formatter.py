import discord
from datetime import datetime
import app.steam as steam
import app.epic as epic
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
        # Fallback for other currencies
        return f"{cents / 100:.2f} {currency}"

def make_deal_embed(game: dict, locale: str = "es") -> discord.Embed:
    # Colors and emojis
    if game.get("is_historical_low"):
        emoji = "🏆"
        color = discord.Color.gold()
    else:
        if game.get("discount_percent", 0) >= 75:
            emoji = "🔥"
        else:
            emoji = "🎮"
        color = discord.Color.from_rgb(102, 192, 244)  # Steam blue #66c0f4
        
    embed = discord.Embed(
        title=f"{emoji} {game.get('name', get_text('unknown_game', locale))}",
        url=game.get("url"),
        color=color
    )
    
    # Add author header
    steam_icon = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/512px-Steam_icon_logo.svg.png"
    embed.set_author(name="Steam Deals", icon_url=steam_icon)
    
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
    
    footer_text = f"Steam Deals Bot • {datetime.now().strftime('%d/%m/%Y')}"
    epic_price = game.get("epic_price")
    if epic_price:
        steam_final = game["price_final"]
        epic_final = epic_price.get("price_final") or epic_price.get("final_price") or 0
        epic_formatted = format_price(epic_final, game["currency"])
        
        if game["currency"].upper() == epic_price["currency"].upper():
            if steam_final < epic_final:
                winner_label = "💚 Más barato en Steam" if locale == "es" else "💚 Cheaper on Steam"
            elif epic_final < steam_final:
                winner_label = "🟣 Más barato en Epic" if locale == "es" else "🟣 Cheaper on Epic"
            else:
                winner_label = "🟰 Mismo precio" if locale == "es" else "🟰 Same price"
            footer_text += f" • Epic: {epic_formatted} ({winner_label})"
        else:
            footer_text += f" • Epic: {epic_formatted}"
            
    embed.set_footer(text=footer_text)
    
    return embed

def make_epic_deal_embed(game: dict, locale: str = "es") -> discord.Embed:
    # Emojis and colors
    if game.get("is_historical_low"):
        emoji = "🏆"
        color = discord.Color.gold()
    else:
        emoji = "🟣"
        color = 0x9b59b6  # Purple for Epic Games
        
    name = game.get("name") or game.get("title") or get_text("unknown_game", locale)
    url = game.get("url") or (epic.get_store_url(game["slug"]) if game.get("slug") else None)
    
    embed = discord.Embed(
        title=f"{emoji} {name}",
        url=url,
        color=color
    )
    
    # Add author header
    epic_icon = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Epic_Games_logo.svg/512px-Epic_Games_logo.svg.png"
    embed.set_author(name="Epic Games Store", icon_url=epic_icon)
    
    price_orig_cents = game.get("price_original") or game.get("original_price") or 0
    price_fin_cents = game.get("price_final") or game.get("final_price") or 0
    
    price_orig = format_price(price_orig_cents, game["currency"])
    price_fin = format_price(price_fin_cents, game["currency"])
    
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
            from datetime import UTC
            recorded_at = datetime.strptime(historical_low["recorded_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            days_ago = (datetime.now(UTC) - recorded_at).days
            history_text = get_text("historical_low", locale, price=hist_price, days=days_ago)
        except Exception:
            history_text = get_text("historical_low_no_date", locale, price=hist_price)
            
    embed.add_field(name=get_text("history", locale), value=history_text, inline=False)
    
    if game.get("thumbnail"):
        embed.set_thumbnail(url=game["thumbnail"])
        
    embed.set_footer(text=f"{get_text('epic_store', locale)} • {datetime.now().strftime('%d/%m/%Y')}")
    
    return embed

def make_epic_free_embed(current: list[dict], upcoming: list[dict], locale: str = "es") -> discord.Embed:
    embed = discord.Embed(
        title=get_text("epic_free_title", locale),
        color=0x2ecc71  # Green for free
    )
    
    # Add author header
    epic_icon = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Epic_Games_logo.svg/512px-Epic_Games_logo.svg.png"
    embed.set_author(name="Epic Games Store", icon_url=epic_icon)
    
    # Available now
    if current:
        lines = []
        for g in current:
            url = epic.get_store_url(g["slug"])
            try:
                date_obj = datetime.strptime(g["end_date"][:19], "%Y-%m-%dT%H:%M:%S")
                date_str = date_obj.strftime("%d/%m/%Y")
            except Exception:
                date_str = g["end_date"]
            lines.append(f"**[{g['title']}]({url})**\n*{get_text('ends_on', locale, date=date_str)}*")
        embed.add_field(name=get_text("available_now", locale), value="\n\n".join(lines), inline=False)
        
        # Set first game's thumbnail as embed thumbnail
        if current[0].get("thumbnail"):
            embed.set_thumbnail(url=current[0]["thumbnail"])
            
    # Upcoming
    if upcoming:
        lines = []
        for g in upcoming:
            url = epic.get_store_url(g["slug"])
            try:
                date_obj = datetime.strptime(g["start_date"][:19], "%Y-%m-%dT%H:%M:%S")
                date_str = date_obj.strftime("%d/%m/%Y")
            except Exception:
                date_str = g["start_date"]
            lines.append(f"**[{g['title']}]({url})**\n*{get_text('starts_on', locale, date=date_str)}*")
        embed.add_field(name=get_text("coming_soon", locale), value="\n\n".join(lines), inline=False)
        
    embed.set_footer(text=get_text("free_games_footer", locale))
    
    return embed

def make_comparison_embed(
    game_name: str,
    steam: dict | None,
    epic: dict | None,
    steam_history: list[dict],
    epic_history: list[dict],
    locale: str = "es"
) -> discord.Embed:
    embed = discord.Embed(
        title=get_text("comparison_title", locale, game_name=game_name),
        color=0xf39c12  # Amber/Orange for neutral comparison
    )
    
    # Steam section
    if steam:
        steam_url = steam.get("url") or steam.get("url") or (steam.get("app_id") and steam.get_store_url(steam["app_id"]))
        if not steam_url and steam.get("app_id"):
            steam_url = steam.get_store_url(steam["app_id"]) if hasattr(steam, 'get_store_url') else f"https://store.steampowered.com/app/{steam['app_id']}/"
            
        orig_formatted = format_price(steam["price_original"], steam["currency"])
        final_formatted = format_price(steam["price_final"], steam["currency"])
        
        steam_val = f"~~{orig_formatted}~~ → **{final_formatted}** (-{steam['discount_percent']}%)\n"
        if steam_history:
            low_val = min(h["price_final"] for h in steam_history)
            low_formatted = format_price(low_val, steam["currency"])
            steam_val += f"📉 {get_text('history', locale)}: {low_formatted}\n"
        else:
            steam_val += f"📊 {get_text('no_records_yet', locale)}\n"
        steam_val += f"🔗 [Steam Store]({steam_url})"
        
        # Set thumbnail if available
        if steam.get("app_id"):
            embed.set_thumbnail(url=steam.get_header_image_url(steam["app_id"]) if hasattr(steam, 'get_header_image_url') else f"https://cdn.cloudflare.steamstatic.com/steam/apps/{steam['app_id']}/header.jpg")
    else:
        steam_val = get_text("not_available", locale)
        
    embed.add_field(name="🟦 Steam", value=steam_val, inline=True)
    
    # Epic section
    if epic:
        epic_url = epic.get("url") or epic.get_store_url(epic["slug"]) if hasattr(epic, 'get_store_url') else f"https://store.epicgames.com/p/{epic['slug']}"
        orig_cents = epic.get("price_original") or epic.get("original_price") or 0
        final_cents = epic.get("price_final") or epic.get("final_price") or 0
        
        orig_formatted = format_price(orig_cents, epic["currency"])
        final_formatted = format_price(final_cents, epic["currency"])
        
        epic_val = f"~~{orig_formatted}~~ → **{final_formatted}** (-{epic['discount_percent']}%)\n"
        if epic_history:
            low_val = min(h["price_final"] for h in epic_history)
            low_formatted = format_price(low_val, epic["currency"])
            epic_val += f"📉 {get_text('history', locale)}: {low_formatted}\n"
        else:
            epic_val += f"📊 {get_text('no_records_yet', locale)}\n"
        epic_val += f"🔗 [Epic Store]({epic_url})"
        
        # Set thumbnail if Steam thumbnail was not set
        if not steam and epic.get("thumbnail"):
            embed.set_thumbnail(url=epic["thumbnail"])
    else:
        epic_val = get_text("not_available", locale)
        
    embed.add_field(name="🟣 Epic Games", value=epic_val, inline=True)
    
    # Determine the winner to place in footer
    footer_text = ""
    if steam and epic:
        steam_final = steam["price_final"]
        epic_final = epic.get("price_final") or epic.get("final_price") or 0
        
        if steam["currency"].upper() == epic["currency"].upper():
            if steam_final < epic_final:
                winner_text = get_text("best_price_steam", locale)
            elif epic_final < steam_final:
                winner_text = get_text("best_price_epic", locale)
            else:
                winner_text = get_text("best_price_equal", locale)
                
            footer_text += winner_text
            
            # History comparison
            if steam_history and epic_history:
                steam_low = min(h["price_final"] for h in steam_history)
                epic_low = min(h["price_final"] for h in epic_history)
                
                if steam_low < epic_low:
                    hist_winner = get_text("lowest_hist_steam", locale)
                elif epic_low < steam_low:
                    hist_winner = get_text("lowest_hist_epic", locale)
                else:
                    hist_winner = get_text("lowest_hist_equal", locale)
                    
                footer_text += f"\n{hist_winner}"
    
    if footer_text:
        embed.set_footer(text=footer_text)
        
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
