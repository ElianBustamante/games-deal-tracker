import discord
from discord import app_commands

COMMAND_TRANSLATIONS = {
    "setsteamchannel": {
        discord.Locale.spain_spanish: "fijarcanalsteam",
        discord.Locale.latin_american_spanish: "fijarcanalsteam",
    },
    "setdiscount": {
        discord.Locale.spain_spanish: "fijardescuento",
        discord.Locale.latin_american_spanish: "fijardescuento",
    },
    "steamdeals": {
        discord.Locale.spain_spanish: "ofertassteam",
        discord.Locale.latin_american_spanish: "ofertassteam",
    },
    "history": {
        discord.Locale.spain_spanish: "historial",
        discord.Locale.latin_american_spanish: "historial",
    },
    "watchlist": {
        discord.Locale.spain_spanish: "deseados",
        discord.Locale.latin_american_spanish: "deseados",
    },
    "add": {
        discord.Locale.spain_spanish: "agregar",
        discord.Locale.latin_american_spanish: "agregar",
    },
    "remove": {
        discord.Locale.spain_spanish: "eliminar",
        discord.Locale.latin_american_spanish: "eliminar",
    },
    "show": {
        discord.Locale.spain_spanish: "mostrar",
        discord.Locale.latin_american_spanish: "mostrar",
    },
    "setlanguage": {
        discord.Locale.spain_spanish: "fijaridioma",
        discord.Locale.latin_american_spanish: "fijaridioma",
    },
    "setcountry": {
        discord.Locale.spain_spanish: "fijarpais",
        discord.Locale.latin_american_spanish: "fijarpais",
    },
    "stop": {
        discord.Locale.spain_spanish: "detener",
        discord.Locale.latin_american_spanish: "detener",
    },
    "setepicchannel": {
        discord.Locale.spain_spanish: "fijarcanalepic",
        discord.Locale.latin_american_spanish: "fijarcanalepic",
    },
    "epicdeals": {
        discord.Locale.spain_spanish: "ofertasepic",
        discord.Locale.latin_american_spanish: "ofertasepic",
    },
    "epicfree": {
        discord.Locale.spain_spanish: "epicfree",
        discord.Locale.latin_american_spanish: "epicfree",
    },
    "compare": {
        discord.Locale.spain_spanish: "comparar",
        discord.Locale.latin_american_spanish: "comparar",
    }
}

DESCRIPTION_TRANSLATIONS = {
    "Gestiona la lista de deseados": {
        discord.Locale.american_english: "Manage the watchlist",
        discord.Locale.british_english: "Manage the watchlist",
    },
    "Añade un juego a la lista de seguimiento": {
        discord.Locale.american_english: "Add a game to the watchlist",
        discord.Locale.british_english: "Add a game to the watchlist",
    },
    "Elimina un juego de la lista de seguimiento": {
        discord.Locale.american_english: "Remove a game from the watchlist",
        discord.Locale.british_english: "Remove a game from the watchlist",
    },
    "Muestra todos los juegos monitoreados": {
        discord.Locale.american_english: "Show all monitored games",
        discord.Locale.british_english: "Show all monitored games",
    },
    "Configura el canal donde se enviarán las alertas de Steam": {
        discord.Locale.american_english: "Set the channel where Steam alerts will be sent",
        discord.Locale.british_english: "Set the channel where Steam alerts will be sent",
    },
    "Configura el descuento mínimo % para alertas generales": {
        discord.Locale.american_english: "Set the minimum % discount for general alerts",
        discord.Locale.british_english: "Set the minimum % discount for general alerts",
    },
    "Configura el idioma para las alertas automáticas": {
        discord.Locale.american_english: "Set the language for automatic alerts",
        discord.Locale.british_english: "Set the language for automatic alerts",
    },
    "Configura el país para obtener precios locales de Steam": {
        discord.Locale.american_english: "Set the country to get local Steam prices",
        discord.Locale.british_english: "Set the country to get local Steam prices",
    },
    "Detiene las notificaciones y borra tus datos": {
        discord.Locale.american_english: "Stop notifications and delete your data",
        discord.Locale.british_english: "Stop notifications and delete your data",
    },
    "Busca ofertas de Steam manualmente en este momento": {
        discord.Locale.american_english: "Search for Steam deals manually right now",
        discord.Locale.british_english: "Search for Steam deals manually right now",
    },
    "Muestra el historial de precios registrado para un juego": {
        discord.Locale.american_english: "Show the recorded price history for a game",
        discord.Locale.british_english: "Show the recorded price history for a game",
    },
    "Configura el canal donde se enviarán las alertas de Epic Games": {
        discord.Locale.american_english: "Set the channel where Epic Games alerts will be sent",
        discord.Locale.british_english: "Set the channel where Epic Games alerts will be sent",
    },
    "Busca ofertas de Epic Games Store manualmente": {
        discord.Locale.american_english: "Search for Epic Games Store deals manually",
        discord.Locale.british_english: "Search for Epic Games Store deals manually",
    },
    "Muestra los juegos gratis actuales y futuros de Epic Games Store": {
        discord.Locale.american_english: "Show the current and upcoming free games from Epic Games Store",
        discord.Locale.british_english: "Show the current and upcoming free games from Epic Games Store",
    },
    "Compara precios e historial de un juego entre Steam y Epic Games": {
        discord.Locale.american_english: "Compare prices and history of a game between Steam and Epic Games",
        discord.Locale.british_english: "Compare prices and history of a game between Steam and Epic Games",
    }
}

