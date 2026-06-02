import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

import app.steam as steam
import app.database as database
import app.checker as checker
import app.epic as epic
from app.formatter import make_history_embed, make_comparison_embed, make_epic_free_embed
from app.i18n import BotTranslator, get_text

STEAM_COUNTRIES = {
    "Argentina": "ar",
    "Australia": "au",
    "Brazil": "br",
    "Canada": "ca",
    "Chile": "cl",
    "China": "cn",
    "Colombia": "co",
    "Costa Rica": "cr",
    "European Union": "es",
    "Hong Kong": "hk",
    "India": "in",
    "Indonesia": "id",
    "Israel": "il",
    "Japan": "jp",
    "Kazakhstan": "kz",
    "Kuwait": "kw",
    "Malaysia": "my",
    "Mexico": "mx",
    "New Zealand": "nz",
    "Norway": "no",
    "Peru": "pe",
    "Philippines": "ph",
    "Poland": "pl",
    "Qatar": "qa",
    "Russia": "ru",
    "Saudi Arabia": "sa",
    "Singapore": "sg",
    "South Africa": "za",
    "South Korea": "kr",
    "Switzerland": "ch",
    "Taiwan": "tw",
    "Thailand": "th",
    "United Arab Emirates": "ae",
    "United Kingdom": "gb",
    "United States": "us",
    "Uruguay": "uy",
    "Vietnam": "vn"
}

async def country_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=name, value=code)
        for name, code in STEAM_COUNTRIES.items()
        if current.lower() in name.lower()
    ][:25]

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

class SteamDealsBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=discord.Intents.default()
        )

    async def setup_hook(self):
        await self.tree.set_translator(BotTranslator())
        await database.init_db()
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guilds")

    async def on_guild_remove(self, guild: discord.Guild):
        await database.stop_notifications(str(guild.id))
        print(f"Bot removed from guild {guild.id} — data deleted.")

def get_target_id(interaction: discord.Interaction) -> tuple[str, bool]:
    if interaction.guild_id:
        return str(interaction.guild_id), False
    return str(interaction.user.id), True

async def ensure_dm_setup(target_id: str, is_dm: bool):
    if is_dm:
        await database.set_channel(target_id, target_id, is_dm=True)

bot = SteamDealsBot()

async def game_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not current or len(current) < 3:
        return []
    
    target_id, _ = get_target_id(interaction)
    country = await database.get_country(target_id)
    language = await database.get_language(target_id)
    
    results = await steam.search_game_autocomplete(current, country=country, language=language)
    
    choices = []
    for r in results:
        name = r["name"][:100]
        choices.append(app_commands.Choice(name=name, value=name))
    
    return choices

watchlist_group = app_commands.Group(
    name="watchlist", 
    description="Gestiona la lista de deseados",
    allowed_installs=app_commands.AppInstallationType(guild=True, user=True),
    allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True)
)

@watchlist_group.command(name="add", description="Añade un juego a la lista de seguimiento")
@app_commands.describe(game="Nombre del juego")
@app_commands.autocomplete(game=game_autocomplete)
async def watchlist_add(interaction: discord.Interaction, game: str):
    await interaction.response.defer(ephemeral=True)
    
    target_id, is_dm = get_target_id(interaction)
    await ensure_dm_setup(target_id, is_dm)
    
    language = await database.get_language(target_id)
    
    # 1. Search Steam
    steam_result = await steam.search_game(game)
    
    # 2. Search Epic
    epic_result = await epic.search_game(game, language)
    
    if not steam_result and not epic_result:
        # Not found anywhere
        await interaction.followup.send(get_text("game_not_found", interaction.locale), ephemeral=True)
        return
        
    if steam_result:
        # Steam game found
        app_id = steam_result["app_id"]
        game_name = steam_result["name"]
        epic_slug = epic_result["slug"] if epic_result else None
        
        added = await database.add_to_watchlist(target_id, app_id, game_name, epic_slug)
        if added:
            # Format custom multi-store confirmation
            if str(interaction.locale).startswith("en"):
                msg = f"✅ Added **{game_name}** to the watchlist\n"
                msg += f"🟦 Steam: Found (ID: {app_id})\n"
                msg += f"🟣 Epic: {'Found (Slug: ' + epic_slug + ')' if epic_slug else 'Not available'}"
            else:
                msg = f"✅ Se añadió **{game_name}** a la lista de deseados\n"
                msg += f"🟦 Steam: Encontrado (ID: {app_id})\n"
                msg += f"🟣 Epic: {'Encontrado (Slug: ' + epic_slug + ')' if epic_slug else 'No disponible'}"
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.followup.send(get_text("already_in_list", interaction.locale), ephemeral=True)
    else:
        # EGS Exclusive game found (Not on Steam)
        epic_slug = epic_result["slug"]
        game_name = epic_result["title"]
        # Save as epic:slug in app_id column
        app_id = f"epic:{epic_slug}"
        
        added = await database.add_to_watchlist(target_id, app_id, game_name, epic_slug)
        if added:
            if str(interaction.locale).startswith("en"):
                msg = f"✅ Added **{game_name}** to the watchlist\n"
                msg += f"🟦 Steam: Not available\n"
                msg += f"🟣 Epic: Found (Slug: {epic_slug})"
            else:
                msg = f"✅ Se añadió **{game_name}** a la lista de deseados\n"
                msg += f"🟦 Steam: No disponible\n"
                msg += f"🟣 Epic: Encontrado (Slug: {epic_slug})"
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.followup.send(get_text("already_in_list", interaction.locale), ephemeral=True)

