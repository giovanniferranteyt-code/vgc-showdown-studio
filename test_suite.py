"""
Comprehensive Verification Test Suite for VGC & Showdown Studio
"""

import sys
import unittest
from pathlib import Path

# Core modules
from core.mechanics import (
    APP_VERSION,
    ShowdownEngine,
    calculate_stat,
    calculate_damage,
    validate_tournament_roster,
    parse_showdown_paste,
    export_showdown_paste,
    discover_formats
)
from core.sprite_loader import SpriteLoader
from scrapers.meta_fetcher import MetaDatabase, check_github_release
from core.simulator import BattleSimulator, BUILTIN_ARCHETYPES
from core.combo_lab import MechanicInteractionMiner, EvolutionaryTeamMutator
from core.planner import TeamAnalyticsEngine, TeamGameplanEngine, EVBenchmarkOptimizer
from core.ots_exporter import export_ots_png
from core.copilot import StudioCopilot

class TestVGCStudio(unittest.TestCase):
    def setUp(self):
        self.engine = ShowdownEngine.get_instance()
        self.db = MetaDatabase.get_instance()

    def test_version(self):
        self.assertEqual(APP_VERSION, "1.0.0")

    def test_pokedex_and_moves_loaded(self):
        self.assertGreater(len(self.engine.pokedex), 500)
        self.assertGreater(len(self.engine.moves), 300)
        self.assertGreater(len(self.engine.items), 100)

    def test_classic_and_champions_stats(self):
        # Incineroar: base 95 HP, 115 Atk
        # Classic Level 50: 252 HP -> floor(((2*95 + 31 + 63)*50)/100) + 60 = 202
        hp_classic = calculate_stat(95, "hp", 252, 31, "Careful", 50, is_champions_sp=False)
        self.assertEqual(hp_classic, 202)

        # Champions SP: 32 SP -> base + 75 + SP = 95 + 75 + 32 = 202
        hp_champions = calculate_stat(95, "hp", 32, 31, "Careful", 50, is_champions_sp=True)
        self.assertEqual(hp_champions, 202)

    def test_damage_calc_16_rolls(self):
        att = {
            "name": "Flutter Mane",
            "item": "Choice Specs",
            "nature": "Timid",
            "evs": {"spa": 252, "spe": 252},
            "level": 50
        }
        df = {
            "name": "Incineroar",
            "item": "Sitrus Berry",
            "nature": "Careful",
            "evs": {"hp": 252, "spd": 96},
            "level": 50
        }
        res = calculate_damage(att, df, "Moonblast", field={"is_doubles": True})
        self.assertEqual(len(res["rolls"]), 16)
        self.assertGreater(res["min_damage"], 0)
        self.assertGreaterEqual(res["max_damage"], res["min_damage"])
        self.assertIn("%", res["desc"])

    def test_damage_calc_weather_and_ruin(self):
        att = {
            "name": "Chi-Yu",
            "nature": "Modest",
            "evs": {"spa": 252},
            "level": 50
        }
        df = {
            "name": "Rillaboom",
            "nature": "Adamant",
            "evs": {"hp": 252, "spd": 4},
            "level": 50
        }
        # In Sun with Beads of Ruin
        res = calculate_damage(att, df, "Heat Wave", field={"weather": "Sun", "beads_of_ruin": True, "is_doubles": True})
        self.assertGreaterEqual(res["ohko_chance"], 90.0)

    def test_legality_validator(self):
        legal_team = [
            {"name": "Incineroar", "item": "Sitrus Berry", "ability": "Intimidate", "moves": ["Fake Out", "Flare Blitz", "Knock Off", "Parting Shot"], "evs": {"hp": 252, "def": 156, "spd": 100}, "is_sp": False},
            {"name": "Rillaboom", "item": "Miracle Seed", "ability": "Grassy Surge", "moves": ["Grassy Glide", "Wood Hammer", "Fake Out", "U-turn"], "evs": {"hp": 252, "atk": 252, "def": 4}, "is_sp": False},
        ]
        is_legal, issues, warnings = validate_tournament_roster(legal_team, "gen9vgc2024regg")
        self.assertTrue(is_legal)
        self.assertEqual(len(issues), 0)

        # Duplicate item violation
        illegal_team = [
            {"name": "Incineroar", "item": "Sitrus Berry", "ability": "Intimidate", "moves": ["Fake Out"], "evs": {}},
            {"name": "Rillaboom", "item": "Sitrus Berry", "ability": "Grassy Surge", "moves": ["Grassy Glide"], "evs": {}}
        ]
        is_legal_bad, issues_bad, _ = validate_tournament_roster(illegal_team, "gen9vgc2024regg")
        self.assertFalse(is_legal_bad)
        self.assertTrue(any("Item Clause" in iss for iss in issues_bad))

    def test_showdown_parser_and_exporter(self):
        paste = """Incineroar @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Atk / 156 Def / 96 SpD / 4 Spe
Careful Nature
- Fake Out
- Parting Shot
- Knock Off
- Flare Blitz"""

        team = parse_showdown_paste(paste)
        self.assertEqual(len(team), 1)
        mon = team[0]
        self.assertEqual(mon["name"], "Incineroar")
        self.assertEqual(mon["item"], "Sitrus Berry")
        self.assertEqual(len(mon["moves"]), 4)

        exported = export_showdown_paste(team)
        self.assertIn("Incineroar @ Sitrus Berry", exported)
        self.assertIn("- Fake Out", exported)

    def test_simulator_and_threats(self):
        sim = BattleSimulator()
        team = BUILTIN_ARCHETYPES["Classic Balance Core"]
        spread_res = sim.analyze_matchup_spread(team)
        self.assertIn("Favored", spread_res)
        self.assertIn("Unfavorable", spread_res)
        self.assertGreater(len(spread_res["all"]), 3)

        threats = sim.scan_threats(team, limit=5)
        self.assertEqual(len(threats), 5)

        gems = sim.find_offmeta_counters(team, limit=3)
        self.assertGreaterEqual(len(gems), 1)

    def test_combo_lab(self):
        miner = MechanicInteractionMiner()
        combos = miner.discover_combos("Palafin")
        self.assertGreaterEqual(len(combos), 2)
        self.assertTrue(any("Eject Pack" in c["combo_name"] for c in combos))

    def test_planner_analytics_and_optimizer(self):
        analytics = TeamAnalyticsEngine()
        team = BUILTIN_ARCHETYPES["Classic Balance Core"]
        report = analytics.generate_report_card(team)
        self.assertGreaterEqual(report["synergy_score"], 50)
        self.assertGreaterEqual(report["board_control_score"], 40)
        self.assertGreater(report["pilot_difficulty_stars"], 0)

        optimizer = EVBenchmarkOptimizer()
        surv = optimizer.optimize_defensive_survival(team[0], "Flutter Mane", "Moonblast")
        self.assertIn("defense_stat_needed", surv)

        creep = optimizer.optimize_speed_creep(team[0], "Farigiraf")
        self.assertIn("desired_speed", creep)

    def test_ots_png_exporter(self):
        team = BUILTIN_ARCHETYPES["Classic Balance Core"]
        ots_path = export_ots_png(team, "UnitTest_Team", "Tester")
        self.assertTrue(ots_path.exists())
        self.assertGreater(ots_path.stat().st_size, 5000)

    def test_copilot_queries(self):
        copilot = StudioCopilot()
        team = BUILTIN_ARCHETYPES["Classic Balance Core"]

        r1 = copilot.process_query("rate my synergy", team)
        self.assertIn("Synergy Score", r1)

        r2 = copilot.process_query("check board control", team)
        self.assertIn("Board Control", r2)

        r3 = copilot.process_query("discover weird combos for Palafin", team)
        self.assertIn("Rogue Synergy", r3)

if __name__ == "__main__":
    unittest.main()
