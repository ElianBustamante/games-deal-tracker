import app.steam as steam
import app.database as database

async def save_and_enrich(price: dict) -> dict:
    # Get historical low BEFORE saving the new snapshot
    historical_low = await database.get_historical_low(price["app_id"], price.get("currency", "USD"))
    
    # Save the snapshot
    await database.save_price_snapshot(
        price["app_id"], 
        price.get("name", "Unknown Game"), 
        price["price_final"], 
        price["price_original"], 
        price["discount_percent"], 
        price.get("currency", "USD")
    )
    
    # Determine if it's a historical low
    is_historical_low = False
    if historical_low is None:
        is_historical_low = True
    elif price["price_final"] <= historical_low["price_final"]:
        is_historical_low = True
        
    enriched_price = price.copy()
    enriched_price["historical_low"] = historical_low
    enriched_price["is_historical_low"] = is_historical_low
    enriched_price["url"] = steam.get_store_url(price["app_id"])
    
    return enriched_price

async def check_watchlist(target_id: str, country: str) -> list[dict]:
    watchlist = await database.get_watchlist(target_id)
    enriched_results = []
    
    for game in watchlist:
        price = await steam.get_game_price(game["app_id"], country)
        if price is None or price.get("discount_percent", 0) == 0:
            continue
            
        if await database.was_notified_today(target_id, game["app_id"]):
            continue
            
        enriched = await save_and_enrich(price)
        enriched_results.append(enriched)
        
    return enriched_results

async def check_general_deals(target_id: str, deals: list[dict], country: str) -> list[dict]:
    min_discount = await database.get_min_discount(target_id)
    enriched_results = []

    for deal in deals:
        if deal.get("discount_percent", 0) >= min_discount:
            if not await database.was_notified_today(target_id, deal["app_id"]):
                # Re-fetch via appdetails to apply content_descriptors filter
                validated = await steam.get_game_price(deal["app_id"], country)
                if validated is None:
                    continue
                enriched = await save_and_enrich(validated)
                enriched_results.append(enriched)

    return enriched_results

async def check_and_notify(bot) -> dict:
    from app.formatter import make_deal_embed
    
    await database.clear_old_notifications()
    targets = await database.get_all_configured_targets()
    
    total_deals_sent = 0
    # Group by unique country/language to minimize Steam API calls
    featured_deals_cache = {}
    for target in targets:
        key = (target["country"], target["language"])
        if key not in featured_deals_cache:
            featured_deals_cache[key] = await steam.get_featured_deals(target["country"], target["language"])
            
    for target in targets:
        target_id = target["target_id"]
        is_dm = target["is_dm"]
        channel_id = target["channel_id"]
        country = target["country"]
        language = target["language"]
        
        try:
            if is_dm:
                channel = bot.get_user(int(target_id)) or await bot.fetch_user(int(target_id))
            else:
                channel = bot.get_channel(int(channel_id))
                
            if not channel:
                continue
        except Exception:
            continue
            
        deals = featured_deals_cache.get((country, language), [])
        
        watchlist_deals = await check_watchlist(target_id, country)
        general_deals = await check_general_deals(target_id, deals, country)
        
        # Combine and deduplicate
        deals_by_app_id = {}
        for deal in general_deals:
            deals_by_app_id[deal["app_id"]] = deal
        for deal in watchlist_deals:
            # Watchlist overwrites general deals
            deals_by_app_id[deal["app_id"]] = deal
            
        locale = await database.get_language(target_id)
        
        for deal in deals_by_app_id.values():
            try:
                embed = make_deal_embed(deal, locale=locale)
                await channel.send(embed=embed)
                await database.mark_as_notified(target_id, deal["app_id"])
                if is_dm:
                    await database.reset_failed_dm_attempts(target_id)
                total_deals_sent += 1
            except Exception as e:
                if is_dm and "Cannot send messages" in str(e) or "Forbidden" in str(e):
                    attempts = await database.increment_failed_dm_attempts(target_id)
                    if attempts >= 3:
                        await database.stop_notifications(target_id)
                        break
                
    return {
        "targets_checked": len(targets),
        "total_deals_sent": total_deals_sent
    }