PARAMETER_TRANSLATIONS = {
    "El canal para las alertas de Steam": {
        discord.Locale.american_english: "The channel for Steam alerts",
        discord.Locale.british_english: "The channel for Steam alerts",
    },
    "Porcentaje (1-100)": {
        discord.Locale.american_english: "Percentage (1-100)",
        discord.Locale.british_english: "Percentage (1-100)",
    },
    "Idioma (en o es)": {
        discord.Locale.american_english: "Language (en or es)",
        discord.Locale.british_english: "Language (en or es)",
    },
    "Nombre del país": {
        discord.Locale.american_english: "Name of the country",
        discord.Locale.british_english: "Name of the country",
    },
    "Nombre del juego": {
        discord.Locale.american_english: "Game name",
        discord.Locale.british_english: "Game name",
    },
    "El canal para las alertas de Epic": {
        discord.Locale.american_english: "The channel for Epic alerts",
        discord.Locale.british_english: "The channel for Epic alerts",
    }
}

class BotTranslator(app_commands.Translator):
    async def translate(self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext) -> str | None:
        if context.location == app_commands.TranslationContextLocation.command_name:
            if string.message in COMMAND_TRANSLATIONS:
                return COMMAND_TRANSLATIONS[string.message].get(locale)
        elif context.location == app_commands.TranslationContextLocation.command_description:
            if string.message in DESCRIPTION_TRANSLATIONS:
                return DESCRIPTION_TRANSLATIONS[string.message].get(locale)
        elif context.location == app_commands.TranslationContextLocation.parameter_description:
            if string.message in PARAMETER_TRANSLATIONS:
                return PARAMETER_TRANSLATIONS[string.message].get(locale)
        return None

