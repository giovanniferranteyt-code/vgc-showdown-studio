"""
VGC & Showdown Studio - Headless Data Sync Job
Automated CLI script for GitHub Actions and background synchronization.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path

from core.mechanics import ShowdownEngine, discover_formats
from scrapers.meta_fetcher import MetaDatabase, sync_smogon_format, scrape_tournament_rosters

def main():
    print("=" * 65)
    print(" VGC & SHOWDOWN STUDIO - HEADLESS DATA PIPELINE")
    print("=" * 65)
    start_time = time.time()

    # 1. Initialize Showdown Engine & download core data
    print("\n[1/4] Initializing Showdown Engine & Data Cache...")
    engine = ShowdownEngine.get_instance()
    print(f" -> Pokédex entries: {len(engine.pokedex)}")
    print(f" -> Moves entries:   {len(engine.moves)}")
    print(f" -> Items entries:   {len(engine.items)}")

    # 2. Discover active formats
    print("\n[2/4] Auto-discovering active VGC, Champions, and Smogon formats...")
    formats = discover_formats()
    print(f" -> Found {len(formats)} target formats:")
    for f in formats[:6]:
        print(f"    * [{f['id']}] {f['name']} (SP Mode: {f.get('is_sp')})")

    # 3. Sync Smogon Stats & Chaos JSON
    print("\n[3/4] Synchronizing Smogon stats, spreads, and teammate co-occurrence...")
    db = MetaDatabase.get_instance()
    synced_formats = 0
    # Prioritize active VGC & Champions formats
    target_formats = [
        "gen9championsvgc2026regmc",
        "gen9vgc2024regg",
        "gen9vgc2024regh",
        "gen9doublesou"
    ]
    for fmt in formats:
        if fmt["id"] not in target_formats and len(target_formats) < 8:
            target_formats.append(fmt["id"])

    for fmt_id in target_formats:
        print(f" -> Fetching stats for '{fmt_id}'...", end=" ", flush=True)
        ok = sync_smogon_format(fmt_id, db)
        if ok:
            synced_formats += 1
            print("OK!")
        else:
            print("Skipped/Offline.")

    # 4. Scrape tournament rosters & PokePastes
    print("\n[4/4] Scraping tournament rosters & PokePastes from Limitless, Victory Road, etc...")
    total_rosters = scrape_tournament_rosters("gen9vgc2024regg")
    print(f" -> Ingested {total_rosters} new tournament rosters.")

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 65)
    print(f" SUCCESS: Meta pipeline completed in {elapsed} seconds.")
    print(f" Database located at: {db.db_path}")
    print("=" * 65)

if __name__ == "__main__":
    main()
