import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

import app.steam as steam
import app.database as database
import app.checker as checker
from app.formatter import make_history_embed
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
    "European Union": "es", # or fr, de
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

watchlist_group = app_commands.Group(name="watchlist", description="Gestiona la lista de deseados")

@watchlist_group.command(name="add", description="Añade un juego a la lista de seguimiento del servidor")
@app_commands.describe(game="Nombre del juego")
async def watchlist_add(interaction: discord.Interaction, game: str):
    await interaction.response.defer(ephemeral=True)
    
    target_id, is_dm = get_target_id(interaction)
    await ensure_dm_setup(target_id, is_dm)
    
    search_result = await steam.search_game(game)
    
    if not search_result:
        await interaction.followup.send(get_text("game_not_found", interaction.locale), ephemeral=True)
        return
        
    added = await database.add_to_watchlist(target_id, search_result["app_id"], search_result["name"])
    if added:
        await interaction.followup.send(get_text("added_to_list", interaction.locale, name=search_result["name"]), ephemeral=True)
    else:
        await interaction.followup.send(get_text("already_in_list", interaction.locale), ephemeral=True)

@watchlist_group.command(name="remove", description="Elimina un juego de la lista de seguimiento")
@app_commands.describe(game="Nombre del juego")
async def watchlist_remove(interaction: discord.Interaction, game: str):
    await interaction.response.defer(ephemeral=True)
    
    target_id, _ = get_target_id(interaction)
    search_result = await steam.search_game(game)
    
    if not search_result:
        await interaction.followup.send(get_text("game_not_found", interaction.locale), ephemeral=True)
        return
        
    removed = await database.remove_from_watchlist(target_id, search_result["app_id"])
    if removed:
        await interaction.followup.send(get_text("removed_from_list", interaction.locale, name=search_result["name"]), ephemeral=True)
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
        price = await steam.get_game_price(game["app_id"])
        if price and price.get("discount_percent", 0) > 0:
            status = get_text("status_discount", interaction.locale, discount=price['discount_percent'])
        else:
            status = get_text("status_no_discount", interaction.locale)
            
        embed.add_field(
            name=game["game_name"], 
            value=f"{get_text('status', interaction.locale)}: {status}\n{get_text('added', interaction.locale)}: {game['added_at'][:10]}",
            inline=False
        )
        
    await interaction.followup.send(embed=embed)

bot.tree.add_command(watchlist_group)

@bot.tree.command(name="setchannel", description="Configura el canal donde se enviarán las alertas")
@app_commands.guild_only()
@app_commands.describe(channel="El canal para las alertas")
@app_commands.checks.has_permissions(manage_channels=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    target_id, is_dm = get_target_id(interaction)
    await database.set_channel(target_id, str(channel.id), is_dm=False)
    await interaction.response.send_message(get_text("alerts_channel_set", interaction.locale, mention=channel.mention), ephemeral=True)

@bot.tree.command(name="setdiscount", description="Configura el descuento mínimo % para alertas generales")
@app_commands.describe(porcentaje="Porcentaje (1-100)")
async def setdiscount(interaction: discord.Interaction, porcentaje: int):
    target_id, is_dm = get_target_id(interaction)
    
    if not is_dm and not interaction.permissions.manage_channels:
        await interaction.response.send_message(get_text("no_permissions", interaction.locale), ephemeral=True)
        return
        
    if porcentaje < 1 or porcentaje > 100:
        await interaction.response.send_message(get_text("invalid_percent", interaction.locale), ephemeral=True)
        return
        
    await ensure_dm_setup(target_id, is_dm)
    await database.set_min_discount(target_id, porcentaje)
    await interaction.response.send_message(get_text("discount_set", interaction.locale, percent=porcentaje), ephemeral=True)

@bot.tree.command(name="setlanguage", description="Configura el idioma para las alertas automáticas")
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
    # Give confirmation in the language they just selected
    await interaction.response.send_message(get_text("language_set", lang), ephemeral=True)

@bot.tree.command(name="setcountry", description="Configura el país para obtener precios locales de Steam")
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
async def stop_alerts(interaction: discord.Interaction):
    target_id, is_dm = get_target_id(interaction)
    if not is_dm and not interaction.permissions.manage_channels:
        await interaction.response.send_message(get_text("no_permissions", interaction.locale), ephemeral=True)
        return
        
    await database.stop_notifications(target_id)
    await interaction.response.send_message(get_text("alerts_stopped", interaction.locale), ephemeral=True)

@bot.tree.command(name="deals", description="Busca ofertas manualmente en este momento")
async def deals(interaction: discord.Interaction):
    await interaction.response.send_message(get_text("searching", interaction.locale))
    
    stats = await checker.check_and_notify(bot)
    
    await interaction.followup.send(
        get_text("search_complete", interaction.locale, targets=stats['targets_checked'], deals=stats['total_deals_sent'])
    )

@bot.tree.command(name="history", description="Muestra el historial de precios registrado para un juego")
@app_commands.describe(game="Nombre del juego")
async def history(interaction: discord.Interaction, game: str):
    await interaction.response.defer()
    
    target_id, _ = get_target_id(interaction)
    country = await database.get_country(target_id)
    language = await database.get_language(target_id)
    
    search_result = await steam.search_game(game, country, language)
    if not search_result:
        await interaction.followup.send(get_text("game_not_found", interaction.locale))
        return
        
    app_id = search_result["app_id"]
    
    # We fetch the current price just to know what currency this country uses
    current_price = await steam.get_game_price(app_id, country)
    currency = current_price.get("currency", "USD") if current_price else "USD"
    
    price_history = await database.get_price_history(app_id, currency, limit=10)
    
    embed = make_history_embed(search_result["name"], price_history, currency, locale=interaction.locale)
    await interaction.followup.send(embed=embed)

def run():
    if not TOKEN:
        print("Error: DISCORD_TOKEN is missing")
        return
    bot.run(TOKEN)

if __name__ == "__main__":
    run()
