import os
import aiohttp
from curl_cffi.requests import AsyncSession
from dotenv import load_dotenv

load_dotenv()


STEAM_COUNTRY = os.getenv("STEAM_COUNTRY", "cl")
STEAM_LANGUAGE = os.getenv("STEAM_LANGUAGE", "es")

def get_epic_locale(lang: str) -> str:
    # Map to Epic supported locale, defaulting to es-MX for Spanish as requested
    return "es-MX" if lang.lower() == "es" else "en-US"

def get_store_url(slug: str) -> str:
    return f"https://store.epicgames.com/p/{slug}"

def normalize_epic_price(price_val: int, currency: str) -> int:
    """
    Normalizes Epic Games prices to cents format (matching Steam's convention).
    Epic returns zero-subunit currencies (CLP, JPY, KRW) in their base unit (e.g. 9990).
    Steam always returns them multiplied by 100 (999000).
    So we multiply Epic zero-subunit currencies by 100.
    """
    if not price_val:
        return 0
    curr_upper = currency.upper()
    if curr_upper in ["CLP", "JPY", "KRW", "VND", "HUF", "TWD"]:
        return price_val * 100
    return price_val

async def get_free_games(country: str = STEAM_COUNTRY, language: str = STEAM_LANGUAGE) -> dict:
    locale = get_epic_locale(language)
    country_upper = country.upper()
    
    url = f"https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale={locale}&country={country_upper}&allowCountries={country_upper}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    result = {"current": [], "upcoming": []}
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
                    
                    for el in elements:
                        title = el.get("title")
                        
                        # Find slug
                        slug = el.get("urlSlug") or el.get("productSlug")
                        if not slug and el.get("catalogNs", {}).get("mappings"):
                            slug = el["catalogNs"]["mappings"][0].get("pageSlug")
                        
                        if not slug or not title:
                            continue
                            
                        # Find thumbnail
                        thumbnail = None
                        key_images = el.get("keyImages", [])
                        # Prefer OfferImageWide or Thumbnail
                        for img in key_images:
                            if img.get("type") in ["OfferImageWide", "Thumbnail"]:
                                thumbnail = img.get("url")
                                break
                        if not thumbnail and key_images:
                            thumbnail = key_images[0].get("url")
                            
                        promotions = el.get("promotions")
                        if not promotions:
                            continue
                            
                        # Current offers
                        promo_offers = promotions.get("promotionalOffers", [])
                        current_active = []
                        for offer_group in promo_offers:
                            for offer in offer_group.get("promotionalOffers", []):
                                discount = offer.get("discountSetting", {}).get("discountPercentage", -1)
                                if discount == 0:
                                    current_active.append(offer)
                                    
                        # Upcoming offers
                        upcoming_promo = promotions.get("upcomingPromotionalOffers", [])
                        upcoming_active = []
                        for offer_group in upcoming_promo:
                            for offer in offer_group.get("promotionalOffers", []):
                                discount = offer.get("discountSetting", {}).get("discountPercentage", -1)
                                if discount == 0:
                                    upcoming_active.append(offer)
                                    
                        if current_active:
                            end_date = current_active[0].get("endDate")
                            result["current"].append({
                                "title": title,
                                "slug": slug,
                                "end_date": end_date,
                                "thumbnail": thumbnail
                            })
                        elif upcoming_active:
                            start_date = upcoming_active[0].get("startDate")
                            result["upcoming"].append({
                                "title": title,
                                "slug": slug,
                                "start_date": start_date,
                                "thumbnail": thumbnail
                            })
    except Exception:
        pass
        
    return result

async def get_deals(country: str = STEAM_COUNTRY, min_discount: int = 0, language: str = STEAM_LANGUAGE) -> list[dict]:
    locale = get_epic_locale(language)
    country_upper = country.upper()
    
    url = "https://store.epicgames.com/graphql"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://store.epicgames.com",
        "Referer": "https://store.epicgames.com/"
    }
    
    query = """
    {
      Catalog {
        searchStore(
          onSale: true
          country: "%s"
          locale: "%s"
          sortBy: "currentPrice"
          count: 40
          category: "games/edition/base"
        ) {
          elements {
            title
            id
            namespace
            productSlug
            urlSlug
            keyImages {
              type
              url
            }
            price(country: "%s") {
              totalPrice {
                originalPrice
                discountPrice
                discount
                currencyCode
              }
            }
            promotions {
              promotionalOffers {
                promotionalOffers {
                  endDate
                  discountSetting {
                    discountPercentage
                  }
                }
              }
            }
          }
        }
      }
    }
    """ % (country_upper, locale, country_upper)
    
    payload = {"query": query}
    deals = []
    
    try:
        async with AsyncSession(impersonate="chrome120") as session:
            response = await session.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []) or []
                
                for el in elements:
                    title = el.get("title")
                    slug = el.get("urlSlug") or el.get("productSlug")
                    if not slug or not title:
                        continue
                        
                    price_data = el.get("price", {}).get("totalPrice", {})
                    if not price_data:
                        continue
                        
                    original_price = price_data.get("originalPrice", 0)
                    final_price = price_data.get("discountPrice", 0)
                    discount_amt = price_data.get("discount", 0)
                    currency = price_data.get("currencyCode", "USD")
                    
                    # Calculate discount percent
                    discount_percent = 0
                    if original_price > 0:
                        discount_percent = round((discount_amt / original_price) * 100)
                        
                    if discount_percent < min_discount or discount_percent == 0:
                        continue
                        
                    # Find end date
                    end_date = None
                    promotions = el.get("promotions")
                    if promotions:
                        promo_offers = promotions.get("promotionalOffers", [])
                        for group in promo_offers:
                            for offer in group.get("promotionalOffers", []):
                                if offer.get("discountSetting", {}).get("discountPercentage") == discount_percent:
                                    end_date = offer.get("endDate")
                                    break
                            if end_date:
                                break
                                
                    thumbnail = None
                    key_images = el.get("keyImages", [])
                    for img in key_images:
                        if img.get("type") in ["OfferImageWide", "Thumbnail"]:
                            thumbnail = img.get("url")
                            break
                    if not thumbnail and key_images:
                        thumbnail = key_images[0].get("url")
                        
                    # Normalize prices to cents/Steam format
                    orig_normalized = normalize_epic_price(original_price, currency)
                    final_normalized = normalize_epic_price(final_price, currency)
                    
                    deals.append({
                        "title": title,
                        "slug": slug,
                        "original_price": orig_normalized,
                        "final_price": final_normalized,
                        "discount_percent": discount_percent,
                        "currency": currency,
                        "end_date": end_date,
                        "thumbnail": thumbnail
                    })
    except Exception:
        pass
        
    return deals


