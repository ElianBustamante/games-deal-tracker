import app.steam as steam
import app.database as database
import app.epic as epic

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
        price.get("currency", "USD"),
        store="steam"
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

async def check_watchlist(target_id: str, country: str, language: str = "es") -> list[dict]:
    watchlist = await database.get_watchlist(target_id)
    enriched_results = []
    
    for game in watchlist:
        app_id_str = str(game["app_id"])
        is_epic_only = app_id_str.startswith("epic:") or not app_id_str.isdigit()
        
        if is_epic_only:
            # EGS Exclusive watchlist item
            slug = app_id_str.replace("epic:", "")
            price = await epic.get_game_price(slug, country, language)
            if price is None or price.get("discount_percent", 0) == 0:
                continue
                
            if await database.was_notified_today(target_id, app_id_str, store="epic"):
                continue
                
            historical_low = await database.get_historical_low(slug, price["currency"], store="epic")
            await database.save_price_snapshot(
                slug,
                price["title"],
                price["final_price"],
                price["original_price"],
                price["discount_percent"],
                price["currency"],
                store="epic"
            )
            
            is_historical_low = False
            if historical_low is None:
                is_historical_low = True
            elif price["final_price"] <= historical_low["price_final"]:
                is_historical_low = True
                
            enriched = price.copy()
            enriched["app_id"] = app_id_str
            enriched["name"] = price["title"]
            enriched["price_original"] = price["original_price"]
            enriched["price_final"] = price["final_price"]
            enriched["url"] = epic.get_store_url(slug)
            enriched["historical_low"] = historical_low
            enriched["is_historical_low"] = is_historical_low
            enriched["store"] = "epic"
            enriched_results.append(enriched)
        else:
            # Steam watchlist item
            app_id = int(app_id_str)
            price = await steam.get_game_price(app_id, country)
            if price is None or price.get("discount_percent", 0) == 0:
                continue
                
            if await database.was_notified_today(target_id, app_id, store="steam"):
                continue
                
            enriched = await save_and_enrich(price)
            enriched["store"] = "steam"
            
            # Enrich with Epic Games Store comparison if available
            if game.get("epic_slug"):
                try:
                    epic_price = await epic.get_game_price(game["epic_slug"], country, language)
                    if epic_price:
                        enriched["epic_price"] = epic_price
                except Exception:
                    pass
                    
            enriched_results.append(enriched)
            
    return enriched_results

async def check_general_deals(target_id: str, deals: list[dict], country: str) -> list[dict]:
    min_discount = await database.get_min_discount(target_id)
    enriched_results = []

    for deal in deals:
        if deal.get("discount_percent", 0) >= min_discount:
            if not await database.was_notified_today(target_id, deal["app_id"], store="steam"):
                # Re-fetch via appdetails to apply content_descriptors filter
                validated = await steam.get_game_price(deal["app_id"], country)
                if validated is None:
                    continue
                enriched = await save_and_enrich(validated)
                enriched["store"] = "steam"
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
        
        watchlist_deals = await check_watchlist(target_id, country, language)
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
                if deal.get("store") == "epic":
                    from app.formatter import make_epic_deal_embed, DealView
                    embed = make_epic_deal_embed(deal, locale=locale)
                    view = DealView(
                        store_url=deal["url"],
                        app_id=deal["app_id"],
                        game_name=deal["name"],
                        epic_slug=deal.get("slug"),
                        locale=locale
                    )
                    await channel.send(embed=embed, view=view)
                    await database.mark_as_notified(target_id, deal["app_id"], store="epic")
                else:
                    from app.formatter import make_deal_embed, DealView
                    embed = make_deal_embed(deal, locale=locale)
                    epic_slug = deal["epic_price"].get("slug") if deal.get("epic_price") else None
                    view = DealView(
                        store_url=deal["url"],
                        app_id=deal["app_id"],
                        game_name=deal["name"],
                        epic_slug=epic_slug,
                        locale=locale
                    )
                    await channel.send(embed=embed, view=view)
                    await database.mark_as_notified(target_id, deal["app_id"], store="steam")
                    
                if is_dm:
                    await database.reset_failed_dm_attempts(target_id)
                total_deals_sent += 1
            except Exception as e:
                if is_dm and ("Cannot send messages" in str(e) or "Forbidden" in str(e)):
                    attempts = await database.increment_failed_dm_attempts(target_id)
                    if attempts >= 3:
                        await database.stop_notifications(target_id)
                        break
                
    return {
        "targets_checked": len(targets),
        "total_deals_sent": total_deals_sent
    }