@watchlist_group.command(name="remove", description="Elimina un juego de la lista de seguimiento")
@app_commands.describe(game="Nombre del juego")
@app_commands.autocomplete(game=game_autocomplete)
async def watchlist_remove(interaction: discord.Interaction, game: str):
    await interaction.response.defer(ephemeral=True)
    
    target_id, _ = get_target_id(interaction)
    language = await database.get_language(target_id)
    
    # Check Steam
    search_result = await steam.search_game(game)
    app_id_to_remove = None
    game_name = None
    
    if search_result:
        app_id_to_remove = search_result["app_id"]
        game_name = search_result["name"]
    else:
        # Check Epic for exclusive games
        epic_result = await epic.search_game(game, language)
        if epic_result:
            app_id_to_remove = f"epic:{epic_result['slug']}"
            game_name = epic_result["title"]
            
    if not app_id_to_remove:
        await interaction.followup.send(get_text("game_not_found", interaction.locale), ephemeral=True)
        return
        
    removed = await database.remove_from_watchlist(target_id, app_id_to_remove)
    if removed:
        await interaction.followup.send(get_text("removed_from_list", interaction.locale, name=game_name), ephemeral=True)
    else:
        await interaction.followup.send(get_text("not_in_list", interaction.locale), ephemeral=True)

@watchlist_group.command(name="show", description="Muestra todos los juegos monitoreados")
async def watchlist_show(interaction: discord.Interaction):
    await interaction.response.defer()
    
    target_id, _ = get_target_id(interaction)
    watchlist = await database.get_watchlist(target_id)
    
    if not watchlist:
        await interaction.followup.send(get_text("list_empty", interaction.locale))
        return
        
    embed = discord.Embed(title=get_text("watchlist_title", interaction.locale), color=discord.Color.blue())
    
    for game in watchlist:
        app_id_str = str(game["app_id"])
        is_epic_only = app_id_str.startswith("epic:") or not app_id_str.isdigit()
        
        if is_epic_only:
            slug = app_id_str.replace("epic:", "")
            price = await epic.get_game_price(slug)
            if price and price.get("discount_percent", 0) > 0:
                status = get_text("status_discount", interaction.locale, discount=price['discount_percent'])
            else:
                status = get_text("status_no_discount", interaction.locale)
                
            embed.add_field(
                name=f"🟣 {game['game_name']}", 
                value=f"{get_text('status', interaction.locale)}: {status}\n{get_text('added', interaction.locale)}: {game['added_at'][:10]}",
                inline=False
            )
        else:
            price = await steam.get_game_price(game["app_id"])
            if price and price.get("discount_percent", 0) > 0:
                status = get_text("status_discount", interaction.locale, discount=price['discount_percent'])
            else:
                status = get_text("status_no_discount", interaction.locale)
                
            embed.add_field(
                name=f"🟦 {game['game_name']}", 
                value=f"{get_text('status', interaction.locale)}: {status}\n{get_text('added', interaction.locale)}: {game['added_at'][:10]}",
                inline=False
            )
        
    await interaction.followup.send(embed=embed)