async def search_game(name: str, language: str = STEAM_LANGUAGE) -> dict | None:
    locale = get_epic_locale(language)
    url = "https://store.epicgames.com/graphql"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://store.epicgames.com",
        "Referer": "https://store.epicgames.com/"
    }
    
    # Escape quotes in game name search keyword
    escaped_name = name.replace('"', '\\"')
    
    query = """
    {
      Catalog {
        searchStore(
          keywords: "%s"
          count: 5
          category: "games/edition/base"
          locale: "%s"
        ) {
          elements {
            title
            id
            namespace
            productSlug
            urlSlug
          }
        }
      }
    }
    """ % (escaped_name, locale)
    
    payload = {"query": query}
    
    try:
        async with AsyncSession(impersonate="chrome120") as session:
            response = await session.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []) or []
                if elements:
                    first = elements[0]
                    slug = first.get("urlSlug") or first.get("productSlug")
                    if slug:
                        return {
                            "title": first.get("title"),
                            "slug": slug,
                            "epic_id": first.get("id"),
                            "namespace": first.get("namespace")
                        }
    except Exception:
        pass
        
    return None


async def get_game_price(slug: str, country: str = STEAM_COUNTRY, language: str = STEAM_LANGUAGE) -> dict | None:
    locale = get_epic_locale(language)
    country_upper = country.upper()
    
    url = "https://store.epicgames.com/graphql"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://store.epicgames.com",
        "Referer": "https://store.epicgames.com/"
    }
    
    # We query using keywords/search terms matching the slug
    query = """
    {
      Catalog {
        searchStore(
          keywords: "%s"
          count: 5
          category: "games/edition/base"
          country: "%s"
          locale: "%s"
        ) {
          elements {
            title
            id
            namespace
            productSlug
            urlSlug
            keyImages {
              type
              url
            }
            price(country: "%s") {
              totalPrice {
                originalPrice
                discountPrice
                discount
                currencyCode
              }
            }
            promotions {
              promotionalOffers {
                promotionalOffers {
                  endDate
                  discountSetting {
                    discountPercentage
                  }
                }
              }
            }
          }
        }
      }
    }
    """ % (slug, country_upper, locale, country_upper)
    
    payload = {"query": query}
    
    try:
        async with AsyncSession(impersonate="chrome120") as session:
            response = await session.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []) or []
                
                for el in elements:
                    el_slug = el.get("urlSlug") or el.get("productSlug")
                    if el_slug == slug:
                        price_data = el.get("price", {}).get("totalPrice", {})
                        if not price_data:
                            continue
                            
                        original_price = price_data.get("originalPrice", 0)
                        final_price = price_data.get("discountPrice", 0)
                        discount_amt = price_data.get("discount", 0)
                        currency = price_data.get("currencyCode", "USD")
                        
                        discount_percent = 0
                        if original_price > 0:
                            discount_percent = round((discount_amt / original_price) * 100)
                            
                        thumbnail = None
                        key_images = el.get("keyImages", [])
                        for img in key_images:
                            if img.get("type") in ["OfferImageWide", "Thumbnail"]:
                                thumbnail = img.get("url")
                                break
                        if not thumbnail and key_images:
                            thumbnail = key_images[0].get("url")
                            
                        orig_normalized = normalize_epic_price(original_price, currency)
                        final_normalized = normalize_epic_price(final_price, currency)
                        
                        return {
                            "title": el.get("title"),
                            "slug": slug,
                            "original_price": orig_normalized,
                            "final_price": final_normalized,
                            "discount_percent": discount_percent,
                            "currency": currency,
                            "thumbnail": thumbnail
                        }
    except Exception:
        pass
        
    return None

