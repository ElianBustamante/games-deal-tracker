import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

import app.steam as steam
import app.database as database
import app.checker as checker
from app.formatter import make_history_embed

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

class SteamDealsBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=discord.Intents.default()
        )

    async def setup_hook(self):
        await database.init_db()
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guilds")

bot = SteamDealsBot()

watchlist_group = app_commands.Group(name="watchlist", description="Gestiona la lista de deseados")

@watchlist_group.command(name="add", description="Añade un juego a la lista de seguimiento del servidor")
@app_commands.describe(game="Nombre del juego")
async def watchlist_add(interaction: discord.Interaction, game: str):
    await interaction.response.defer(ephemeral=True)
    
    server_id = str(interaction.guild_id)
    search_result = await steam.search_game(game)
    
    if not search_result:
        await interaction.followup.send("No encontré ese juego en Steam.", ephemeral=True)
        return
        
    added = await database.add_to_watchlist(server_id, search_result["app_id"], search_result["name"])
    if added:
        await interaction.followup.send(f"✅ Se añadió **{search_result['name']}** a la lista.", ephemeral=True)
    else:
        await interaction.followup.send("Este juego ya está en la lista.", ephemeral=True)

@watchlist_group.command(name="remove", description="Elimina un juego de la lista de seguimiento")
@app_commands.describe(game="Nombre del juego")
async def watchlist_remove(interaction: discord.Interaction, game: str):
    await interaction.response.defer(ephemeral=True)
    
    server_id = str(interaction.guild_id)
    search_result = await steam.search_game(game)
    
    if not search_result:
        await interaction.followup.send("No encontré ese juego en Steam.", ephemeral=True)
        return
        
    removed = await database.remove_from_watchlist(server_id, search_result["app_id"])
    if removed:
        await interaction.followup.send(f"✅ Se eliminó **{search_result['name']}** de la lista.", ephemeral=True)
    else:
        await interaction.followup.send("No encontré ese juego en tu lista.", ephemeral=True)

@watchlist_group.command(name="show", description="Muestra todos los juegos monitoreados")
async def watchlist_show(interaction: discord.Interaction):
    await interaction.response.defer()
    
    server_id = str(interaction.guild_id)
    watchlist = await database.get_watchlist(server_id)
    
    if not watchlist:
        await interaction.followup.send("La lista está vacía.")
        return
        
    embed = discord.Embed(title="🎮 Lista de deseados del servidor", color=discord.Color.blue())
    
    for game in watchlist:
        price = await steam.get_game_price(game["app_id"])
        if price and price.get("discount_percent", 0) > 0:
            status = f"-{price['discount_percent']}% descuento"
        else:
            status = "Sin descuento"
            
        embed.add_field(
            name=game["game_name"], 
            value=f"Estado: {status}\nAñadido: {game['added_at'][:10]}",
            inline=False
        )
        
    await interaction.followup.send(embed=embed)

bot.tree.add_command(watchlist_group)

@bot.tree.command(name="setchannel", description="Configura el canal donde se enviarán las alertas")
@app_commands.describe(channel="El canal para las alertas")
@app_commands.checks.has_permissions(manage_channels=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    server_id = str(interaction.guild_id)
    await database.set_channel(server_id, str(channel.id))
    await interaction.response.send_message(f"✅ Las alertas se enviarán a {channel.mention}", ephemeral=True)

@bot.tree.command(name="setdiscount", description="Configura el descuento mínimo % para alertas generales")
@app_commands.describe(porcentaje="Porcentaje (1-100)")
@app_commands.checks.has_permissions(manage_channels=True)
async def setdiscount(interaction: discord.Interaction, porcentaje: int):
    if porcentaje < 1 or porcentaje > 100:
        await interaction.response.send_message("El porcentaje debe estar entre 1 y 100.", ephemeral=True)
        return
        
    server_id = str(interaction.guild_id)
    await database.set_min_discount(server_id, porcentaje)
    await interaction.response.send_message(f"✅ Alertas generales configuradas a mínimo **{porcentaje}%** de descuento.", ephemeral=True)

@bot.tree.command(name="deals", description="Busca ofertas manualmente en este momento")
async def deals(interaction: discord.Interaction):
    await interaction.response.send_message("🔍 Buscando ofertas ahora...")
    
    stats = await checker.check_and_notify(bot)
    
    await interaction.followup.send(
        f"✅ Búsqueda completada. Se verificaron {stats['servers_checked']} servidores y se enviaron {stats['total_deals_sent']} alertas en total."
    )

@bot.tree.command(name="historial", description="Muestra el historial de precios registrado para un juego")
@app_commands.describe(game="Nombre del juego")
async def historial(interaction: discord.Interaction, game: str):
    await interaction.response.defer()
    
    search_result = await steam.search_game(game)
    if not search_result:
        await interaction.followup.send("No encontré ese juego en Steam.")
        return
        
    app_id = search_result["app_id"]
    history = await database.get_price_history(app_id, limit=10)
    
    embed = make_history_embed(app_id, search_result["name"], history, "CLP") # Using CLP as default for formatting fallback
    await interaction.followup.send(embed=embed)

def run():
    if not TOKEN:
        print("Error: DISCORD_TOKEN is missing")
        return
    bot.run(TOKEN)

if __name__ == "__main__":
    run()
