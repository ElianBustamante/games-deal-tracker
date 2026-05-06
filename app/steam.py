import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

STEAM_COUNTRY = os.getenv("STEAM_COUNTRY", "cl")
STEAM_LANGUAGE = os.getenv("STEAM_LANGUAGE", "es")

async def search_game(name: str) -> dict | None:
    url = f"https://store.steampowered.com/api/storesearch/?term={name}&l={STEAM_LANGUAGE}&cc={STEAM_COUNTRY}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and data.get("items"):
                        first_item = data["items"][0]
                        return {"app_id": first_item.get("id"), "name": first_item.get("name")}
    except Exception:
        pass
    return None

async def get_game_price(app_id: int) -> dict | None:
    # Using filters=basic,price_overview to ensure we get the game name along with price
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc={STEAM_COUNTRY}&filters=basic,price_overview"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    app_str = str(app_id)
                    if data and data.get(app_str) and data[app_str].get("success"):
                        app_data = data[app_str].get("data", {})
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

async def get_featured_deals() -> list[dict]:
    url = f"https://store.steampowered.com/api/featuredcategories?cc={STEAM_COUNTRY}&l={STEAM_LANGUAGE}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        deals = []
                        seen_apps = set()
                        for category_name, category_data in data.items():
                            if isinstance(category_data, dict) and "items" in category_data:
                                for item in category_data["items"]:
                                    app_id = item.get("id")
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