async def check_epic_and_notify(bot) -> dict:
    from app.formatter import make_epic_deal_embed
    
    await database.clear_old_notifications()
    targets = await database.get_all_configured_targets()
    
    total_deals_sent = 0
    epic_deals_cache = {}
    
    for target in targets:
        key = (target["country"], target["language"])
        if key not in epic_deals_cache:
            epic_deals_cache[key] = await epic.get_deals(target["country"], min_discount=0, language=target["language"])
            
    for target in targets:
        target_id = target["target_id"]
        is_dm = target["is_dm"]
        language = target["language"]
        country = target["country"]
        
        try:
            if is_dm:
                channel = bot.get_user(int(target_id)) or await bot.fetch_user(int(target_id))
            else:
                epic_channel_id = target.get("epic_channel_id")
                channel_to_use = epic_channel_id if epic_channel_id else target["channel_id"]
                if not channel_to_use:
                    continue
                channel = bot.get_channel(int(channel_to_use))
                
            if not channel:
                continue
        except Exception:
            continue
            
        min_discount = await database.get_min_discount(target_id)
        deals = epic_deals_cache.get((country, language), [])
        
        for deal in deals:
            if deal["discount_percent"] < min_discount:
                continue
                
            if await database.was_notified_today(target_id, deal["slug"], store="epic"):
                continue
                
            # Get historical low BEFORE saving the snapshot
            historical_low = await database.get_historical_low(deal["slug"], deal["currency"], store="epic")
            
            # Save the snapshot
            await database.save_price_snapshot(
                deal["slug"],
                deal["title"],
                deal["final_price"],
                deal["original_price"],
                deal["discount_percent"],
                deal["currency"],
                store="epic"
            )
            
            is_historical_low = False
            if historical_low is None:
                is_historical_low = True
            elif deal["final_price"] <= historical_low["price_final"]:
                is_historical_low = True
                
            enriched = deal.copy()
            enriched["name"] = deal["title"]
            enriched["price_original"] = deal["original_price"]
            enriched["price_final"] = deal["final_price"]
            enriched["url"] = epic.get_store_url(deal["slug"])
            enriched["historical_low"] = historical_low
            enriched["is_historical_low"] = is_historical_low
            enriched["store"] = "epic"
            
            locale = await database.get_language(target_id)
            
            try:
                from app.formatter import DealView
                embed = make_epic_deal_embed(enriched, locale=locale)
                view = DealView(
                    store_url=enriched["url"],
                    app_id=f"epic:{deal['slug']}",
                    game_name=enriched["name"],
                    epic_slug=deal["slug"],
                    locale=locale
                )
                await channel.send(embed=embed, view=view)
                await database.mark_as_notified(target_id, deal["slug"], store="epic")
                if is_dm:
                    await database.reset_failed_dm_attempts(target_id)
                total_deals_sent += 1
            except Exception as e:
                if is_dm and ("Cannot send messages" in str(e) or "Forbidden" in str(e)):
                    attempts = await database.increment_failed_dm_attempts(target_id)
                    if attempts >= 3:
                        await database.stop_notifications(target_id)
                        break
                        
    return {
        "targets_checked": len(targets),
        "total_deals_sent": total_deals_sent
    }

async def check_epic_free_games(bot) -> dict:
    from app.formatter import make_epic_free_embed
    
    targets = await database.get_all_configured_targets()
    total_alerts_sent = 0
    free_games_cache = {}
    
    for target in targets:
        key = (target["country"], target["language"])
        if key not in free_games_cache:
            free_games_cache[key] = await epic.get_free_games(target["country"], target["language"])
            
    for target in targets:
        target_id = target["target_id"]
        is_dm = target["is_dm"]
        language = target["language"]
        country = target["country"]
        
        try:
            if is_dm:
                channel = bot.get_user(int(target_id)) or await bot.fetch_user(int(target_id))
            else:
                epic_channel_id = target.get("epic_channel_id")
                channel_to_use = epic_channel_id if epic_channel_id else target["channel_id"]
                if not channel_to_use:
                    continue
                channel = bot.get_channel(int(channel_to_use))
                
            if not channel:
                continue
        except Exception:
            continue
            
        free_games = free_games_cache.get((country, language), {"current": [], "upcoming": []})
        
        new_games = []
        for game in free_games.get("current", []):
            key = f"{game['slug']}_{game['end_date']}"
            if not await database.was_notified_today(target_id, key, store="epic_free"):
                new_games.append(game)
                
        if new_games:
            locale = await database.get_language(target_id)
            try:
                embed = make_epic_free_embed(free_games["current"], free_games["upcoming"], locale=locale)
                await channel.send(embed=embed)
                
                for game in free_games["current"]:
                    key = f"{game['slug']}_{game['end_date']}"
                    await database.mark_as_notified(target_id, key, store="epic_free")
                    
                if is_dm:
                    await database.reset_failed_dm_attempts(target_id)
                total_alerts_sent += 1
            except Exception as e:
                if is_dm and ("Cannot send messages" in str(e) or "Forbidden" in str(e)):
                    attempts = await database.increment_failed_dm_attempts(target_id)
                    if attempts >= 3:
                        await database.stop_notifications(target_id)
                        break
                        
    return {
        "targets_checked": len(targets),
        "total_deals_sent": total_alerts_sent
    }
