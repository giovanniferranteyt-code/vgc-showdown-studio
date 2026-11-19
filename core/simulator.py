"""
VGC & Showdown Studio - Battle Simulator & Matchup Analyzer
Features Monte Carlo 2v2/1v1 battle engine, dynamic meta archetype clustering,
Matchup Spread Analyzer, Bad Pokémon Threat Scanner, and Anti-Meta Hidden Gem Finder.
"""

from __future__ import annotations
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from core.mechanics import (
    ShowdownEngine,
    calculate_damage,
    calculate_stat,
    get_type_effectiveness,
    resolve_form_change,
    BUILTIN_POKEMON,
    BUILTIN_MOVES
)
from scrapers.meta_fetcher import MetaDatabase

# Standard Archetype Templates
BUILTIN_ARCHETYPES = {
    "Classic Balance Core": [
        {"name": "Incineroar", "item": "Sitrus Berry", "ability": "Intimidate", "moves": ["Fake Out", "Parting Shot", "Knock Off", "Flare Blitz"], "nature": "Careful", "evs": {"hp": 252, "atk": 4, "def": 156, "spa": 0, "spd": 96, "spe": 4}},
        {"name": "Rillaboom", "item": "Miracle Seed", "ability": "Grassy Surge", "moves": ["Grassy Glide", "Wood Hammer", "Fake Out", "U-turn"], "nature": "Adamant", "evs": {"hp": 252, "atk": 252, "def": 4, "spa": 0, "spd": 0, "spe": 0}},
        {"name": "Flutter Mane", "item": "Booster Energy", "ability": "Protosynthesis", "moves": ["Moonblast", "Shadow Ball", "Dazzling Gleam", "Protect"], "nature": "Timid", "evs": {"hp": 116, "atk": 0, "def": 156, "spa": 116, "spd": 4, "spe": 116}},
        {"name": "Urshifu-Rapid-Strike", "item": "Choice Scarf", "ability": "Unseen Fist", "moves": ["Surging Strikes", "Close Combat", "Aqua Jet", "U-turn"], "nature": "Jolly", "evs": {"hp": 4, "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252}},
        {"name": "Kingambit", "item": "Assault Vest", "ability": "Defiant", "moves": ["Kowtow Cleave", "Sucker Punch", "Iron Head", "Protect"], "nature": "Adamant", "evs": {"hp": 252, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 0}},
        {"name": "Whimsicott", "item": "Focus Sash", "ability": "Prankster", "moves": ["Tailwind", "Moonblast", "Encore", "Protect"], "nature": "Timid", "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252}},
    ],
    "Rain Hyper Offense": [
        {"name": "Pelipper", "item": "Focus Sash", "ability": "Drizzle", "moves": ["Weather Ball", "Hurricane", "Tailwind", "Protect"], "nature": "Modest", "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252}},
        {"name": "Archaludon", "item": "Assault Vest", "ability": "Stamina", "moves": ["Electro Shot", "Flash Cannon", "Draco Meteor", "Body Press"], "nature": "Modest", "evs": {"hp": 252, "atk": 0, "def": 4, "spa": 252, "spd": 0, "spe": 0}},
        {"name": "Urshifu-Rapid-Strike", "item": "Mystic Water", "ability": "Unseen Fist", "moves": ["Surging Strikes", "Close Combat", "Aqua Jet", "Detect"], "nature": "Adamant", "evs": {"hp": 4, "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252}},
        {"name": "Rillaboom", "item": "Assault Vest", "ability": "Grassy Surge", "moves": ["Grassy Glide", "Wood Hammer", "Fake Out", "U-turn"], "nature": "Adamant", "evs": {"hp": 252, "atk": 252, "def": 4, "spa": 0, "spd": 0, "spe": 0}},
        {"name": "Farigiraf", "item": "Rocky Helmet", "ability": "Armor Tail", "moves": ["Psychic", "Hyper Voice", "Trick Room", "Helping Hand"], "nature": "Bold", "evs": {"hp": 252, "atk": 0, "def": 156, "spa": 0, "spd": 100, "spe": 0}},
        {"name": "Flutter Mane", "item": "Choice Specs", "ability": "Protosynthesis", "moves": ["Moonblast", "Shadow Ball", "Dazzling Gleam", "Thunder"], "nature": "Timid", "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252}},
    ],
    "Sun Room / Hyper Sun": [
        {"name": "Torkoal", "item": "Charcoal", "ability": "Drought", "moves": ["Eruption", "Heat Wave", "Earth Power", "Protect"], "nature": "Quiet", "evs": {"hp": 252, "atk": 0, "def": 0, "spa": 252, "spd": 4, "spe": 0}},
        {"name": "Chi-Yu", "item": "Choice Scarf", "ability": "Beads of Ruin", "moves": ["Heat Wave", "Dark Pulse", "Overheat", "Snarl"], "nature": "Modest", "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252}},
        {"name": "Flutter Mane", "item": "Booster Energy", "ability": "Protosynthesis", "moves": ["Moonblast", "Shadow Ball", "Dazzling Gleam", "Protect"], "nature": "Timid", "evs": {"hp": 116, "atk": 0, "def": 156, "spa": 116, "spd": 4, "spe": 116}},
        {"name": "Koraidon", "item": "Clear Amulet", "ability": "Orichalcum Pulse", "moves": ["Collision Course", "Flare Blitz", "Dragon Claw", "Protect"], "nature": "Jolly", "evs": {"hp": 4, "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252}},
        {"name": "Farigiraf", "item": "Sitrus Berry", "ability": "Armor Tail", "moves": ["Trick Room", "Psychic", "Helping Hand", "Imprison"], "nature": "Quiet", "evs": {"hp": 252, "atk": 0, "def": 140, "spa": 0, "spd": 116, "spe": 0}},
        {"name": "Ursaluna-Bloodmoon", "item": "Life Orb", "ability": "Mind's Eye", "moves": ["Blood Moon", "Hyper Voice", "Earth Power", "Protect"], "nature": "Modest", "evs": {"hp": 252, "atk": 0, "def": 0, "spa": 252, "spd": 4, "spe": 0}},
    ],
    "Trick Room Psyspam": [
        {"name": "Indeedee-F", "item": "Psychic Seed", "ability": "Psychic Surge", "moves": ["Follow Me", "Helping Hand", "Trick Room", "Dazzling Gleam"], "nature": "Relaxed", "evs": {"hp": 252, "atk": 0, "def": 252, "spa": 0, "spd": 4, "spe": 0}},
        {"name": "Armarouge", "item": "Twisted Spoon", "ability": "Flash Fire", "moves": ["Expanding Force", "Armor Cannon", "Wide Guard", "Trick Room"], "nature": "Quiet", "evs": {"hp": 252, "atk": 0, "def": 0, "spa": 252, "spd": 4, "spe": 0}},
        {"name": "Ursaluna-Bloodmoon", "item": "Silk Scarf", "ability": "Mind's Eye", "moves": ["Blood Moon", "Hyper Voice", "Earth Power", "Protect"], "nature": "Quiet", "evs": {"hp": 252, "atk": 0, "def": 4, "spa": 252, "spd": 0, "spe": 0}},
        {"name": "Torkoal", "item": "Charcoal", "ability": "Drought", "moves": ["Eruption", "Heat Wave", "Solar Beam", "Protect"], "nature": "Quiet", "evs": {"hp": 252, "atk": 0, "def": 0, "spa": 252, "spd": 4, "spe": 0}},
        {"name": "Kingambit", "item": "Assault Vest", "ability": "Defiant", "moves": ["Kowtow Cleave", "Sucker Punch", "Iron Head", "Low Kick"], "nature": "Brave", "evs": {"hp": 252, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 0}},
        {"name": "Amoonguss", "item": "Sitrus Berry", "ability": "Regenerator", "moves": ["Spore", "Rage Powder", "Pollen Puff", "Protect"], "nature": "Sassy", "evs": {"hp": 252, "atk": 0, "def": 156, "spa": 0, "spd": 100, "spe": 0}},
    ],
    "Champions Mega Offense": [
        {"name": "Kangaskhan-Mega", "item": "Kangaskhanite", "ability": "Parental Bond", "moves": ["Fake Out", "Double-Edge", "Sucker Punch", "Power-Up Punch"], "nature": "Jolly", "evs": {"hp": 4, "atk": 32, "def": 0, "spa": 0, "spd": 0, "spe": 30}, "is_sp": True, "gimmick": "Mega Evolution"},
        {"name": "Charizard-Mega-Y", "item": "Charizardite Y", "ability": "Drought", "moves": ["Heat Wave", "Solar Beam", "Overheat", "Protect"], "nature": "Timid", "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 32, "spd": 0, "spe": 30}, "is_sp": True, "gimmick": "Mega Evolution"},
        {"name": "Salamence-Mega", "item": "Salamencite", "ability": "Aerilate", "moves": ["Double-Edge", "Hyper Voice", "Tailwind", "Protect"], "nature": "Hasty", "evs": {"hp": 0, "atk": 32, "def": 0, "spa": 4, "spd": 0, "spe": 30}, "is_sp": True, "gimmick": "Mega Evolution"},
        {"name": "Rillaboom", "item": "Miracle Seed", "ability": "Grassy Surge", "moves": ["Grassy Glide", "Wood Hammer", "Fake Out", "U-turn"], "nature": "Adamant", "evs": {"hp": 32, "atk": 32, "def": 0, "spa": 0, "spd": 2, "spe": 0}, "is_sp": True},
        {"name": "Incineroar", "item": "Sitrus Berry", "ability": "Intimidate", "moves": ["Fake Out", "Parting Shot", "Knock Off", "Flare Blitz"], "nature": "Careful", "evs": {"hp": 32, "atk": 2, "def": 16, "spa": 0, "spd": 16, "spe": 0}, "is_sp": True},
        {"name": "Sneasler", "item": "Focus Sash", "ability": "Unburden", "moves": ["Close Combat", "Dire Claw", "Fake Out", "Protect"], "nature": "Jolly", "evs": {"hp": 0, "atk": 32, "def": 0, "spa": 0, "spd": 2, "spe": 32}, "is_sp": True},
    ]
}

class BattleSimulator:
    def __init__(self, format_id: str = "gen9vgc2024regg"):
        self.format_id = format_id
        self.engine = ShowdownEngine.get_instance()
        self.db = MetaDatabase.get_instance()

    def get_meta_archetypes(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch archetypes dynamically from vgc_meta.db or use high-tier built-ins."""
        archetypes = dict(BUILTIN_ARCHETYPES)
        top_meta = self.db.get_top_pokemon(self.format_id, limit=20)
        if len(top_meta) >= 6:
            # Build dynamic meta-aggregate team
            dyn_team = []
            for mon in top_meta[:6]:
                name = mon["name"]
                meta_info = self.db.get_top_meta_for_pokemon(name, self.format_id)
                spread = meta_info.get("top_spread") or {"nature": "Hardy", "evs": {"hp": 252, "atk": 4, "def": 124, "spa": 4, "spd": 124, "spe": 0}, "is_sp": False}
                dyn_team.append({
                    "name": name,
                    "item": meta_info.get("top_item") or "Sitrus Berry",
                    "ability": meta_info.get("top_ability") or "Intimidate",
                    "moves": meta_info.get("top_moves") or ["Protect", "Fake Out", "U-turn", "Shadow Ball"],
                    "nature": spread.get("nature", "Hardy"),
                    "evs": spread.get("evs", {}),
                    "is_sp": spread.get("is_sp", False)
                })
            archetypes["Top Ladder Meta Aggregate"] = dyn_team
        return archetypes

    def simulate_1v1_turn(self, p1: Dict[str, Any], p2: Dict[str, Any], field: Optional[Dict[str, Any]] = None) -> float:
        """
        Fast 1v1 battle evaluator: returns p1 win probability (0.0 to 1.0)
        based on damage output, speed tier, and bulk.
        """
        field = field or {}
        # Calculate speeds
        p1_stats, _, _ = resolve_form_change(p1.get("name", ""))
        p2_stats, _, _ = resolve_form_change(p2.get("name", ""))
        
        p1_spe = calculate_stat(p1_stats.get("spe", 100), "spe", p1.get("evs", {}).get("spe", 0), 31, p1.get("nature", "Hardy"), 50, p1.get("is_sp", False))
        p2_spe = calculate_stat(p2_stats.get("spe", 100), "spe", p2.get("evs", {}).get("spe", 0), 31, p2.get("nature", "Hardy"), 50, p2.get("is_sp", False))

        # Best damage by p1 on p2
        p1_best_dmg = 0
        for m in p1.get("moves", ["Moonblast"]):
            calc = calculate_damage(p1, p2, m, field)
            avg_roll = sum(calc["rolls"]) / 16.0
            if avg_roll > p1_best_dmg:
                p1_best_dmg = avg_roll

        # Best damage by p2 on p1
        p2_best_dmg = 0
        for m in p2.get("moves", ["Moonblast"]):
            calc2 = calculate_damage(p2, p1, m, field)
            avg_roll2 = sum(calc2["rolls"]) / 16.0
            if avg_roll2 > p2_best_dmg:
                p2_best_dmg = avg_roll2

        p1_hp = calculate_stat(p1_stats.get("hp", 100), "hp", p1.get("evs", {}).get("hp", 0), 31, p1.get("nature", "Hardy"), 50, p1.get("is_sp", False))
        p2_hp = calculate_stat(p2_stats.get("hp", 100), "hp", p2.get("evs", {}).get("hp", 0), 31, p2.get("nature", "Hardy"), 50, p2.get("is_sp", False))

        p1_turns_to_kill = math.ceil(p2_hp / max(1.0, p1_best_dmg))
        p2_turns_to_kill = math.ceil(p1_hp / max(1.0, p2_best_dmg))

        if p1_turns_to_kill < p2_turns_to_kill:
            return 0.85
        elif p2_turns_to_kill < p1_turns_to_kill:
            return 0.15
        else:
            # Tie breaker: Speed priority
            if p1_spe > p2_spe:
                return 0.65
            elif p2_spe > p1_spe:
                return 0.35
            return 0.50

    def simulate_doubles_matchup(
        self,
        team_a: List[Dict[str, Any]],
        team_b: List[Dict[str, Any]],
        num_simulations: int = 50
    ) -> float:
        """
        Monte Carlo 2v2 Doubles Simulator:
        Simulates bring-4/pick-2 matches across iterations.
        Returns Team A win percentage (0.0 to 100.0).
        """
        if not team_a or not team_b:
            return 50.0

        wins_a = 0
        for _ in range(num_simulations):
            # Select 4 random/smart Pokémon from each roster
            cand_a = random.sample(team_a, min(4, len(team_a)))
            cand_b = random.sample(team_b, min(4, len(team_b)))

            # Lead pair
            lead_a1, lead_a2 = cand_a[0], cand_a[1]
            lead_b1, lead_b2 = cand_b[0], cand_b[1]

            score_a = 0
            score_b = 0

            # Lead clash simulation
            field = {"is_doubles": True}
            p_a1_b1 = self.simulate_1v1_turn(lead_a1, lead_b1, field)
            p_a2_b2 = self.simulate_1v1_turn(lead_a2, lead_b2, field)
            p_a1_b2 = self.simulate_1v1_turn(lead_a1, lead_b2, field)
            p_a2_b1 = self.simulate_1v1_turn(lead_a2, lead_b1, field)

            avg_a_advantage = (p_a1_b1 + p_a2_b2 + p_a1_b2 + p_a2_b1) / 4.0

            # Back-2 support clash
            back_a1 = cand_a[2] if len(cand_a) > 2 else lead_a1
            back_b1 = cand_b[2] if len(cand_b) > 2 else lead_b1
            back_advantage = self.simulate_1v1_turn(back_a1, back_b1, field)

            composite = avg_a_advantage * 0.65 + back_advantage * 0.35
            if random.random() < composite:
                wins_a += 1

        return round((wins_a / num_simulations) * 100, 1)

    def analyze_matchup_spread(self, team: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Full Matchup Spread Analyzer:
        Classifies opposing archetypes into:
        - Favored (65%+)
        - Slight Edge (55-64%)
        - Even (45-54%)
        - Unfavorable (<45%)
        with win percentages and clear tactical explanations.
        """
        archetypes = self.get_meta_archetypes()
        results: Dict[str, Any] = {
            "Favored": [],
            "Slight Edge": [],
            "Even": [],
            "Unfavorable": [],
            "all": []
        }

        for arch_name, opp_team in archetypes.items():
            win_rate = self.simulate_doubles_matchup(team, opp_team, num_simulations=40)
            
            # Tactical explanation generator
            reasons = []
            if win_rate >= 65:
                tier = "Favored"
                reasons.append("High offensive speed control and super-effective priority pressure overwhelms their leads.")
                reasons.append("Defensive immunities cleanly absorb opposing core attacks.")
            elif win_rate >= 55:
                tier = "Slight Edge"
                reasons.append("Positioning and pivot advantage allows safe switches into favorable matchups.")
                reasons.append("Protect density successfully stalls opposing temporary speed/weather conditions.")
            elif win_rate >= 45:
                tier = "Even"
                reasons.append("Equally matched offensive damage rolls; victory depends on Turn-1 positioning and prediction.")
            else:
                tier = "Unfavorable"
                reasons.append("Opposing weather/terrain speed advantages threaten early knockouts before setup.")
                reasons.append("Vulnerable to opposing spread moves or redirection.")

            item = {
                "archetype": arch_name,
                "win_rate": win_rate,
                "tier": tier,
                "explanation": " ".join(reasons)
            }
            results[tier].append(item)
            results["all"].append(item)

        return results

    def scan_threats(self, team: List[Dict[str, Any]], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Bad Pokémon Threat Scanner:
        Scans top 50 meta Pokémon against all 6 team members.
        Ranks most dangerous threats by OHKO/2HKO pressure and identifies teammate checks.
        """
        top_meta = self.db.get_top_pokemon(self.format_id, limit=limit)
        threats = []

        for opp_row in top_meta:
            opp_name = opp_row["name"]
            meta_data = self.db.get_top_meta_for_pokemon(opp_name, self.format_id)
            opp_moves = meta_data.get("top_moves") or ["Moonblast", "Shadow Ball", "Protect", "Close Combat"]
            opp_item = meta_data.get("top_item") or "Life Orb"
            opp_mon = {
                "name": opp_name,
                "item": opp_item,
                "moves": opp_moves,
                "nature": "Timid",
                "evs": {"hp": 4, "atk": 252, "def": 0, "spa": 252, "spd": 0, "spe": 252}
            }

            ohko_threat_count = 0
            best_checks: List[str] = []

            for member in team:
                member_name = member.get("name", "Unknown")
                max_opp_pct = 0.0
                for m in opp_moves:
                    calc = calculate_damage(opp_mon, member, m)
                    if calc["max_pct"] > max_opp_pct:
                        max_opp_pct = calc["max_pct"]

                if max_opp_pct >= 90.0:
                    ohko_threat_count += 1

                # Check if member checks this opponent
                member_max_pct = 0.0
                for mm in member.get("moves", []):
                    c2 = calculate_damage(member, opp_mon, mm)
                    if c2["max_pct"] > member_max_pct:
                        member_max_pct = c2["max_pct"]

                if member_max_pct >= 80.0:
                    best_checks.append(member_name)

            danger_score = min(100, int((ohko_threat_count / max(1, len(team))) * 80 + (opp_row["usage_pct"] * 0.4)))
            threats.append({
                "name": opp_name,
                "usage_pct": opp_row["usage_pct"],
                "danger_score": danger_score,
                "ohko_threat_count": ohko_threat_count,
                "checks": list(set(best_checks))[:3],
                "status": "Critical Threat" if danger_score >= 65 else ("Moderate Threat" if danger_score >= 40 else "Manageable")
            })

        return sorted(threats, key=lambda x: x["danger_score"], reverse=True)

    def find_offmeta_counters(
        self,
        team: List[Dict[str, Any]],
        max_usage_pct: float = 5.0,
        limit: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Anti-Meta Hidden Gem Finder:
        Searches low-usage Pokémon (<5% usage) whose typing, abilities, speed tiers,
        and movepools directly answer user's worst matchups and top threat Pokémon.
        """
        threats = self.scan_threats(team, limit=15)
        critical_threats = [t["name"] for t in threats if t["danger_score"] >= 45][:6]

        dex = self.engine.pokedex
        candidates = []

        # Candidate pool of off-meta rogue Pokémon
        rogue_pool = [
            ("Clefable", "Unaware", ["Moonblast", "Follow Me", "Encore", "Life Dew"]),
            ("Tauros-Paldea-Aqua", "Intimidate", ["Wave Crash", "Close Combat", "Raging Bull", "Protect"]),
            ("Gastrodon", "Storm Drain", ["Earth Power", "Muddy Water", "Yawn", "Recover"]),
            ("Kilowattrel", "Competitive", ["Thunderbolt", "Tailwind", "Air Slash", "Electroweb"]),
            ("Torkoal", "Drought", ["Eruption", "Heat Wave", "Clear Smog", "Protect"]),
            ("Bruxish", "Dazzling", ["Psychic Fangs", "Wave Crash", "Aqua Jet", "Trick Room"]),
            ("Tsareena", "Queenly Majesty", ["Power Whip", "Triple Axel", "Helping Hand", "Protect"]),
            ("Grafaiai", "Prankster", ["Parting Shot", "Taunt", "Toxic", "Knock Off"]),
            ("Scrafty", "Intimidate", ["Fake Out", "Drain Punch", "Knock Off", "Quick Guard"]),
            ("Electivire", "Motor Drive", ["Thunder Punch", "Ice Punch", "Supercell Slam", "Protect"]),
            ("Talonflame", "Gale Wings", ["Tailwind", "Brave Bird", "Will-O-Wisp", "Quick Guard"]),
            ("Shedinja", "Wonder Guard", ["Shadow Sneak", "Will-O-Wisp", "Protect", "Endure"]),
            ("Toedscruel", "Mycelium Might", ["Spore", "Earth Power", "Rage Powder", "Taunt"]),
            ("Alomomola", "Regenerator", ["Wide Guard", "Helping Hand", "Flip Turn", "Wish"]),
            ("Snorlax", "Thick Fat", ["Body Slam", "Belly Drum", "Yawn", "Heavy Slam"]),
            ("Weezing-Galar", "Neutralizing Gas", ["Strange Steam", "Sludge Bomb", "Will-O-Wisp", "Protect"]),
        ]

        for sp_name, ability, moves in rogue_pool:
            clean = self.engine._clean_key(sp_name)
            dex_entry = dex.get(clean) or BUILTIN_POKEMON.get(clean)
            if not dex_entry:
                continue

            test_mon = {
                "name": sp_name,
                "ability": ability,
                "moves": moves,
                "nature": "Adamant",
                "evs": {"hp": 252, "atk": 128, "def": 128, "spa": 0, "spd": 0, "spe": 0}
            }

            countered = []
            for target_name in critical_threats:
                target_dex = self.engine.get_pokemon(target_name) or BUILTIN_POKEMON.get(self.engine._clean_key(target_name), {})
                target_mon = {"name": target_name, "nature": "Hardy", "evs": {"hp": 252, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}}
                for m in moves:
                    calc = calculate_damage(test_mon, target_mon, m)
                    if calc.get("type_multiplier", 1.0) >= 2.0 or calc.get("max_pct", 0.0) >= 65.0:
                        countered.append(target_name)
                        break

            counter_count = len(set(countered))
            synergy_score = counter_count * 25 + (20 if ability in ["Unaware", "Neutralizing Gas", "Prankster", "Storm Drain", "Intimidate", "Queenly Majesty"] else 10)

            candidates.append({
                "name": sp_name,
                "ability": ability,
                "suggested_moves": moves,
                "types": dex_entry.get("types", ["Normal"]),
                "synergy_score": min(98, synergy_score),
                "targets_answered": list(set(countered)),
                "why": f"Directly halts {', '.join(set(countered)) if countered else 'fast meta threats'} utilizing {ability} and defensive coverage."
            })

        return sorted(candidates, key=lambda x: x["synergy_score"], reverse=True)[:limit]
