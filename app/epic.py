import os
import logging
import asyncio
import aiohttp
from curl_cffi.requests import AsyncSession
from dotenv import load_dotenv
from cachetools import TTLCache

load_dotenv()

logger = logging.getLogger("steam_deals_bot")

STEAM_COUNTRY = os.getenv("STEAM_COUNTRY", "cl")
STEAM_LANGUAGE = os.getenv("STEAM_LANGUAGE", "es")

EPIC_COUNTRY = os.getenv("EPIC_COUNTRY", STEAM_COUNTRY)
EPIC_LANGUAGE = os.getenv("EPIC_LANGUAGE", STEAM_LANGUAGE)

# Cache for EGS deals (5 minutes TTL)
deals_cache = TTLCache(maxsize=100, ttl=300)

# Cache for search_game (1 hour TTL)
search_cache = TTLCache(maxsize=100, ttl=3600)

# Cache for get_game_price (15 minutes TTL)
price_cache = TTLCache(maxsize=1000, ttl=900)

def get_epic_locale(lang: str) -> str:
    # Map to Epic supported locale, defaulting to es-MX for Spanish as requested
    return "es-MX" if lang.lower() == "es" else "en-US"

def get_store_url(slug: str) -> str:
    return f"https://store.epicgames.com/p/{slug}"

def normalize_epic_price(price_val: int, currency: str) -> int:
    """
    Normalizes Epic Games prices to cents format (matching Steam's convention).
    Epic returns zero-subunit currencies (JPY, KRW, VND) in their base unit (e.g. 2080).
    Steam always returns them multiplied by 100 (208000).
    So we multiply Epic zero-subunit currencies by 100.
    """
    if not price_val:
        return 0
    curr_upper = currency.upper()
    if curr_upper in ["JPY", "KRW", "VND"]:
        return price_val * 100
    return price_val

def resolve_epic_slug(element: dict) -> str | None:
    mappings = element.get("catalogNs", {}).get("mappings", []) or []
    for mapping in mappings:
        if mapping.get("pageType") == "productHome":
            slug = mapping.get("pageSlug")
            if slug:
                return slug
    for mapping in mappings:
        slug = mapping.get("pageSlug")
        if slug:
            return slug
    return element.get("productSlug") or element.get("urlSlug")

async def _fetch_free_games(url: str, headers: dict, timeout_secs: int = 10, max_attempts: int = 3, delay: float = 1.0) -> any:
    for attempt in range(1, max_attempts + 1):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_secs)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status in [429, 500, 502, 503, 504]:
                        logger.warning(
                            f"Epic Free Games API returned transient status {response.status} for URL: {url}. "
                            f"Attempt {attempt} of {max_attempts}."
                        )
                        if attempt == max_attempts:
                            response.raise_for_status()
                    else:
                        response.raise_for_status()
        except Exception as e:
            logger.warning(
                f"Network exception calling Epic Free Games API: {e} for URL: {url}. "
                f"Attempt {attempt} of {max_attempts}."
            )
            if attempt == max_attempts:
                logger.error(f"Failed all {max_attempts} attempts to fetch Epic free games: {url}. Error: {e}", exc_info=True)
                raise
            await asyncio.sleep(delay * attempt)
    return None

async def _post_graphql(url: str, headers: dict, payload: dict, timeout_secs: int = 10, max_attempts: int = 3, delay: float = 1.0) -> any:
    for attempt in range(1, max_attempts + 1):
        try:
            async with AsyncSession(impersonate="chrome120") as s:
                response = await s.post(url, headers=headers, json=payload, timeout=timeout_secs)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [429, 500, 502, 503, 504]:
                    logger.warning(
                        f"Epic GraphQL API returned transient status {response.status_code} for URL: {url}. "
                        f"Attempt {attempt} of {max_attempts}."
                    )
                    if attempt == max_attempts:
                        raise Exception(f"HTTP {response.status_code}")
                else:
                    raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            logger.warning(
                f"Network or Cloudflare bypass exception calling Epic GraphQL: {e} for URL: {url}. "
                f"Attempt {attempt} of {max_attempts}."
            )
            if attempt == max_attempts:
                logger.error(f"Failed all {max_attempts} attempts to execute Epic GraphQL query. Error: {e}", exc_info=True)
                raise
            await asyncio.sleep(delay * attempt)
    return None

