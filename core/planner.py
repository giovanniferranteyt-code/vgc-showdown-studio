"""
VGC & Showdown Studio - Team Analytics, Gameplan Engine & EV Benchmark Optimizer
Computes Team Report Card, Dynamic Bo3 Gameplans, and solves defensive/offensive meta benchmarks.
"""

from __future__ import annotations
import copy
import math
from typing import Any, Dict, List, Optional, Tuple

from core.mechanics import (
    ShowdownEngine,
    calculate_damage,
    calculate_stat,
    get_nature_mult,
    resolve_form_change,
    BUILTIN_POKEMON,
    BUILTIN_MOVES,
    TYPE_CHART
)
from scrapers.meta_fetcher import MetaDatabase

# ==========================================
# Team Analytics Engine (Report Card)
# ==========================================
class TeamAnalyticsEngine:
    def __init__(self, format_id: str = "gen9vgc2024regg"):
        self.format_id = format_id
        self.engine = ShowdownEngine.get_instance()
        self.db = MetaDatabase.get_instance()

    def generate_report_card(self, team: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Computes a complete multi-dimensional Team Report Card."""
        if not team:
            return self._empty_report_card()

        # 1. Type Cores & Synergy Score
        all_types = set()
        for m in team:
            mon_data = self.engine.get_pokemon(m.get("name", "")) or BUILTIN_POKEMON.get(self.engine._clean_key(m.get("name", "")), {})
            for t in mon_data.get("types", []):
                all_types.add(t)

        fwg_core = ("Fire" in all_types and "Water" in all_types and "Grass" in all_types)
        dfs_core = ("Dragon" in all_types and "Fairy" in all_types and "Steel" in all_types)
        immunities = {
            "Ground": ("Flying" in all_types),
            "Electric": ("Ground" in all_types),
            "Ghost": ("Normal" in all_types),
            "Dragon": ("Fairy" in all_types),
            "Poison": ("Steel" in all_types),
            "Psychic": ("Dark" in all_types)
        }
        immunity_count = sum(1 for v in immunities.values() if v)

        # Offensive Coverage: count unique types hit super-effectively
        covered_types = set()
        for m in team:
            for move_name in m.get("moves", []):
                mv = self.engine.get_move(move_name) or BUILTIN_MOVES.get(self.engine._clean_key(move_name), {})
                m_type = mv.get("type", "Normal")
                for def_t, mult in TYPE_CHART.get(m_type, {}).items():
                    if mult > 1.0:
                        covered_types.add(def_t)

        coverage_ratio = len(covered_types) / 18.0

        # Base Synergy Score (0-100)
        synergy_score = int(
            (25 if fwg_core else 10) +
            (25 if dfs_core else 10) +
            min(25, immunity_count * 5) +
            (coverage_ratio * 25)
        )
        synergy_score = min(100, max(20, synergy_score))

        # 2. Offensive vs Defensive Stat Profile
        offense_ratings = []
        defense_ratings = []
        phys_moves = 0
        spec_moves = 0
        speed_tiers = []

        for m in team:
            stats, _, _ = resolve_form_change(m.get("name", ""))
            atk = stats.get("atk", 100)
            spa = stats.get("spa", 100)
            hp  = stats.get("hp", 100)
            df  = stats.get("def", 100)
            spd = stats.get("spd", 100)
            spe = stats.get("spe", 100)

            offense_ratings.append(max(atk, spa))
            defense_ratings.append(hp * (df + spd) / 200.0)

            # Speed tier at Level 50
            spe_val = calculate_stat(spe, "spe", m.get("evs", {}).get("spe", 0), 31, m.get("nature", "Hardy"), 50, m.get("is_sp", False))
            speed_tiers.append({"name": m.get("name", ""), "speed": spe_val})

            for move_name in m.get("moves", []):
                mv = self.engine.get_move(move_name) or BUILTIN_MOVES.get(self.engine._clean_key(move_name), {})
                cat = mv.get("category", "")
                if cat == "Physical": phys_moves += 1
                elif cat == "Special": spec_moves += 1

        avg_offense = sum(offense_ratings) / max(1, len(offense_ratings))
        avg_defense = sum(defense_ratings) / max(1, len(defense_ratings))

        offense_index = min(100, int((avg_offense / 140.0) * 100))
        defense_index = min(100, int((avg_defense / 130.0) * 100))

        tot_moves = max(1, phys_moves + spec_moves)
        phys_pct = int((phys_moves / tot_moves) * 100)
        spec_pct = 100 - phys_pct

        # 3. Board Control & Disruption Index (0-100)
        tools_found = {
            "Turn-1 Disruption": [],
            "Lockdown & Denial": [],
            "Speed Control": [],
            "Pivoting": [],
            "Protection": []
        }

        fake_out_count = 0
        redirection_count = 0
        intimidate_count = 0
        lockdown_count = 0
        speed_control_count = 0
        pivot_count = 0
        protect_count = 0

        for m in team:
            name = m.get("name", "")
            ability = m.get("ability", "").lower()
            if ability == "intimidate":
                intimidate_count += 1
                tools_found["Turn-1 Disruption"].append(f"{name} (Intimidate)")

            for move_name in m.get("moves", []):
                ml = move_name.lower()
                if ml == "fake out":
                    fake_out_count += 1
                    tools_found["Turn-1 Disruption"].append(f"{name} (Fake Out)")
                elif ml in ["follow me", "rage powder"]:
                    redirection_count += 1
                    tools_found["Turn-1 Disruption"].append(f"{name} ({move_name})")
                elif ml in ["encore", "taunt", "spore", "yawn", "disable", "wide guard", "quick guard"]:
                    lockdown_count += 1
                    tools_found["Lockdown & Denial"].append(f"{name} ({move_name})")
                elif ml in ["tailwind", "trick room", "icy wind", "electroweb", "thunder wave", "scary face"]:
                    speed_control_count += 1
                    tools_found["Speed Control"].append(f"{name} ({move_name})")
                elif ml in ["parting shot", "u-turn", "volt switch", "flip turn", "shed tail", "chilly reception"]:
                    pivot_count += 1
                    tools_found["Pivoting"].append(f"{name} ({move_name})")
                elif ml in ["protect", "detect", "spiky shield", "silk trap", "burning bulwark", "kings shield", "king's shield"]:
                    protect_count += 1
                    tools_found["Protection"].append(f"{name} ({move_name})")

        board_control_score = min(100, int(
            min(30, (fake_out_count * 10 + redirection_count * 10 + intimidate_count * 10)) +
            min(25, lockdown_count * 8) +
            min(25, speed_control_count * 10) +
            min(20, pivot_count * 7)
        ))

        # 4. Pilot Difficulty Rating (1.0 - 5.0 Stars)
        # Based on positioning reliance, fragile sweepers, and setup requirements
        fragile_count = sum(1 for m in team if (self.engine.get_pokemon(m.get("name", "")) or {}).get("baseStats", {}).get("hp", 100) < 70)
        setup_moves = sum(1 for m in team for mv in m.get("moves", []) if mv.lower() in ["trick room", "tailwind", "swords dance", "nasty plot", "belly drum"])
        
        difficulty_val = 1.5 + (0.5 if speed_control_count > 0 else 1.0) + (0.4 * fragile_count) + (0.3 * setup_moves) - (0.2 * protect_count)
        difficulty_stars = max(1.0, min(5.0, round(difficulty_val, 1)))

        if difficulty_stars <= 2.2:
            difficulty_label = "Accessible Hyper Offense"
        elif difficulty_stars <= 3.4:
            difficulty_label = "Balanced Tactical Positioning"
        elif difficulty_stars <= 4.2:
            difficulty_label = "High-Skill Pivot & Condition Control"
        else:
            difficulty_label = "Master-Tier Setup Dependent"

        # 5. CTS Surprise vs OTS Bo3 Resiliency
        cts_points = 25
        ots_points = 45

        # CTS rewards surprise tech
        surprise_items = ["Eject Pack", "Room Service", "Iron Ball", "Weakness Policy", "Covert Cloak", "Red Card"]
        for m in team:
            if m.get("item") in surprise_items:
                cts_points += 12
            if any(mv.lower() in ["wide guard", "quick guard", "gravity", "hypnosis", "imprison", "encore"] for mv in m.get("moves", [])):
                cts_points += 8

        # OTS rewards pivots, Protect count, and high natural bulk
        ots_points += min(25, protect_count * 5)
        ots_points += min(20, pivot_count * 7)
        ots_points += min(15, (avg_defense / 130.0) * 15)

        cts_surprise = min(100, max(20, int(cts_points)))
        ots_resiliency = min(100, max(25, int(ots_points)))

        return {
            "synergy_score": synergy_score,
            "fwg_core": fwg_core,
            "dfs_core": dfs_core,
            "immunities": immunities,
            "coverage_types_count": len(covered_types),
            "offense_pressure": offense_index,
            "defense_bulk": defense_index,
            "physical_ratio": phys_pct,
            "special_ratio": spec_pct,
            "speed_tiers": sorted(speed_tiers, key=lambda x: x["speed"], reverse=True),
            "pilot_difficulty_stars": difficulty_stars,
            "pilot_difficulty_label": difficulty_label,
            "board_control_score": board_control_score,
            "tools_found": tools_found,
            "protect_count": protect_count,
            "cts_surprise_score": cts_surprise,
            "ots_resiliency_score": ots_resiliency,
        }

    def _empty_report_card(self) -> Dict[str, Any]:
        return {
            "synergy_score": 0, "fwg_core": False, "dfs_core": False, "immunities": {}, "coverage_types_count": 0,
            "offense_pressure": 0, "defense_bulk": 0, "physical_ratio": 50, "special_ratio": 50,
            "speed_tiers": [], "pilot_difficulty_stars": 1.0, "pilot_difficulty_label": "Unassigned Roster",
            "board_control_score": 0, "tools_found": {}, "protect_count": 0,
            "cts_surprise_score": 0, "ots_resiliency_score": 0
        }

# ==========================================
# Dynamic Team Gameplan Engine
# ==========================================
class TeamGameplanEngine:
    def __init__(self, format_id: str = "gen9vgc2024regg"):
        self.format_id = format_id
        self.analytics = TeamAnalyticsEngine(format_id)

    def generate_overall_plan(self, team: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates Overall Team Plan, Lead Pairs, Bo3 adaptations, and counter-gameplans."""
        if not team or len(team) < 2:
            return {
                "primary_win_con": "Fill all 6 roster slots to generate tactical team gameplans.",
                "secondary_win_con": "N/A",
                "speed_control_plan": "N/A",
                "leads": [],
                "bo3_adaptations": [],
                "counter_gameplans": []
            }

        report = self.analytics.generate_report_card(team)
        names = [m.get("name", "Unknown") for m in team]

        # Identify speed controllers & sweepers
        speed_mon = None
        for m in team:
            if any(mv.lower() in ["tailwind", "trick room", "icy wind", "electroweb"] for mv in m.get("moves", [])):
                speed_mon = m.get("name")
                break

        primary_sweeper = report["speed_tiers"][0]["name"] if report["speed_tiers"] else names[0]
        secondary_sweeper = report["speed_tiers"][1]["name"] if len(report["speed_tiers"]) > 1 else names[-1]

        # Top 3 Lead Pairs with Turn-1 script & Back-2 recommendations
        lead_pairs = []
        if len(names) >= 4:
            lead_pairs.append({
                "pair": (names[0], names[1]),
                "name": "Standard Pressure / Momentum Lead",
                "turn1_script": f"Turn 1: {names[0]} pressures with Fake Out or Parting Shot disruption while {names[1]} positions attacks or sets speed control.",
                "back2": [names[2] if len(names) > 2 else names[0], names[3] if len(names) > 3 else names[1]],
                "preferred_against": "Standard Balance & Goodstuffs cores."
            })
            lead_pairs.append({
                "pair": (names[2] if len(names) > 2 else names[0], names[3] if len(names) > 3 else names[1]),
                "name": "Defensive Pivot & Redirection Lead",
                "turn1_script": "Turn 1: Absorb opposing offensive priority with redirection/pivots to protect your endgame sweepers.",
                "back2": [names[0], names[1]],
                "preferred_against": "Hyper Offense, Psyspam, and Choice Band/Specs leads."
            })
            lead_pairs.append({
                "pair": (names[0], names[-1]),
                "name": "Rogue Surprise Tech Lead",
                "turn1_script": "Turn 1: Activate surprise positioning or unexpected coverage to claim an early 4v3 board state.",
                "back2": [names[1], names[2] if len(names) > 2 else names[0]],
                "preferred_against": "Unfamiliar or rogue tournament setups."
            })

        # Bo3 Adaptations (Game 2 & Game 3)
        bo3_adaptations = [
            {
                "phase": "Game 2 Adjustment (When opponent adapts to your Game 1 tech)",
                "advice": (
                    "In Open Team Sheet (OTS) play, the opponent will predict your primary Turn-1 move. "
                    "If they lead Protect or Fake Out anticipation, pivot your primary lead to the bench and start with your back-2 pivots "
                    "to bait their Tera commitment on Turn 1."
                )
            },
            {
                "phase": "Game 3 Decider (High-pressure positioning)",
                "advice": (
                    "Rely strictly on natural defensive bulk and Protect turns. "
                    "Do not rush Tera early: preserve Terastallization for your primary endgame sweeper once their main counter is removed."
                )
            }
        ]

        # Specific Counter-Gameplans
        counter_gameplans = [
            {
                "matchup": "Vs. Rain Hyper Offense (Pelipper + Archaludon / Urshifu)",
                "gameplan": (
                    "Deny Weather Ball / Electro Shot momentum. "
                    "Lead your Grass/Electric core to threaten immediate OHKO on Pelipper before Tailwind can be established."
                )
            },
            {
                "matchup": "Vs. Trick Room Psyspam (Indeedee-F + Armarouge / Ursaluna)",
                "gameplan": (
                    "Psychic Surge prevents Fake Out priority. Lead Wide Guard or Dark/Steel pivot to deny Expanding Force spread damage, "
                    "or stall the 5 turns of Trick Room with staggered Protects."
                )
            },
            {
                "matchup": "Vs. Hyper Sun (Torkoal + Chi-Yu / Koraidon)",
                "gameplan": (
                    "Preserve Fire resistances and use Snarl / Parting Shot to soften incoming Eruptions and Heat Waves."
                )
            }
        ]

        return {
            "primary_win_con": f"Establish board control with {speed_mon or 'positioning pivots'} and sweep with {primary_sweeper}.",
            "secondary_win_con": f"Defensively stall opposing temporary conditions and clean up with {secondary_sweeper}.",
            "speed_control_plan": f"Utilize {speed_mon or 'priority attacks and speed-crept spreads'} to dictate turn order.",
            "leads": lead_pairs,
            "bo3_adaptations": bo3_adaptations,
            "counter_gameplans": counter_gameplans
        }

# ==========================================
# EV / SP Benchmark Optimizer
# ==========================================
class EVBenchmarkOptimizer:
    """
    Solves both:
    - Defensive survival benchmarks (min HP + Def/SpD EVs or 0-32 SP to survive 16/16 rolls).
    - Offensive meta-punish benchmarks:
      * Minimum Speed EVs/SP to creep +1 above target's most common tournament spread.
      * Minimum Atk/SpA EVs/SP to 16/16 OHKO target's standard tournament bulk spread.
    """

    def __init__(self, format_id: str = "gen9vgc2024regg"):
        self.format_id = format_id
        self.engine = ShowdownEngine.get_instance()
        self.db = MetaDatabase.get_instance()

    def optimize_defensive_survival(
        self,
        defender: Dict[str, Any],
        attacker_species: str,
        attacker_move: str,
        attacker_item: str = "Life Orb",
        attacker_nature: str = "Adamant",
        field: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Finds the exact minimum HP + Def (or SpD) EVs (or Champions SPs)
        so that defender survives 16 out of 16 damage rolls.
        """
        field = field or {}
        is_sp = defender.get("is_sp", False)
        move_data = self.engine.get_move(attacker_move) or BUILTIN_MOVES.get(self.engine._clean_key(attacker_move), BUILTIN_MOVES["shadowball"])
        is_phys = (move_data.get("category") == "Physical")
        stat_key = "def" if is_phys else "spd"

        # Build attacker dict
        att_dict = {
            "name": attacker_species,
            "item": attacker_item,
            "nature": attacker_nature,
            "evs": {"hp": 4, "atk": 252, "def": 0, "spa": 252, "spd": 0, "spe": 252},
            "level": 50,
            "is_sp": False
        }

        # Step search
        best_hp = 0
        best_def = 0
        survived = False

        if is_sp:
            # Champions format: 0 to 32 SP, max sum 66
            for hp_sp in range(0, 33, 2):
                for def_sp in range(0, 33, 2):
                    if (hp_sp + def_sp) > 66:
                        continue
                    test_def = copy.deepcopy(defender)
                    test_def["evs"]["hp"] = hp_sp
                    test_def["evs"][stat_key] = def_sp
                    calc = calculate_damage(att_dict, test_def, attacker_move, field)
                    if calc["max_damage"] < calc["defender_hp"]:
                        best_hp = hp_sp
                        best_def = def_sp
                        survived = True
                        break
                if survived:
                    break
        else:
            # Mainline format: 0 to 252 EVs, step 8
            for hp_ev in range(0, 253, 8):
                for def_ev in range(0, 253, 8):
                    if (hp_ev + def_ev) > 508:
                        continue
                    test_def = copy.deepcopy(defender)
                    test_def["evs"]["hp"] = hp_ev
                    test_def["evs"][stat_key] = def_ev
                    calc = calculate_damage(att_dict, test_def, attacker_move, field)
                    if calc["max_damage"] < calc["defender_hp"]:
                        best_hp = hp_ev
                        best_def = def_ev
                        survived = True
                        break
                if survived:
                    break

        unit = "SP" if is_sp else "EVs"
        if survived:
            msg = f"Guaranteed Survival (16/16 rolls) achieved with: {best_hp} HP {unit} / {best_def} {stat_key.upper()} {unit}."
        else:
            msg = f"Attack is too devastating: cannot survive 100% of rolls without defensive Terastallization or screens."

        return {
            "survived": survived,
            "hp_needed": best_hp,
            "defense_stat_needed": best_def,
            "defense_stat_name": stat_key.upper(),
            "is_sp": is_sp,
            "explanation": msg
        }

    def optimize_speed_creep(
        self,
        user_pokemon: Dict[str, Any],
        target_species: str
    ) -> Dict[str, Any]:
        """
        Calculates exact minimum Speed EVs/SP to creep +1 Speed above
        the target's most common tournament spread in vgc_meta.db.
        """
        is_sp = user_pokemon.get("is_sp", False)
        target_meta = self.db.get_top_meta_for_pokemon(target_species, self.format_id)
        target_spread = target_meta.get("top_spread") or {"nature": "Jolly", "evs": {"spe": 252}, "is_sp": False}

        target_stats, _, _ = resolve_form_change(target_species)
        target_base_spe = target_stats.get("spe", 100)
        target_spe_val = calculate_stat(
            target_base_spe, "spe",
            target_spread.get("evs", {}).get("spe", 0), 31,
            target_spread.get("nature", "Hardy"), 50,
            target_spread.get("is_sp", False)
        )

        desired_speed = target_spe_val + 1

        user_stats, _, _ = resolve_form_change(user_pokemon.get("name", ""))
        user_base_spe = user_stats.get("spe", 100)
        user_nature = user_pokemon.get("nature", "Hardy")

        # Find min EV/SP
        found_ev = None
        max_points = 32 if is_sp else 252
        step = 1 if is_sp else 4

        for spe_points in range(0, max_points + 1, step):
            calc_val = calculate_stat(user_base_spe, "spe", spe_points, 31, user_nature, 50, is_sp)
            if calc_val >= desired_speed:
                found_ev = spe_points
                break

        # Check with speed-boosting nature if neutral couldn't reach
        nature_needed = user_nature
        if found_ev is None:
            nature_needed = "Timid" if user_stats.get("spa", 0) > user_stats.get("atk", 0) else "Jolly"
            for spe_points in range(0, max_points + 1, step):
                calc_val = calculate_stat(user_base_spe, "spe", spe_points, 31, nature_needed, 50, is_sp)
                if calc_val >= desired_speed:
                    found_ev = spe_points
                    break

        unit = "SP" if is_sp else "EVs"
        can_outspeed = (found_ev is not None)

        if can_outspeed:
            desc = f"Requires {found_ev} {unit} in Speed ({nature_needed} Nature) to reach {desired_speed} Spe (+1 above standard {target_species})."
        else:
            desc = f"{user_pokemon.get('name', 'User')} base speed ({user_base_spe}) is too low to outspeed standard {target_species} ({target_spe_val} Spe) without Tailwind or Choice Scarf."

        return {
            "can_outspeed": can_outspeed,
            "target_speed": target_spe_val,
            "desired_speed": desired_speed,
            "spe_needed": found_ev if found_ev is not None else 0,
            "nature_needed": nature_needed,
            "is_sp": is_sp,
            "desc": desc
        }

    def optimize_ohko_punish(
        self,
        attacker: Dict[str, Any],
        target_species: str,
        move_name: str
    ) -> Dict[str, Any]:
        """
        Solves minimum Attack or Sp. Atk EVs/SP to guarantee a 16/16 OHKO
        on target's standard tournament bulk spread.
        """
        is_sp = attacker.get("is_sp", False)
        target_meta = self.db.get_top_meta_for_pokemon(target_species, self.format_id)
        target_spread = target_meta.get("top_spread") or {"nature": "Careful", "evs": {"hp": 252, "def": 124, "spd": 124}, "is_sp": False}

        target_defender = {
            "name": target_species,
            "item": target_meta.get("top_item") or "Sitrus Berry",
            "nature": target_spread.get("nature", "Hardy"),
            "evs": target_spread.get("evs", {"hp": 252, "def": 124, "spd": 124}),
            "level": 50,
            "is_sp": target_spread.get("is_sp", False)
        }

        move_data = self.engine.get_move(move_name) or BUILTIN_MOVES.get(self.engine._clean_key(move_name), BUILTIN_MOVES["shadowball"])
        is_phys = (move_data.get("category") == "Physical")
        atk_stat_key = "atk" if is_phys else "spa"

        max_points = 32 if is_sp else 252
        step = 1 if is_sp else 4

        found_ev = None
        user_nature = attacker.get("nature", "Hardy")

        # Test current nature first
        for points in range(0, max_points + 1, step):
            test_att = copy.deepcopy(attacker)
            test_att["evs"][atk_stat_key] = points
            calc = calculate_damage(test_att, target_defender, move_name)
            if calc["ohko_chance"] >= 100.0:
                found_ev = points
                break

        # Test +Atk / +SpA nature if neutral didn't achieve 100% OHKO
        nature_needed = user_nature
        if found_ev is None:
            nature_needed = "Adamant" if is_phys else "Modest"
            for points in range(0, max_points + 1, step):
                test_att = copy.deepcopy(attacker)
                test_att["nature"] = nature_needed
                test_att["evs"][atk_stat_key] = points
                calc = calculate_damage(test_att, target_defender, move_name)
                if calc["ohko_chance"] >= 100.0:
                    found_ev = points
                    break

        unit = "SP" if is_sp else "EVs"
        can_ohko = (found_ev is not None)

        if can_ohko:
            desc = f"Guaranteed 16/16 OHKO on standard tournament {target_species} with {found_ev} {atk_stat_key.upper()} {unit} ({nature_needed} Nature)."
        else:
            desc = f"Cannot guarantee 100% OHKO on tournament bulk {target_species} without offensive stat boosts (Choice Specs/Band, Terastallization, or Life Orb)."

        return {
            "can_ohko": can_ohko,
            "points_needed": found_ev if found_ev is not None else 0,
            "stat_name": atk_stat_key.upper(),
            "nature_needed": nature_needed,
            "is_sp": is_sp,
            "desc": desc
        }
