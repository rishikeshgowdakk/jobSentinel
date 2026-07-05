import re

def main():
    with open('src/main.py', 'r') as f:
        content = f.read()

    # Let's replace the whole aggregation logic block
    old_block = """            # Consolidated search keywords and locations to minimize WAF blockages/rate limits
            consolidated_keywords = set()
            consolidated_locations = set()
            job_types = set()
            exp_levels = set()
            
            # Keep track of individual preferences to filter matching
            user_prefs_map = {}
            for p in profiles:
                uid = p["user_id"]
                prefs = db.get_user_preferences(uid)
                user_prefs_map[uid] = prefs
                
                for k in prefs["keywords"].split(","):
                    if k.strip(): consolidated_keywords.add(k.strip())
                for l in prefs["locations"].split(","):
                    if l.strip(): consolidated_locations.add(l.strip())
                job_types.add(prefs.get("job_type", "All"))
                exp_levels.add(prefs.get("experience_level", "All"))
            
            keywords_list = list(consolidated_keywords) if consolidated_keywords else [config.JOB_KEYWORDS]
            locations_list = list(consolidated_locations) if consolidated_locations else [config.JOB_LOCATIONS]
            
            jtype = "I" if "I" in job_types or any("intern" in k.lower() for k in keywords_list) else "All"
            elevel = "2" if "2" in exp_levels or jtype == "I" else "All"
            
            logger.info(f"HUNT CYCLE START: Scrape union of Keywords={keywords_list} | Locations={locations_list} | Type={jtype} for {len(profiles)} active profiles")
            
            # 2. Scrape platforms in parallel
            tasks = [
                scraper.scrape_linkedin(keywords_list, locations_list, jtype, elevel),
                scraper.scrape_naukri(keywords_list, locations_list, jtype, elevel),
                scraper.scrape_google_xray(keywords_list, locations_list, jtype, elevel)
            ]
            
            platform_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_found_jobs = []
            
            for res in platform_results:
                if isinstance(res, list):
                    all_found_jobs.extend(res)
                elif isinstance(res, Exception):
                    logger.error(f"Platform scraper error: {res}")"""

    new_block = """            user_prefs_map = {}
            all_found_jobs = []
            
            # 2. Scrape platforms per profile
            for p in profiles:
                uid = p["user_id"]
                prefs = db.get_user_preferences(uid)
                user_prefs_map[uid] = prefs
                
                k_list = [k.strip() for k in prefs["keywords"].split(",") if k.strip()] or [config.JOB_KEYWORDS]
                l_list = [l.strip() for l in prefs["locations"].split(",") if l.strip()] or [config.JOB_LOCATIONS]
                
                jtype = "I" if prefs.get("job_type", "All") == "I" or any("intern" in k.lower() for k in k_list) else "All"
                elevel = "2" if prefs.get("experience_level", "All") == "2" or jtype == "I" else "All"
                
                logger.info(f"HUNT CYCLE START for {uid}: Keywords={k_list} | Locations={l_list} | Type={jtype}")
                
                tasks = [
                    scraper.scrape_linkedin(k_list, l_list, jtype, elevel),
                    scraper.scrape_naukri(k_list, l_list, jtype, elevel),
                    scraper.scrape_google_xray(k_list, l_list, jtype, elevel)
                ]
                
                platform_results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in platform_results:
                    if isinstance(res, list):
                        all_found_jobs.extend(res)
                    elif isinstance(res, Exception):
                        logger.error(f"Platform scraper error: {res}")"""

    if old_block in content:
        content = content.replace(old_block, new_block)
    else:
        print("Could not find the block to replace!")

    # Fix the mock jobs fallback to use the first profile's keywords just in case
    old_mock = """                mock_jobs = scraper.generate_mock_jobs(keywords_list)"""
    new_mock = """                k_list = [k.strip() for k in user_prefs_map.get(profiles[0]["user_id"], {}).get("keywords", "").split(",")] if profiles else [config.JOB_KEYWORDS]
                mock_jobs = scraper.generate_mock_jobs(k_list)"""
    if old_mock in content:
        content = content.replace(old_mock, new_mock)

    with open('src/main.py', 'w') as f:
        f.write(content)
    print("main.py updated successfully.")

if __name__ == '__main__':
    main()