bot.tree.add_command(watchlist_group)

@bot.tree.command(name="setsteamchannel", description="Configura el canal donde se enviarán las alertas de Steam")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.guild_only()
@app_commands.describe(channel="El canal para las alertas de Steam")
@app_commands.checks.has_permissions(manage_channels=True)
async def setsteamchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    target_id, is_dm = get_target_id(interaction)
    await database.set_channel(target_id, str(channel.id), is_dm=False)
    await interaction.response.send_message(get_text("alerts_channel_set", interaction.locale, mention=channel.mention), ephemeral=True)

@bot.tree.command(name="setepicchannel", description="Configura el canal donde se enviarán las alertas de Epic Games")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.guild_only()
@app_commands.describe(channel="El canal para las alertas de Epic")
@app_commands.checks.has_permissions(manage_channels=True)
async def setepicchannel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_id, _ = get_target_id(interaction)
    if channel:
        await database.set_epic_channel(target_id, str(channel.id))
        await interaction.response.send_message(get_text("epic_channel_set", interaction.locale, mention=channel.mention), ephemeral=True)
    else:
        await database.set_epic_channel(target_id, None)
        await interaction.response.send_message(get_text("epic_channel_fallback", interaction.locale), ephemeral=True)

@bot.tree.command(name="setdiscount", description="Configura el descuento mínimo % para alertas generales")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(percent="Porcentaje (1-100)")
async def setdiscount(interaction: discord.Interaction, percent: int):
    target_id, is_dm = get_target_id(interaction)
    
    if not is_dm and not interaction.permissions.manage_channels:
        await interaction.response.send_message(get_text("no_permissions", interaction.locale), ephemeral=True)
        return
        
    if percent < 1 or percent > 100:
        await interaction.response.send_message(get_text("invalid_percent", interaction.locale), ephemeral=True)
        return
        
    await ensure_dm_setup(target_id, is_dm)
    await database.set_min_discount(target_id, percent)
    await interaction.response.send_message(get_text("discount_set", interaction.locale, percent=percent), ephemeral=True)

@bot.tree.command(name="setlanguage", description="Configura el idioma para las alertas automáticas")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(lang="Idioma (en o es)")
@app_commands.choices(lang=[
    app_commands.Choice(name="English", value="en"),
    app_commands.Choice(name="Español", value="es")
])
async def setlanguage(interaction: discord.Interaction, lang: str):
    target_id, is_dm = get_target_id(interaction)
    if not is_dm and not interaction.permissions.manage_channels:
        await interaction.response.send_message(get_text("no_permissions", interaction.locale), ephemeral=True)
        return
        
    await ensure_dm_setup(target_id, is_dm)
    await database.set_language(target_id, lang)
    await interaction.response.send_message(get_text("language_set", lang), ephemeral=True)

@bot.tree.command(name="setcountry", description="Configura el país para obtener precios locales de Steam")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(country="Nombre del país")
@app_commands.autocomplete(country=country_autocomplete)
async def setcountry(interaction: discord.Interaction, country: str):
    target_id, is_dm = get_target_id(interaction)
    if not is_dm and not interaction.permissions.manage_channels:
        await interaction.response.send_message(get_text("no_permissions", interaction.locale), ephemeral=True)
        return
        
    await ensure_dm_setup(target_id, is_dm)
    await database.set_country(target_id, country)
    await interaction.response.send_message(get_text("country_set", interaction.locale, country=country.upper()), ephemeral=True)

@bot.tree.command(name="stop", description="Detiene las notificaciones y borra tus datos")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def stop_alerts(interaction: discord.Interaction):
    target_id, is_dm = get_target_id(interaction)
    if not is_dm and not interaction.permissions.manage_channels:
        await interaction.response.send_message(get_text("no_permissions", interaction.locale), ephemeral=True)
        return
        
    await database.stop_notifications(target_id)
    await interaction.response.send_message(get_text("alerts_stopped", interaction.locale), ephemeral=True)

@bot.tree.command(name="steamdeals", description="Busca ofertas de Steam manualmente en este momento")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def steamdeals(interaction: discord.Interaction):
    await interaction.response.send_message(get_text("searching", interaction.locale))
    
    stats = await checker.check_and_notify(bot)
    
    await interaction.followup.send(
        get_text("search_complete", interaction.locale, targets=stats['targets_checked'], deals=stats['total_deals_sent'])
    )

