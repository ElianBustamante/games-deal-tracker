import app.steam as steam
import app.database as database

async def save_and_enrich(price: dict) -> dict:
    # Get historical low BEFORE saving the new snapshot
    historical_low = await database.get_historical_low(price["app_id"])
    
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

async def check_watchlist(server_id: str) -> list[dict]:
    watchlist = await database.get_watchlist(server_id)
    enriched_results = []
    
    for game in watchlist:
        price = await steam.get_game_price(game["app_id"])
        if price is None or price.get("discount_percent", 0) == 0:
            continue
            
        if await database.was_notified_today(server_id, game["app_id"]):
            continue
            
        enriched = await save_and_enrich(price)
        enriched_results.append(enriched)
        
    return enriched_results

async def check_general_deals(server_id: str) -> list[dict]:
    deals = await steam.get_featured_deals()
    min_discount = await database.get_min_discount(server_id)
    enriched_results = []
    
    for deal in deals:
        if deal.get("discount_percent", 0) >= min_discount:
            if not await database.was_notified_today(server_id, deal["app_id"]):
                enriched = await save_and_enrich(deal)
                enriched_results.append(enriched)
                
    return enriched_results

async def check_and_notify(bot) -> dict:
    from app.formatter import make_deal_embed
    
    await database.clear_old_notifications()
    servers = await database.get_all_configured_servers()
    
    total_deals_sent = 0
    
    for server_id in servers:
        channel_id = await database.get_channel(server_id)
        if not channel_id:
            continue
            
        try:
            channel = bot.get_channel(int(channel_id))
            if not channel:
                continue
        except Exception:
            continue
            
        watchlist_deals = await check_watchlist(server_id)
        general_deals = await check_general_deals(server_id)
        
        # Combine and deduplicate
        deals_by_app_id = {}
        for deal in general_deals:
            deals_by_app_id[deal["app_id"]] = deal
        for deal in watchlist_deals:
            # Watchlist overwrites general deals
            deals_by_app_id[deal["app_id"]] = deal
            
        for deal in deals_by_app_id.values():
            try:
                embed = make_deal_embed(deal)
                await channel.send(embed=embed)
                await database.mark_as_notified(server_id, deal["app_id"])
                total_deals_sent += 1
            except Exception:
                pass
                
    return {
        "servers_checked": len(servers),
        "total_deals_sent": total_deals_sent
    }