UI_TEXT = {
    "es": {
        "price": "Precio",
        "discount": "Descuento",
        "history": "Historial",
        "no_history": "📊 Primer registro — sin historial previo",
        "historical_low_alert": "🏆 ¡Precio mínimo histórico registrado!",
        "historical_low": "⚠️ Mínimo registrado: {price} ({days} días atrás)",
        "historical_low_no_date": "⚠️ Mínimo registrado: {price}",
        "history_title": "📈 Historial de precios — {game_name}",
        "no_records": "Sin registros",
        "no_records_yet": "Sin historial registrado aún",
        "unknown_game": "Juego Desconocido",
        "game_not_found": "No encontré ese juego en Steam.",
        "already_in_list": "Este juego ya está en la lista.",
        "added_to_list": "✅ Se añadió **{name}** a la lista.",
        "removed_from_list": "✅ Se eliminó **{name}** de la lista.",
        "not_in_list": "No encontré ese juego en tu lista.",
        "list_empty": "La lista está vacía.",
        "watchlist_title": "🎮 Lista de deseados",
        "status": "Estado",
        "status_discount": "-{discount}% descuento",
        "status_no_discount": "Sin descuento",
        "added": "Añadido",
        "alerts_channel_set": "✅ Las alertas de Steam se enviarán a {mention}",
        "invalid_percent": "El porcentaje debe estar entre 1 y 100.",
        "discount_set": "✅ Alertas generales configuradas a mínimo **{percent}%** de descuento.",
        "language_set": "✅ Idioma configurado a **Español**.",
        "searching": "🔍 Buscando ofertas ahora...",
        "search_complete": "✅ Búsqueda completada. Se verificaron {targets} destinos y se enviaron {deals} alertas en total.",
        "no_permissions": "❌ No tienes permisos para usar esto aquí.",
        "country_set": "✅ Región configurada correctamente a: **{country}**",
        "alerts_stopped": "⏹️ Notificaciones pausadas y datos eliminados de la base de datos.",
        "unexpected_error": "❌ Ocurrió un error inesperado al procesar este comando.",
        "epic_deals_title": "🟣 Ofertas Epic Games",
        "epic_free_title": "🎁 Juegos Gratis — Epic Games",
        "available_now": "🎮 Disponibles ahora",
        "coming_soon": "🔜 Próximamente",
        "ends_on": "Disponible hasta: {date}",
        "starts_on": "Disponible el: {date}",
        "free_games_footer": "Los juegos gratis de Epic rotan los jueves",
        "comparison_title": "⚖️ Comparación de precios — {game_name}",
        "not_available": "❌ No disponible",
        "best_price_steam": "💚 Mejor precio ahora: Steam",
        "best_price_epic": "🟣 Mejor precio ahora: Epic",
        "best_price_equal": "🟰 Mismo precio en ambas tiendas",
        "lowest_hist_steam": "📉 Mínimo histórico más bajo registrado: Steam",
        "lowest_hist_epic": "📉 Mínimo histórico más bajo registrado: Epic",
        "lowest_hist_equal": "📉 Mismo mínimo histórico registrado en ambas",
        "epic_store": "Epic Games Store",
        "no_epic_game": "No encontré ese juego en Epic Games.",
        "no_game_anywhere": "El juego no fue encontrado en ninguna tienda.",
        "epic_channel_set": "✅ Alertas de Epic se enviarán a {mention}",
        "epic_channel_fallback": "ℹ️ Sin canal Epic configurado — se usará el canal de Steam",
        "searching_epic": "🔍 Buscando ofertas en Epic Games...",
        "searching_free": "🔍 Buscando juegos gratis en Epic Games...",
        "view_deal": "Ver Oferta",
        "add_to_watchlist": "Añadir a Deseados",
        "watchlist_added": "✅ Se añadió **{name}** a la lista de deseados.",
        "admin_only": "❌ Solo los administradores del servidor pueden añadir juegos a la lista de deseados.",
        "original_price": "Precio Original",
        "final_price": "Precio Final",
        "valid_until": "válido hasta {date}"
    },
    "en": {
        "price": "Price",
        "discount": "Discount",
        "history": "History",
        "no_history": "📊 First record — no previous history",
        "historical_low_alert": "🏆 All-time low price recorded!",
        "historical_low": "⚠️ Lowest recorded: {price} ({days} days ago)",
        "historical_low_no_date": "⚠️ Lowest recorded: {price}",
        "history_title": "📈 Price History — {game_name}",
        "no_records": "No records",
        "no_records_yet": "No history recorded yet",
        "unknown_game": "Unknown Game",
        "game_not_found": "I couldn't find that game on Steam.",
        "already_in_list": "This game is already on the list.",
        "added_to_list": "✅ Added **{name}** to the list.",
        "removed_from_list": "✅ Removed **{name}** from the list.",
        "not_in_list": "I couldn't find that game on your list.",
        "list_empty": "The list is empty.",
        "watchlist_title": "🎮 Watchlist",
        "status": "Status",
        "status_discount": "{discount}% off",
        "status_no_discount": "No discount",
        "added": "Added",
        "alerts_channel_set": "✅ Steam alerts will be sent to {mention}",
        "invalid_percent": "The percentage must be between 1 and 100.",
        "discount_set": "✅ General alerts configured for a minimum of **{percent}%** off.",
        "language_set": "✅ Language set to **English**.",
        "searching": "🔍 Searching for deals now...",
        "search_complete": "✅ Search complete. Checked {targets} targets and sent {deals} alerts in total.",
        "no_permissions": "❌ You don't have permissions to use this here.",
        "country_set": "✅ Region correctly configured to: **{country}**",
        "alerts_stopped": "⏹️ Notifications stopped and your data has been deleted.",
        "unexpected_error": "❌ An unexpected error occurred while processing this command.",
        "epic_deals_title": "🟣 Epic Games Deals",
        "epic_free_title": "🎁 Free Games — Epic Games",
        "available_now": "🎮 Available now",
        "coming_soon": "🔜 Coming soon",
        "ends_on": "Available until: {date}",
        "starts_on": "Available on: {date}",
        "free_games_footer": "Epic free games rotate on Thursdays",
        "comparison_title": "⚖️ Price Comparison — {game_name}",
        "not_available": "❌ Not available",
        "best_price_steam": "💚 Best price now: Steam",
        "best_price_epic": "🟣 Best price now: Epic",
        "best_price_equal": "🟰 Same price in both stores",
        "lowest_hist_steam": "📉 Lowest historical low recorded: Steam",
        "lowest_hist_epic": "📉 Lowest historical low recorded: Epic",
        "lowest_hist_equal": "📉 Same historical low recorded in both",
        "epic_store": "Epic Games Store",
        "no_epic_game": "I couldn't find that game on Epic Games.",
        "no_game_anywhere": "The game was not found on any store.",
        "epic_channel_set": "✅ Epic alerts will be sent to {mention}",
        "epic_channel_fallback": "ℹ️ No Epic channel configured — Steam channel will be used",
        "searching_epic": "🔍 Searching for Epic Games deals...",
        "searching_free": "🔍 Searching for Epic Games free games...",
        "view_deal": "View Deal",
        "add_to_watchlist": "Add to Watchlist",
        "watchlist_added": "✅ Added **{name}** to the watchlist.",
        "admin_only": "❌ Only server administrators can add games to the watchlist.",
        "original_price": "Original Price",
        "final_price": "Final Price",
        "valid_until": "valid until {date}"
    }
}

def get_text(key: str, locale: str | discord.Locale, **kwargs) -> str:
    lang = "en" if str(locale).startswith("en") else "es"
    text = UI_TEXT.get(lang, UI_TEXT["es"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
