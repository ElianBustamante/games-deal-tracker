import os
import logging
import asyncio
import aiohttp
from dotenv import load_dotenv
from cachetools import TTLCache

load_dotenv()

logger = logging.getLogger("steam_deals_bot")

STEAM_COUNTRY = os.getenv("STEAM_COUNTRY", "cl")
STEAM_LANGUAGE = os.getenv("STEAM_LANGUAGE", "es")

async def _fetch_url(url: str, timeout_secs: int = 10, max_attempts: int = 3, delay: float = 1.0) -> any:
    for attempt in range(1, max_attempts + 1):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_secs)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status in [429, 500, 502, 503, 504]:
                        logger.warning(
                            f"Steam API returned transient HTTP status {response.status} for URL: {url}. "
                            f"Attempt {attempt} of {max_attempts}."
                        )
                        if attempt == max_attempts:
                            response.raise_for_status()
                    else:
                        response.raise_for_status()
        except Exception as e:
            logger.warning(
                f"Network exception calling Steam API: {e} for URL: {url}. "
                f"Attempt {attempt} of {max_attempts}."
            )
            if attempt == max_attempts:
                logger.error(f"Failed all {max_attempts} attempts to fetch: {url}. Error: {e}", exc_info=True)
                raise
            await asyncio.sleep(delay * attempt)
    return None

async def search_game(name: str, country: str = STEAM_COUNTRY, language: str = STEAM_LANGUAGE) -> dict | None:
    cleaned_name = name.replace("®", "").replace("™", "").strip()
    url = f"https://store.steampowered.com/api/storesearch/?term={cleaned_name}&l={language}&cc={country}"
    try:
        data = await _fetch_url(url)
        if data and data.get("items"):
            first_item = data["items"][0]
            return {"app_id": first_item.get("id"), "name": first_item.get("name")}
    except Exception:
        pass
    return None

# Cache for autocomplete searches. 2000 items, expires after 1 hour (3600 seconds)
autocomplete_cache = TTLCache(maxsize=2000, ttl=3600)

async def search_game_autocomplete(term: str, country: str = STEAM_COUNTRY, language: str = STEAM_LANGUAGE) -> list[dict]:
    term = term.strip().lower()
    if len(term) < 3:
        return []
        
    cache_key = f"{term}_{language}_{country}"
    if cache_key in autocomplete_cache:
        return autocomplete_cache[cache_key]
        
    url = f"https://store.steampowered.com/api/storesearch/?term={term}&l={language}&cc={country}"
    results = []
    try:
        data = await _fetch_url(url, timeout_secs=5)
        if data and data.get("items"):
            # Discord allows max 25 choices
            for item in data["items"][:25]:
                results.append({"app_id": item.get("id"), "name": item.get("name")})
            autocomplete_cache[cache_key] = results
    except Exception:
        pass
    return results

# Steam content descriptor ID 3 = Adult Only Sexual Content (explicit/pornographic)
_ADULT_DESCRIPTOR_IDS = {3}

async def get_game_price(app_id: int, country: str = STEAM_COUNTRY) -> dict | None:
    # Filters include content_descriptors to detect adult sexual content
    url = (
        f"https://store.steampowered.com/api/appdetails"
        f"?appids={app_id}&cc={country}&filters=basic,price_overview,content_descriptors"
    )
    try:
        data = await _fetch_url(url)
        app_str = str(app_id)
        if data and data.get(app_str) and data[app_str].get("success"):
            app_data = data[app_str].get("data", {})
            # Skip games with nudity/sexual content descriptors
            descriptor_ids = set(
                app_data.get("content_descriptors", {}).get("ids", [])
            )
            if descriptor_ids & _ADULT_DESCRIPTOR_IDS:
                return None
            if "price_overview" in app_data:
                po = app_data["price_overview"]
                return {
                    "app_id": app_id,
                    "name": app_data.get("name", "Unknown Game"),
                    "price_original": po.get("initial"),
                    "price_final": po.get("final"),
                    "discount_percent": po.get("discount_percent"),
                    "currency": po.get("currency")
                }
    except Exception:
        pass
    return None

async def get_featured_deals(country: str = STEAM_COUNTRY, language: str = STEAM_LANGUAGE) -> list[dict]:
    url = f"https://store.steampowered.com/api/featuredcategories?cc={country}&l={language}"
    try:
        data = await _fetch_url(url)
        if data:
            deals = []
            seen_apps = set()
            for category_name, category_data in data.items():
                if isinstance(category_data, dict) and "items" in category_data:
                    for item in category_data["items"]:
                        app_id = item.get("id")
                        # Skip adult-only content (type 13 = adults only on Steam)
                        if item.get("type") == 13:
                            continue
                        if app_id not in seen_apps and item.get("discounted"):
                            seen_apps.add(app_id)
                            deals.append({
                                "app_id": app_id,
                                "name": item.get("name"),
                                "price_original": item.get("original_price"),
                                "price_final": item.get("final_price"),
                                "discount_percent": item.get("discount_percent", 0),
                                "currency": item.get("currency", "USD")
                            })
            return deals
    except Exception:
        pass
    return []

def get_store_url(app_id: int) -> str:
    return f"https://store.steampowered.com/app/{app_id}/"

def get_header_image_url(app_id: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"