@bot.tree.command(name="epicdeals", description="Busca ofertas de Epic Games Store manualmente")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def epicdeals(interaction: discord.Interaction):
    await interaction.response.send_message(get_text("searching_epic", interaction.locale))
    
    stats = await checker.check_epic_and_notify(bot)
    
    await interaction.followup.send(
        get_text("search_complete", interaction.locale, targets=stats['targets_checked'], deals=stats['total_deals_sent'])
    )

@bot.tree.command(name="epicfree", description="Muestra los juegos gratis actuales y futuros de Epic Games Store")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def epicfree(interaction: discord.Interaction):
    await interaction.response.send_message(get_text("searching_free", interaction.locale))
    
    target_id, _ = get_target_id(interaction)
    country = await database.get_country(target_id)
    language = await database.get_language(target_id)
    
    free_games = await epic.get_free_games(country, language)
    
    embed = make_epic_free_embed(free_games["current"], free_games["upcoming"], locale=interaction.locale)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="compare", description="Compara precios e historial de un juego entre Steam y Epic Games")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(game="Nombre del juego")
@app_commands.autocomplete(game=game_autocomplete)
async def compare(interaction: discord.Interaction, game: str):
    await interaction.response.defer()
    
    target_id, _ = get_target_id(interaction)
    country = await database.get_country(target_id)
    language = await database.get_language(target_id)
    
    # 1. Steam Lookup
    steam_result = await steam.search_game(game, country, language)
    steam_data = None
    steam_history = []
    
    if steam_result:
        steam_data = await steam.get_game_price(steam_result["app_id"], country)
        if steam_data:
            steam_data["url"] = steam.get_store_url(steam_result["app_id"])
            steam_history = await database.get_price_history(steam_result["app_id"], steam_data["currency"], limit=10, store="steam")
            
    # 2. Epic Lookup
    epic_result = await epic.search_game(game, language)
    epic_data = None
    epic_history = []
    
    if epic_result:
        epic_data = await epic.get_game_price(epic_result["slug"], country, language)
        if epic_data:
            epic_data["url"] = epic.get_store_url(epic_result["slug"])
            epic_history = await database.get_price_history(epic_result["slug"], epic_data["currency"], limit=10, store="epic")
            
    # Check if not found on both
    if not steam_data and not epic_data:
        await interaction.followup.send(get_text("no_game_anywhere", interaction.locale))
        return
        
    embed = make_comparison_embed(
        game_name=game,
        steam=steam_data,
        epic=epic_data,
        steam_history=steam_history,
        epic_history=epic_history,
        locale=interaction.locale
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="history", description="Muestra el historial de precios registrado para un juego")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(game="Nombre del juego")
@app_commands.autocomplete(game=game_autocomplete)
async def history(interaction: discord.Interaction, game: str):
    await interaction.response.defer()
    
    target_id, _ = get_target_id(interaction)
    country = await database.get_country(target_id)
    language = await database.get_language(target_id)
    
    # 1. Search Steam
    search_result = await steam.search_game(game, country, language)
    
    if search_result:
        app_id = search_result["app_id"]
        current_price = await steam.get_game_price(app_id, country)
        currency = current_price.get("currency", "USD") if current_price else "USD"
        
        price_history = await database.get_price_history(app_id, currency, limit=10, store="steam")
        embed = make_history_embed(search_result["name"], price_history, currency, locale=interaction.locale)
        await interaction.followup.send(embed=embed)
    else:
        # Fallback to Epic Games Store
        epic_result = await epic.search_game(game, language)
        if epic_result:
            slug = epic_result["slug"]
            current_price = await epic.get_game_price(slug, country, language)
            currency = current_price.get("currency", "USD") if current_price else "USD"
            
            price_history = await database.get_price_history(slug, currency, limit=10, store="epic")
            embed = make_history_embed(epic_result["title"], price_history, currency, locale=interaction.locale)
            embed.title = f"📈 {get_text('history_title', interaction.locale, game_name=epic_result['title'])} (Epic Games)"
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(get_text("game_not_found", interaction.locale))

def run():
    if not TOKEN:
        print("Error: DISCORD_TOKEN is missing")
        return
    bot.run(TOKEN)

if __name__ == "__main__":
    run()