async def get_free_games(country: str = EPIC_COUNTRY, language: str = EPIC_LANGUAGE) -> dict:
    locale = get_epic_locale(language)
    country_upper = country.upper()
    
    url = f"https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale={locale}&country={country_upper}&allowCountries={country_upper}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    result = {"current": [], "upcoming": []}
    
    try:
        data = await _fetch_free_games(url, headers)
        if data:
            elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []) or []
            
            for el in elements:
                title = el.get("title")
                slug = resolve_epic_slug(el)
                
                if not slug or not title:
                    continue
                    
                thumbnail = None
                key_images = el.get("keyImages", [])
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

async def get_deals(country: str = EPIC_COUNTRY, min_discount: int = 0, language: str = EPIC_LANGUAGE) -> list[dict]:
    cache_key = f"{country}_{min_discount}_{language}"
    if cache_key in deals_cache:
        return deals_cache[cache_key]
        
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
          count: 30
          category: "games/edition/base"
        ) {
          elements {
            title
            id
            namespace
            productSlug
            urlSlug
            catalogNs {
              mappings {
                pageSlug
                pageType
              }
            }
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
        data = await _post_graphql(url, headers, payload)
        if data:
            elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []) or []
            
            for el in elements:
                title = el.get("title")
                slug = resolve_epic_slug(el)
                if not slug or not title:
                    continue
                    
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
                    
                if discount_percent < min_discount or discount_percent == 0:
                    continue
                    
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
        
    if deals:
        deals_cache[cache_key] = deals
    return deals

async def search_game(name: str, language: str = EPIC_LANGUAGE) -> dict | None:
    cache_key = f"{name.lower().strip()}_{language}"
    if cache_key in search_cache:
        return search_cache[cache_key]
        
    locale = get_epic_locale(language)
    url = "https://store.epicgames.com/graphql"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://store.epicgames.com",
        "Referer": "https://store.epicgames.com/"
    }
    
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
            catalogNs {
              mappings {
                pageSlug
                pageType
              }
            }
          }
        }
      }
    }
    """ % (escaped_name, locale)
    
    payload = {"query": query}
    
    try:
        data = await _post_graphql(url, headers, payload)
        if data:
            elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []) or []
            if elements:
                best_match = None
                search_clean = name.lower().strip()
                for el in elements:
                    el_title = el.get("title", "")
                    if el_title.lower().strip() == search_clean:
                        best_match = el
                        break
                        
                if not best_match:
                    best_match = elements[0]
                    
                slug = resolve_epic_slug(best_match)
                if slug:
                    res = {
                        "title": best_match.get("title"),
                        "slug": slug,
                        "epic_id": best_match.get("id"),
                        "namespace": best_match.get("namespace")
                    }
                    search_cache[cache_key] = res
                    return res
    except Exception:
        pass
        
    return None

async def get_game_price(slug: str, country: str = EPIC_COUNTRY, language: str = EPIC_LANGUAGE, search_keyword: str = None) -> dict | None:
    cache_key = f"{slug.lower().strip()}_{country}_{language}"
    if cache_key in price_cache:
        return price_cache[cache_key]
        
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
    
    import re
    if not search_keyword:
        search_keyword = re.sub(r'-[0-9a-fA-F]{6}$', '', slug).replace('-', ' ')
    escaped_keyword = search_keyword.replace('"', '\\"')
    
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
            catalogNs {
              mappings {
                pageSlug
                pageType
              }
            }
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
    """ % (escaped_keyword, country_upper, locale, country_upper)
    
    payload = {"query": query}
    
    try:
        data = await _post_graphql(url, headers, payload)
        if data:
            elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []) or []
            
            for el in elements:
                el_slug = resolve_epic_slug(el)
                if el_slug and slug and el_slug.lower().strip() == slug.lower().strip():
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
                    
                    res = {
                        "title": el.get("title"),
                        "slug": slug,
                        "original_price": orig_normalized,
                        "final_price": final_normalized,
                        "discount_percent": discount_percent,
                        "currency": currency,
                        "thumbnail": thumbnail
                    }
                    price_cache[cache_key] = res
                    return res
    except Exception:
        pass
        
    return None
