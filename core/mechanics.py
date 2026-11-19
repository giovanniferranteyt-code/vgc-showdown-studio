"""
VGC & Showdown Studio - Core Mechanics Engine
Engineered for all past, current, and future Pokémon generations and formats.
"""

from __future__ import annotations
import os
import sys
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

APP_VERSION = "1.0.0"

def get_base_dir() -> Path:
    """Resolve base directory safely for both frozen exe and script environments."""
    if getattr(sys, "frozen", False):
        parent = Path(sys.executable).parent
        if (parent / "data").exists():
            return parent
        if (parent / "_internal" / "data").exists():
            return parent / "_internal"
        return parent
    return Path(__file__).resolve().parent.parent

def get_data_dir() -> Path:
    d = get_base_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d

# ==========================================
# 18-Type Matchup Chart
# ==========================================
ALL_TYPES = [
    "Normal", "Fire", "Water", "Grass", "Electric", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Steel", "Dark", "Fairy", "Stellar"
]

TYPE_CHART: Dict[str, Dict[str, float]] = {
    "Normal":   {"Rock": 0.5, "Ghost": 0.0, "Steel": 0.5},
    "Fire":     {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 2.0, "Bug": 2.0, "Rock": 0.5, "Dragon": 0.5, "Steel": 2.0},
    "Water":    {"Fire": 2.0, "Water": 0.5, "Grass": 0.5, "Ground": 2.0, "Rock": 2.0, "Dragon": 0.5},
    "Grass":    {"Fire": 0.5, "Water": 2.0, "Grass": 0.5, "Poison": 0.5, "Ground": 2.0, "Flying": 0.5, "Bug": 0.5, "Rock": 2.0, "Dragon": 0.5, "Steel": 0.5},
    "Electric": {"Water": 2.0, "Grass": 0.5, "Electric": 0.5, "Ground": 0.0, "Flying": 2.0, "Dragon": 0.5},
    "Ice":      {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 0.5, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Steel": 0.5},
    "Fighting": {"Normal": 2.0, "Ice": 2.0, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2.0, "Ghost": 0.0, "Dark": 2.0, "Steel": 2.0, "Fairy": 0.5},
    "Poison":   {"Grass": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0.0, "Fairy": 2.0},
    "Ground":   {"Fire": 2.0, "Grass": 0.5, "Electric": 2.0, "Poison": 2.0, "Flying": 0.0, "Bug": 0.5, "Rock": 2.0, "Steel": 2.0},
    "Flying":   {"Grass": 2.0, "Electric": 0.5, "Fighting": 2.0, "Bug": 2.0, "Rock": 0.5, "Steel": 0.5},
    "Psychic":  {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Dark": 0.0, "Steel": 0.5},
    "Bug":      {"Fire": 0.5, "Grass": 2.0, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Psychic": 2.0, "Ghost": 0.5, "Dark": 2.0, "Steel": 0.5, "Fairy": 0.5},
    "Rock":     {"Fire": 2.0, "Ice": 2.0, "Fighting": 0.5, "Ground": 0.5, "Flying": 2.0, "Bug": 2.0, "Steel": 0.5},
    "Ghost":    {"Normal": 0.0, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5},
    "Dragon":   {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
    "Steel":    {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2.0, "Rock": 2.0, "Steel": 0.5, "Fairy": 2.0},
    "Dark":     {"Fighting": 0.5, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Fairy": 0.5},
    "Fairy":    {"Fire": 0.5, "Fighting": 2.0, "Poison": 0.5, "Dragon": 2.0, "Dark": 2.0, "Steel": 0.5},
    "Stellar":  {}
}

def get_type_effectiveness(attack_type: str, defender_types: List[str]) -> float:
    """Calculate offensive type effectiveness multiplier against 1 or 2 defender types."""
    if not attack_type or attack_type == "Stellar":
        return 1.2 if attack_type == "Stellar" else 1.0
    mult = 1.0
    chart = TYPE_CHART.get(attack_type, {})
    for def_t in defender_types:
        if not def_t:
            continue
        mult *= chart.get(def_t, 1.0)
    return mult

# ==========================================
# Nature Modifiers
# ==========================================
NATURES = {
    "Hardy":   {"plus": None, "minus": None},
    "Lonely":  {"plus": "atk", "minus": "def"},
    "Brave":   {"plus": "atk", "minus": "spe"},
    "Adamant": {"plus": "atk", "minus": "spa"},
    "Naughty": {"plus": "atk", "minus": "spd"},
    "Bold":    {"plus": "def", "minus": "atk"},
    "Docile":  {"plus": None, "minus": None},
    "Relaxed": {"plus": "def", "minus": "spe"},
    "Impish":  {"plus": "def", "minus": "spa"},
    "Lax":     {"plus": "def", "minus": "spd"},
    "Timid":   {"plus": "spe", "minus": "atk"},
    "Hasty":   {"plus": "spe", "minus": "def"},
    "Serious": {"plus": None, "minus": None},
    "Jolly":   {"plus": "spe", "minus": "spa"},
    "Naive":   {"plus": "spe", "minus": "spd"},
    "Modest":  {"plus": "spa", "minus": "atk"},
    "Mild":    {"plus": "spa", "minus": "def"},
    "Quiet":   {"plus": "spa", "minus": "spe"},
    "Bashful": {"plus": None, "minus": None},
    "Rash":    {"plus": "spa", "minus": "spd"},
    "Calm":    {"plus": "spd", "minus": "atk"},
    "Gentle":  {"plus": "spd", "minus": "def"},
    "Sassy":   {"plus": "spd", "minus": "spe"},
    "Careful": {"plus": "spd", "minus": "spa"},
    "Quirky":  {"plus": None, "minus": None},
}

def get_nature_mult(nature: str, stat_name: str) -> float:
    nat = NATURES.get(nature.capitalize() if nature else "Serious", NATURES["Serious"])
    if nat["plus"] == stat_name:
        return 1.1
    if nat["minus"] == stat_name:
        return 0.9
    return 1.0

# ==========================================
# Stat Calculation Engine (Classic EVs vs Champions SPs)
# ==========================================
def calculate_stat(
    base: int,
    stat_name: str,
    ev_or_sp: int = 0,
    iv: int = 31,
    nature: str = "Serious",
    level: int = 50,
    is_champions_sp: bool = False,
    is_shedinja: bool = False
) -> int:
    """
    Era-agnostic stat calculator:
    - Classic EVs/IVs: 0-252 EVs, 0-31 IVs.
    - Champions Stat Points: 0-32 SP per stat (sum <= 66).
    """
    stat_name = stat_name.lower()
    if stat_name == "hp" and is_shedinja:
        return 1

    nature_mult = get_nature_mult(nature, stat_name)

    if is_champions_sp:
        # In Pokémon Champions format:
        # Standard Level 50 scaling with Stat Points (0-32 SP):
        sp = max(0, min(32, int(ev_or_sp)))
        if stat_name == "hp":
            # HP = base + 75 + SP
            return int(base + 75 + sp)
        else:
            # Other = floor((base + 20 + SP) * nature_mult)
            return int(math.floor((base + 20 + sp) * nature_mult))
    else:
        # Classic Mainline / Smogon EVs/IVs formula:
        ev = max(0, min(252, int(ev_or_sp)))
        iv = max(0, min(31, int(iv)))
        if stat_name == "hp":
            return int(math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100) + level + 10)
        else:
            raw = math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100) + 5
            return int(math.floor(raw * nature_mult))

# ==========================================
# Fallback / Built-In Data Cache
# ==========================================
BUILTIN_POKEMON: Dict[str, Any] = {
    "incineroar": {"num": 727, "name": "Incineroar", "types": ["Fire", "Dark"], "baseStats": {"hp": 95, "atk": 115, "def": 90, "spa": 80, "spd": 90, "spe": 60}, "abilities": {"0": "Blaze", "H": "Intimidate"}, "weightkg": 83.0},
    "rillaboom": {"num": 812, "name": "Rillaboom", "types": ["Grass"], "baseStats": {"hp": 100, "atk": 125, "def": 90, "spa": 60, "spd": 70, "spe": 85}, "abilities": {"0": "Overgrow", "H": "Grassy Surge"}, "weightkg": 90.0},
    "fluttermane": {"num": 987, "name": "Flutter Mane", "types": ["Ghost", "Fairy"], "baseStats": {"hp": 55, "atk": 55, "def": 55, "spa": 135, "spd": 135, "spe": 135}, "abilities": {"0": "Protosynthesis"}, "weightkg": 4.0},
    "urshifurapidstrike": {"num": 892, "name": "Urshifu-Rapid-Strike", "types": ["Fighting", "Water"], "baseStats": {"hp": 100, "atk": 130, "def": 100, "spa": 63, "spd": 60, "spe": 97}, "abilities": {"0": "Unseen Fist"}, "weightkg": 105.0},
    "urshifu": {"num": 892, "name": "Urshifu", "types": ["Fighting", "Dark"], "baseStats": {"hp": 100, "atk": 130, "def": 100, "spa": 63, "spd": 60, "spe": 97}, "abilities": {"0": "Unseen Fist"}, "weightkg": 105.0},
    "kingambit": {"num": 983, "name": "Kingambit", "types": ["Dark", "Steel"], "baseStats": {"hp": 100, "atk": 135, "def": 120, "spa": 60, "spd": 85, "spe": 50}, "abilities": {"0": "Defiant", "1": "Supreme Overlord", "H": "Pressure"}, "weightkg": 120.0},
    "whimsicott": {"num": 547, "name": "Whimsicott", "types": ["Grass", "Fairy"], "baseStats": {"hp": 60, "atk": 67, "def": 85, "spa": 77, "spd": 75, "spe": 116}, "abilities": {"0": "Prankster", "1": "Infiltrator", "H": "Chlorophyll"}, "weightkg": 6.6},
    "archaludon": {"num": 1018, "name": "Archaludon", "types": ["Steel", "Dragon"], "baseStats": {"hp": 90, "atk": 105, "def": 130, "spa": 125, "spd": 65, "spe": 85}, "abilities": {"0": "Stamina", "1": "Sturdy", "H": "Drizzle"}, "weightkg": 60.0},
    "pelipper": {"num": 279, "name": "Pelipper", "types": ["Water", "Flying"], "baseStats": {"hp": 60, "atk": 50, "def": 100, "spa": 95, "spd": 70, "spe": 65}, "abilities": {"0": "Keen Eye", "1": "Drizzle", "H": "Rain Dish"}, "weightkg": 28.0},
    "torkoal": {"num": 324, "name": "Torkoal", "types": ["Fire"], "baseStats": {"hp": 70, "atk": 85, "def": 140, "spa": 85, "spd": 70, "spe": 20}, "abilities": {"0": "White Smoke", "1": "Drought", "H": "Shell Armor"}, "weightkg": 80.4},
    "chiyu": {"num": 1004, "name": "Chi-Yu", "types": ["Dark", "Fire"], "baseStats": {"hp": 55, "atk": 80, "def": 80, "spa": 135, "spd": 120, "spe": 100}, "abilities": {"0": "Beads of Ruin"}, "weightkg": 4.9},
    "chienpao": {"num": 1002, "name": "Chien-Pao", "types": ["Dark", "Ice"], "baseStats": {"hp": 80, "atk": 120, "def": 80, "spa": 90, "spd": 65, "spe": 135}, "abilities": {"0": "Sword of Ruin"}, "weightkg": 152.2},
    "tinglu": {"num": 1003, "name": "Ting-Lu", "types": ["Dark", "Ground"], "baseStats": {"hp": 155, "atk": 110, "def": 125, "spa": 55, "spd": 80, "spe": 45}, "abilities": {"0": "Vessel of Ruin"}, "weightkg": 699.7},
    "wochien": {"num": 1001, "name": "Wo-Chien", "types": ["Dark", "Grass"], "baseStats": {"hp": 85, "atk": 85, "def": 100, "spa": 95, "spd": 135, "spe": 70}, "abilities": {"0": "Tablets of Ruin"}, "weightkg": 74.2},
    "miraidon": {"num": 1008, "name": "Miraidon", "types": ["Electric", "Dragon"], "baseStats": {"hp": 100, "atk": 85, "def": 100, "spa": 135, "spd": 115, "spe": 135}, "abilities": {"0": "Hadron Engine"}, "weightkg": 240.0},
    "koraidon": {"num": 1007, "name": "Koraidon", "types": ["Fighting", "Dragon"], "baseStats": {"hp": 100, "atk": 135, "def": 115, "spa": 85, "spd": 100, "spe": 135}, "abilities": {"0": "Orichalcum Pulse"}, "weightkg": 303.0},
    "calyrexshadow": {"num": 898, "name": "Calyrex-Shadow", "types": ["Psychic", "Ghost"], "baseStats": {"hp": 100, "atk": 85, "def": 80, "spa": 165, "spd": 100, "spe": 150}, "abilities": {"0": "As One (Spectrier)"}, "weightkg": 53.6},
    "calyrexice": {"num": 898, "name": "Calyrex-Ice", "types": ["Psychic", "Ice"], "baseStats": {"hp": 100, "atk": 165, "def": 150, "spa": 85, "spd": 130, "spe": 50}, "abilities": {"0": "As One (Glastrier)"}, "weightkg": 809.1},
    "ogerponwellspring": {"num": 1017, "name": "Ogerpon-Wellspring", "types": ["Grass", "Water"], "baseStats": {"hp": 80, "atk": 120, "def": 84, "spa": 60, "spd": 96, "spe": 110}, "abilities": {"0": "Water Absorb"}, "weightkg": 39.8},
    "ogerponhearthflame": {"num": 1017, "name": "Ogerpon-Hearthflame", "types": ["Grass", "Fire"], "baseStats": {"hp": 80, "atk": 120, "def": 84, "spa": 60, "spd": 96, "spe": 110}, "abilities": {"0": "Mold Breaker"}, "weightkg": 39.8},
    "ogerponcornerstone": {"num": 1017, "name": "Ogerpon-Cornerstone", "types": ["Grass", "Rock"], "baseStats": {"hp": 80, "atk": 120, "def": 84, "spa": 60, "spd": 96, "spe": 110}, "abilities": {"0": "Sturdy"}, "weightkg": 39.8},
    "farigiraf": {"num": 981, "name": "Farigiraf", "types": ["Normal", "Psychic"], "baseStats": {"hp": 120, "atk": 90, "def": 70, "spa": 110, "spd": 70, "spe": 60}, "abilities": {"0": "Cud Chew", "1": "Armor Tail", "H": "Sap Sipper"}, "weightkg": 160.0},
    "ursalunabloodmoon": {"num": 901, "name": "Ursaluna-Bloodmoon", "types": ["Ground", "Normal"], "baseStats": {"hp": 113, "atk": 70, "def": 120, "spa": 135, "spd": 65, "spe": 52}, "abilities": {"0": "Mind's Eye"}, "weightkg": 333.0},
    "palafin": {"num": 964, "name": "Palafin", "types": ["Water"], "baseStats": {"hp": 100, "atk": 70, "def": 72, "spa": 53, "spd": 62, "spe": 100}, "abilities": {"0": "Zero to Hero"}, "weightkg": 60.2},
    "palafinhero": {"num": 964, "name": "Palafin-Hero", "types": ["Water"], "baseStats": {"hp": 100, "atk": 160, "def": 97, "spa": 106, "spd": 87, "spe": 100}, "abilities": {"0": "Zero to Hero"}, "weightkg": 97.4},
    "charizardmegay": {"num": 6, "name": "Charizard-Mega-Y", "types": ["Fire", "Flying"], "baseStats": {"hp": 78, "atk": 104, "def": 78, "spa": 159, "spd": 115, "spe": 100}, "abilities": {"0": "Drought"}, "weightkg": 100.5},
    "kangaskhanmega": {"num": 115, "name": "Kangaskhan-Mega", "types": ["Normal"], "baseStats": {"hp": 105, "atk": 125, "def": 100, "spa": 60, "spd": 100, "spe": 100}, "abilities": {"0": "Parental Bond"}, "weightkg": 100.0},
    "salamencemega": {"num": 373, "name": "Salamence-Mega", "types": ["Dragon", "Flying"], "baseStats": {"hp": 95, "atk": 145, "def": 130, "spa": 120, "spd": 90, "spe": 120}, "abilities": {"0": "Aerilate"}, "weightkg": 112.6},
    "gengarmega": {"num": 94, "name": "Gengar-Mega", "types": ["Ghost", "Poison"], "baseStats": {"hp": 60, "atk": 65, "def": 80, "spa": 170, "spd": 95, "spe": 130}, "abilities": {"0": "Shadow Tag"}, "weightkg": 40.5},
    "sneasler": {"num": 903, "name": "Sneasler", "types": ["Fighting", "Poison"], "baseStats": {"hp": 80, "atk": 130, "def": 60, "spa": 40, "spd": 80, "spe": 120}, "abilities": {"0": "Pressure", "1": "Unburden", "H": "Poison Touch"}, "weightkg": 43.0},
    "landorustherian": {"num": 645, "name": "Landorus-Therian", "types": ["Ground", "Flying"], "baseStats": {"hp": 89, "atk": 145, "def": 90, "spa": 105, "spd": 80, "spe": 91}, "abilities": {"0": "Intimidate"}, "weightkg": 68.0},
    "gholdengo": {"num": 1000, "name": "Gholdengo", "types": ["Steel", "Ghost"], "baseStats": {"hp": 87, "atk": 60, "def": 95, "spa": 133, "spd": 91, "spe": 84}, "abilities": {"0": "Good as Gold"}, "weightkg": 30.0},
    "armarouge": {"num": 936, "name": "Armarouge", "types": ["Fire", "Psychic"], "baseStats": {"hp": 85, "atk": 60, "def": 100, "spa": 125, "spd": 80, "spe": 75}, "abilities": {"0": "Flash Fire", "H": "Weak Armor"}, "weightkg": 85.0},
    "indeedee": {"num": 876, "name": "Indeedee-F", "types": ["Psychic", "Normal"], "baseStats": {"hp": 70, "atk": 55, "def": 65, "spa": 95, "spd": 105, "spe": 85}, "abilities": {"0": "Own Tempo", "1": "Synchronize", "H": "Psychic Surge"}, "weightkg": 28.0},
    "clefairy": {"num": 35, "name": "Clefairy", "types": ["Fairy"], "baseStats": {"hp": 70, "atk": 45, "def": 48, "spa": 60, "spd": 65, "spe": 35}, "abilities": {"0": "Cute Charm", "1": "Magic Guard", "H": "Friend Guard"}, "weightkg": 7.5},
    "amoonguss": {"num": 591, "name": "Amoonguss", "types": ["Grass", "Poison"], "baseStats": {"hp": 114, "atk": 85, "def": 70, "spa": 85, "spd": 80, "spe": 30}, "abilities": {"0": "Effect Spore", "H": "Regenerator"}, "weightkg": 10.5},
    "dondozo": {"num": 977, "name": "Dondozo", "types": ["Water"], "baseStats": {"hp": 150, "atk": 100, "def": 115, "spa": 65, "spd": 65, "spe": 35}, "abilities": {"0": "Unaware", "1": "Oblivious", "H": "Water Veil"}, "weightkg": 220.0},
    "tatsugiri": {"num": 978, "name": "Tatsugiri", "types": ["Dragon", "Water"], "baseStats": {"hp": 68, "atk": 50, "def": 60, "spa": 120, "spd": 95, "spe": 82}, "abilities": {"0": "Commander", "H": "Storm Drain"}, "weightkg": 8.0},
    "grimmsnarl": {"num": 861, "name": "Grimmsnarl", "types": ["Dark", "Fairy"], "baseStats": {"hp": 95, "atk": 120, "def": 65, "spa": 95, "spd": 75, "spe": 60}, "abilities": {"0": "Prankster", "1": "Frisk", "H": "Pickpocket"}, "weightkg": 61.0},
    "tornadus": {"num": 641, "name": "Tornadus", "types": ["Flying"], "baseStats": {"hp": 79, "atk": 115, "def": 70, "spa": 125, "spd": 80, "spe": 111}, "abilities": {"0": "Prankster", "H": "Defiant"}, "weightkg": 63.0},
    "dragonite": {"num": 149, "name": "Dragonite", "types": ["Dragon", "Flying"], "baseStats": {"hp": 91, "atk": 134, "def": 95, "spa": 100, "spd": 100, "spe": 80}, "abilities": {"0": "Inner Focus", "H": "Multiscale"}, "weightkg": 210.0},
    "terapagos": {"num": 1024, "name": "Terapagos", "types": ["Normal"], "baseStats": {"hp": 90, "atk": 65, "def": 85, "spa": 65, "spd": 85, "spe": 60}, "abilities": {"0": "Tera Shift"}, "weightkg": 6.5},
    "terapagosterastal": {"num": 1024, "name": "Terapagos-Terastal", "types": ["Normal"], "baseStats": {"hp": 95, "atk": 95, "def": 110, "spa": 105, "spd": 110, "spe": 85}, "abilities": {"0": "Tera Shell"}, "weightkg": 16.0},
    "terapagosstellar": {"num": 1024, "name": "Terapagos-Stellar", "types": ["Stellar"], "baseStats": {"hp": 160, "atk": 105, "def": 110, "spa": 130, "spd": 110, "spe": 85}, "abilities": {"0": "Teraform Zero"}, "weightkg": 77.0},
}

BUILTIN_MOVES: Dict[str, Any] = {
    "fakeout": {"name": "Fake Out", "basePower": 40, "type": "Normal", "category": "Physical", "priority": 3, "flags": {"contact": 1, "protect": 1}},
    "grassyglide": {"name": "Grassy Glide", "basePower": 55, "type": "Grass", "category": "Physical", "priority": 0, "flags": {"contact": 1, "protect": 1}},
    "woodhammer": {"name": "Wood Hammer", "basePower": 120, "type": "Grass", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "uturn": {"name": "U-turn", "basePower": 70, "type": "Bug", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "partingshot": {"name": "Parting Shot", "basePower": 0, "type": "Dark", "category": "Status"},
    "flareblitz": {"name": "Flare Blitz", "basePower": 120, "type": "Fire", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "knockoff": {"name": "Knock Off", "basePower": 65, "type": "Dark", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "moonblast": {"name": "Moonblast", "basePower": 95, "type": "Fairy", "category": "Special", "flags": {"protect": 1}},
    "shadowball": {"name": "Shadow Ball", "basePower": 80, "type": "Ghost", "category": "Special", "flags": {"bullet": 1, "protect": 1}},
    "dazzlinggleam": {"name": "Dazzling Gleam", "basePower": 80, "type": "Fairy", "category": "Special", "target": "allAdjacentFoes", "flags": {"protect": 1}},
    "surgingstrikes": {"name": "Surging Strikes", "basePower": 25, "type": "Water", "category": "Physical", "critRatio": 99, "multihit": 3, "flags": {"contact": 1}},
    "wickedblow": {"name": "Wicked Blow", "basePower": 75, "type": "Dark", "category": "Physical", "critRatio": 99, "flags": {"contact": 1}},
    "closecombat": {"name": "Close Combat", "basePower": 120, "type": "Fighting", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "suckerpunch": {"name": "Sucker Punch", "basePower": 70, "type": "Dark", "category": "Physical", "priority": 1, "flags": {"contact": 1, "protect": 1}},
    "ironhead": {"name": "Iron Head", "basePower": 80, "type": "Steel", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "kowtowcleave": {"name": "Kowtow Cleave", "basePower": 85, "type": "Dark", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "protect": {"name": "Protect", "basePower": 0, "type": "Normal", "category": "Status", "priority": 4},
    "detect": {"name": "Detect", "basePower": 0, "type": "Fighting", "category": "Status", "priority": 4},
    "spikyshield": {"name": "Spiky Shield", "basePower": 0, "type": "Grass", "category": "Status", "priority": 4},
    "tailwind": {"name": "Tailwind", "basePower": 0, "type": "Flying", "category": "Status"},
    "trickroom": {"name": "Trick Room", "basePower": 0, "type": "Psychic", "category": "Status", "priority": -7},
    "followme": {"name": "Follow Me", "basePower": 0, "type": "Normal", "category": "Status", "priority": 2},
    "ragepowder": {"name": "Rage Powder", "basePower": 0, "type": "Bug", "category": "Status", "priority": 2},
    "helpinghand": {"name": "Helping Hand", "basePower": 0, "type": "Normal", "category": "Status", "priority": 5},
    "wideguard": {"name": "Wide Guard", "basePower": 0, "type": "Rock", "category": "Status", "priority": 3},
    "quickguard": {"name": "Quick Guard", "basePower": 0, "type": "Fighting", "category": "Status", "priority": 3},
    "icywind": {"name": "Icy Wind", "basePower": 55, "type": "Ice", "category": "Special", "target": "allAdjacentFoes", "flags": {"protect": 1}},
    "electroweb": {"name": "Electroweb", "basePower": 55, "type": "Electric", "category": "Special", "target": "allAdjacentFoes", "flags": {"protect": 1}},
    "taunt": {"name": "Taunt", "basePower": 0, "type": "Dark", "category": "Status"},
    "encore": {"name": "Encore", "basePower": 0, "type": "Normal", "category": "Status"},
    "spore": {"name": "Spore", "basePower": 0, "type": "Grass", "category": "Status"},
    "pollenpuff": {"name": "Pollen Puff", "basePower": 90, "type": "Bug", "category": "Special", "flags": {"protect": 1}},
    "makeitrain": {"name": "Make It Rain", "basePower": 120, "type": "Steel", "category": "Special", "target": "allAdjacentFoes", "flags": {"protect": 1}},
    "electrodrift": {"name": "Electro Drift", "basePower": 100, "type": "Electric", "category": "Special", "flags": {"protect": 1}},
    "collisioncourse": {"name": "Collision Course", "basePower": 100, "type": "Fighting", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "astralbarrage": {"name": "Astral Barrage", "basePower": 120, "type": "Ghost", "category": "Special", "target": "allAdjacentFoes", "flags": {"protect": 1}},
    "glaciallance": {"name": "Glacial Lance", "basePower": 120, "type": "Ice", "category": "Physical", "target": "allAdjacentFoes", "flags": {"protect": 1}},
    "heatwave": {"name": "Heat Wave", "basePower": 95, "type": "Fire", "category": "Special", "target": "allAdjacentFoes", "flags": {"protect": 1}},
    "overheat": {"name": "Overheat", "basePower": 130, "type": "Fire", "category": "Special", "flags": {"protect": 1}},
    "earthquake": {"name": "Earthquake", "basePower": 100, "type": "Ground", "category": "Physical", "target": "allAdjacent", "flags": {"protect": 1}},
    "earthpower": {"name": "Earth Power", "basePower": 90, "type": "Ground", "category": "Special", "flags": {"protect": 1}},
    "dracometeor": {"name": "Draco Meteor", "basePower": 130, "type": "Dragon", "category": "Special", "flags": {"protect": 1}},
    "bodypress": {"name": "Body Press", "basePower": 80, "type": "Fighting", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "foulplay": {"name": "Foul Play", "basePower": 95, "type": "Dark", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "psyshock": {"name": "Psyshock", "basePower": 80, "type": "Psychic", "category": "Special", "flags": {"protect": 1}},
    "bloodmoon": {"name": "Blood Moon", "basePower": 140, "type": "Normal", "category": "Special", "flags": {"protect": 1}},
    "hypervoice": {"name": "Hyper Voice", "basePower": 90, "type": "Normal", "category": "Special", "target": "allAdjacentFoes", "flags": {"sound": 1, "protect": 1}},
    "jetpunch": {"name": "Jet Punch", "basePower": 60, "type": "Water", "category": "Physical", "priority": 1, "flags": {"contact": 1, "protect": 1}},
    "wavecrash": {"name": "Wave Crash", "basePower": 120, "type": "Water", "category": "Physical", "flags": {"contact": 1, "protect": 1}},
    "bleakwindstorm": {"name": "Bleakwind Storm", "basePower": 100, "type": "Flying", "category": "Special", "target": "allAdjacentFoes", "flags": {"protect": 1}},
    "hydrosteam": {"name": "Hydro Steam", "basePower": 80, "type": "Water", "category": "Special", "flags": {"protect": 1}},
    "starstorm": {"name": "Tera Starstorm", "basePower": 120, "type": "Normal", "category": "Special", "flags": {"protect": 1}},
    "gravity": {"name": "Gravity", "basePower": 0, "type": "Psychic", "category": "Status"},
    "hypnosis": {"name": "Hypnosis", "basePower": 0, "type": "Psychic", "category": "Status"},
    "skillswap": {"name": "Skill Swap", "basePower": 0, "type": "Psychic", "category": "Status"},
    "entrainment": {"name": "Entrainment", "basePower": 0, "type": "Normal", "category": "Status"},
    "doodle": {"name": "Doodle", "basePower": 0, "type": "Normal", "category": "Status"},
}

BUILTIN_ITEMS: Dict[str, Any] = {
    "assaultvest": {"name": "Assault Vest", "desc": "Raises Sp. Def by 50%, locks status moves."},
    "boosterenergy": {"name": "Booster Energy", "desc": "Activates Protosynthesis or Quark Drive."},
    "focussash": {"name": "Focus Sash", "desc": "Survives any OHKO at full HP with 1 HP."},
    "lifeorb": {"name": "Life Orb", "desc": "Attacks deal 1.3x damage at cost of 10% max HP."},
    "choiceband": {"name": "Choice Band", "desc": "Raises Attack by 50%, locks into one move."},
    "choicespecs": {"name": "Choice Specs", "desc": "Raises Sp. Atk by 50%, locks into one move."},
    "choicescarf": {"name": "Choice Scarf", "desc": "Raises Speed by 50%, locks into one move."},
    "sitrusberry": {"name": "Sitrus Berry", "desc": "Restores 25% max HP when at or below 50% HP."},
    "covertcloak": {"name": "Covert Cloak", "desc": "Protects holder from secondary effects of moves (e.g. Fake Out flinch)."},
    "clearamulet": {"name": "Clear Amulet", "desc": "Protects holder from stat reductions by other Pokemon (e.g. Intimidate, Parting Shot)."},
    "safetygoggles": {"name": "Safety Goggles", "desc": "Immunity to powder moves (Spore, Rage Powder) and weather damage."},
    "leftovers": {"name": "Leftovers", "desc": "Restores 1/16th max HP at end of each turn."},
    "rockyhelmet": {"name": "Rocky Helmet", "desc": "Attacker takes 1/6th max HP damage upon making contact."},
    "weaknesspolicy": {"name": "Weakness Policy", "desc": "Raises Attack and Sp. Atk by 2 stages when hit by super-effective move."},
    "ejectpack": {"name": "Eject Pack", "desc": "Switches out immediately when holder's stats are lowered."},
    "ejectbutton": {"name": "Eject Button", "desc": "Switches out immediately after being hit by an attack."},
    "roomservice": {"name": "Room Service", "desc": "Lowers Speed by 1 stage when Trick Room is active."},
    "ironball": {"name": "Iron Ball", "desc": "Halves holder's Speed and grounds Flying/Levitating Pokemon."},
    "miracleseed": {"name": "Miracle Seed", "desc": "Boosts Grass-type attacks by 20%."},
    "charcoal": {"name": "Charcoal", "desc": "Boosts Fire-type attacks by 20%."},
    "mysticwater": {"name": "Mystic Water", "desc": "Boosts Water-type attacks by 20%."},
    "wellspringmask": {"name": "Wellspring Mask", "desc": "Changes Ogerpon to Water type and boosts attacks by 20%."},
    "hearthflamemask": {"name": "Hearthflame Mask", "desc": "Changes Ogerpon to Fire type and boosts attacks by 20%."},
    "cornerstonemask": {"name": "Cornerstone Mask", "desc": "Changes Ogerpon to Rock type and boosts attacks by 20%."},
    "charizarditey": {"name": "Charizardite Y", "desc": "Mega evolves Charizard into Charizard-Mega-Y."},
    "kangaskhanite": {"name": "Kangaskhanite", "desc": "Mega evolves Kangaskhan into Kangaskhan-Mega."},
    "salamencite": {"name": "Salamencite", "desc": "Mega evolves Salamence into Salamence-Mega."},
    "gengarite": {"name": "Gengarite", "desc": "Mega evolves Gengar into Gengar-Mega."},
}

# ==========================================
# Showdown Data Engine & Auto-Downloader
# ==========================================
class ShowdownEngine:
    _instance: Optional[ShowdownEngine] = None

    def __init__(self):
        self.data_dir = get_data_dir()
        self.pokedex: Dict[str, Any] = dict(BUILTIN_POKEMON)
        self.moves: Dict[str, Any] = dict(BUILTIN_MOVES)
        self.items: Dict[str, Any] = dict(BUILTIN_ITEMS)
        self.learnsets: Dict[str, Any] = {}
        self.formats_data: Dict[str, Any] = {}
        self.load_or_download_all()

    @classmethod
    def get_instance(cls) -> ShowdownEngine:
        if cls._instance is None:
            cls._instance = ShowdownEngine()
        return cls._instance

    def _clean_key(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", text.lower())

    def _parse_js_object(self, js_text: str) -> Dict[str, Any]:
        """Convert JS export dictionary to Python dict safely."""
        try:
            # Strip JS export assignment like exports.BattleItems = ...;
            content = re.sub(r'^[^{]*', '', js_text).rstrip('; \n')
            # Fast regex to wrap unquoted keys in quotes
            json_str = re.sub(r'([{\[,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', content)
            return json.loads(json_str)
        except Exception:
            return {}

    def load_or_download_all(self):
        """Load from local data/ directory; if missing, fetch from play.pokemonshowdown.com."""
        files_to_sync = {
            "pokedex.json": "https://play.pokemonshowdown.com/data/pokedex.json",
            "moves.json": "https://play.pokemonshowdown.com/data/moves.json",
            "items.json": "https://play.pokemonshowdown.com/data/items.js",
            "learnsets.json": "https://play.pokemonshowdown.com/data/learnsets.json",
            "formats-data.js": "https://play.pokemonshowdown.com/data/formats-data.js",
        }

        for filename, url in files_to_sync.items():
            path = self.data_dir / filename
            if not path.exists() or path.stat().st_size < 100:
                try:
                    resp = requests.get(url, timeout=7, headers={"User-Agent": f"VGCShowdownStudio/{APP_VERSION}"})
                    if resp.status_code == 200:
                        if filename == "items.json" and url.endswith(".js"):
                            # Parse JS export and save as clean JSON
                            parsed = self._parse_js_object(resp.text)
                            if parsed:
                                with open(path, "w", encoding="utf-8") as f:
                                    json.dump(parsed, f, indent=2)
                            else:
                                with open(path, "w", encoding="utf-8") as f:
                                    f.write(resp.text)
                        else:
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(resp.text)
                except Exception:
                    pass

        # Load Pokédex
        pokedex_path = self.data_dir / "pokedex.json"
        if pokedex_path.exists():
            try:
                with open(pokedex_path, "r", encoding="utf-8") as f:
                    dex_data = json.load(f)
                    self.pokedex.update(dex_data)
            except Exception:
                pass

        # Load Moves
        moves_path = self.data_dir / "moves.json"
        if moves_path.exists():
            try:
                with open(moves_path, "r", encoding="utf-8") as f:
                    moves_data = json.load(f)
                    self.moves.update(moves_data)
            except Exception:
                pass

        # Load Items
        items_path = self.data_dir / "items.json"
        if items_path.exists():
            try:
                with open(items_path, "r", encoding="utf-8") as f:
                    try:
                        self.items.update(json.load(f))
                    except Exception:
                        f.seek(0)
                        self.items.update(self._parse_js_object(f.read()))
            except Exception:
                pass

        # Load Learnsets
        learnsets_path = self.data_dir / "learnsets.json"
        if learnsets_path.exists():
            try:
                with open(learnsets_path, "r", encoding="utf-8") as f:
                    self.learnsets = json.load(f)
            except Exception:
                pass

        # Load Formats Data
        formats_path = self.data_dir / "formats-data.js"
        if formats_path.exists():
            try:
                with open(formats_path, "r", encoding="utf-8") as f:
                    self.formats_data = self._parse_js_object(f.read())
            except Exception:
                pass

    def get_pokemon(self, name: str) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        key = self._clean_key(name)
        # Direct lookup
        if key in self.pokedex:
            return self.pokedex[key]
        # Search by display name
        for k, v in self.pokedex.items():
            if isinstance(v, dict) and v.get("name", "").lower() == name.lower():
                return v
        return None

    def get_move(self, name: str) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        key = self._clean_key(name)
        if key in self.moves:
            return self.moves[key]
        for k, v in self.moves.items():
            if isinstance(v, dict) and v.get("name", "").lower() == name.lower():
                return v
        return None

    def get_item(self, name: str) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        key = self._clean_key(name)
        if key in self.items:
            return self.items[key]
        for k, v in self.items.items():
            if isinstance(v, dict) and v.get("name", "").lower() == name.lower():
                return v
        return None

    def get_all_pokemon_names(self) -> List[str]:
        names = []
        for v in self.pokedex.values():
            if isinstance(v, dict) and "name" in v:
                names.append(v["name"])
        return sorted(list(set(names)))

    def get_all_move_names(self) -> List[str]:
        names = []
        for v in self.moves.values():
            if isinstance(v, dict) and "name" in v:
                names.append(v["name"])
        return sorted(list(set(names)))

    def get_all_item_names(self) -> List[str]:
        names = []
        for v in self.items.values():
            if isinstance(v, dict) and "name" in v:
                names.append(v["name"])
        return sorted(list(set(names)))

# ==========================================
# Battle Form Change & Gimmick System
# ==========================================
def resolve_form_change(
    species: str,
    gimmick_mode: str = "Standard/None",
    is_transformed: bool = False
) -> Tuple[Dict[str, int], List[str], str]:
    """
    Resolve stats, typing, and abilities for active battle form states:
    - Palafin-Zero (base 70 Atk) -> Palafin-Hero (base 160 Atk)
    - Mega Evolutions (e.g., Kangaskhan, Charizard-Y, Salamence)
    - Zen Mode, Terastal forms, etc.
    """
    engine = ShowdownEngine.get_instance()
    clean = engine._clean_key(species)
    base_data = engine.get_pokemon(species) or BUILTIN_POKEMON.get(clean, BUILTIN_POKEMON["incineroar"])
    
    stats = dict(base_data.get("baseStats", {"hp": 100, "atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100}))
    types = list(base_data.get("types", ["Normal"]))
    primary_ability = base_data.get("abilities", {}).get("0", "None")

    # Form Changes:
    if clean == "palafin" and is_transformed:
        hero_data = engine.get_pokemon("palafinhero") or BUILTIN_POKEMON.get("palafinhero")
        if hero_data:
            stats = dict(hero_data.get("baseStats", stats))

    elif gimmick_mode == "Mega Evolution":
        mega_name = f"{clean}mega"
        if mega_name in engine.pokedex or f"{clean}megay" in engine.pokedex:
            target_key = mega_name if mega_name in engine.pokedex else f"{clean}megay"
            mega_data = engine.pokedex.get(target_key, {})
            if mega_data:
                stats = dict(mega_data.get("baseStats", stats))
                types = list(mega_data.get("types", types))
                primary_ability = mega_data.get("abilities", {}).get("0", primary_ability)

    return stats, types, primary_ability

# ==========================================
# Tournament Legality Validator
# ==========================================
RESTRICTED_LEGENDARIES = {
    "miraidon", "koraidon", "calyrexshadow", "calyrexice", "calyrex",
    "zacian", "zaciancrowned", "zamazenta", "zamazentacrowned",
    "kyogre", "kyogreprimal", "groudon", "groudonprimal", "rayquaza", "rayquazamega",
    "dialga", "dialgaorigin", "palkia", "palkiaorigin", "giratina", "giratinaorigin",
    "mewtwo", "mewtwomegax", "mewtwomegay", "lunala", "solgaleo",
    "necrozmadawnwings", "necrozmaduskmane", "necrozmaultra", "terapagos",
    "reshiram", "zekrom", "kyurem", "kyuremwhite", "kyuremblack",
    "xerneas", "yveltal", "zygarde"
}

def validate_tournament_roster(team: List[Dict[str, Any]], format_id: str = "gen9vgc2024regg") -> Tuple[bool, List[str], List[str]]:
    """
    Validates a tournament roster:
    - 1-6 Pokémon (standard tournament roster is 6)
    - Species Clause (no duplicate Pokédex species)
    - Item Clause (no duplicate held items)
    - Restricted / Legendary limits based on format
    - Move legality via learnsets.json
    - Complete 4-move / item / ability / nature readiness
    Returns: (is_legal, issues, warnings)
    """
    engine = ShowdownEngine.get_instance()
    issues: List[str] = []
    warnings: List[str] = []

    if not team:
        issues.append("Roster is empty. A valid tournament roster requires 6 Pokémon.")
        return False, issues, warnings

    if len(team) < 6:
        warnings.append(f"Tournament rosters normally feature 6 Pokémon (currently {len(team)}).")

    species_seen = set()
    items_seen = set()
    restricted_count = 0

    fmt = format_id.lower()
    restricted_limit = 2 if ("regi" in fmt or "regj" in fmt) else (1 if "regg" in fmt else 0)

    for idx, mon in enumerate(team, 1):
        name = mon.get("name") or mon.get("species", "")
        if not name:
            issues.append(f"Slot {idx}: Missing Pokémon species.")
            continue

        clean_name = engine._clean_key(name)
        dex_entry = engine.get_pokemon(name)
        
        # Species Clause Check
        dex_num = dex_entry.get("num") if dex_entry else clean_name
        if dex_num in species_seen:
            issues.append(f"Slot {idx} ({name}): Species Clause violation - duplicate species detected.")
        else:
            species_seen.add(dex_num)

        # Restricted Check
        if clean_name in RESTRICTED_LEGENDARIES or (dex_entry and engine._clean_key(dex_entry.get("name", "")) in RESTRICTED_LEGENDARIES):
            restricted_count += 1

        # Item Clause Check
        item = mon.get("item", "").strip()
        if item:
            clean_item = engine._clean_key(item)
            if clean_item in items_seen:
                issues.append(f"Slot {idx} ({name}): Item Clause violation - duplicate item '{item}'.")
            else:
                items_seen.add(clean_item)
        else:
            warnings.append(f"Slot {idx} ({name}): No held item assigned.")

        # Ability Check
        ability = mon.get("ability", "").strip()
        if not ability:
            warnings.append(f"Slot {idx} ({name}): No ability selected.")

        # Moves Check
        moves = [m.strip() for m in mon.get("moves", []) if m and m.strip()]
        if len(moves) < 4:
            warnings.append(f"Slot {idx} ({name}): Incomplete moveset ({len(moves)}/4 moves assigned).")

        # Learnset Legality Check
        if engine.learnsets and clean_name in engine.learnsets:
            known_moves = engine.learnsets[clean_name].get("learnset", {})
            for m in moves:
                m_clean = engine._clean_key(m)
                if m_clean not in known_moves and m_clean not in ["protect", "substitute", "rest", "sleeptalk"]:
                    # Check base species learnset if it's an alternate form
                    base_species = dex_entry.get("baseSpecies") if dex_entry else None
                    if base_species and engine._clean_key(base_species) in engine.learnsets:
                        base_moves = engine.learnsets[engine._clean_key(base_species)].get("learnset", {})
                        if m_clean in base_moves:
                            continue
                    warnings.append(f"Slot {idx} ({name}): Move '{m}' might not be in standard learnset for this species.")

        # EVs / SPs Check
        is_sp = mon.get("is_sp", False)
        evs = mon.get("evs", {})
        total_points = sum(evs.values())
        if is_sp:
            if total_points > 66:
                issues.append(f"Slot {idx} ({name}): Champions Stat Points exceeded (Total: {total_points}/66 max).")
            for stat_k, stat_v in evs.items():
                if stat_v > 32:
                    issues.append(f"Slot {idx} ({name}): {stat_k.upper()} Stat Points exceed 32 (Value: {stat_v}).")
        else:
            if total_points > 510:
                issues.append(f"Slot {idx} ({name}): EVs exceed legal maximum of 510 (Total: {total_points}).")
            for stat_k, stat_v in evs.items():
                if stat_v > 252:
                    issues.append(f"Slot {idx} ({name}): {stat_k.upper()} EVs exceed legal maximum of 252 (Value: {stat_v}).")

    if restricted_count > restricted_limit and restricted_limit > 0:
        issues.append(f"Restricted limit violated: Format '{format_id}' permits at most {restricted_limit} restricted Pokémon (Found {restricted_count}).")
    elif restricted_limit == 0 and restricted_count > 0 and "vgc" in fmt:
        warnings.append(f"Restricted Pokémon detected ({restricted_count}) in format '{format_id}' which normally restricts them.")

    is_legal = len(issues) == 0
    return is_legal, issues, warnings

# ==========================================
# Full Multi-Era 16-Roll Damage Calculator
# ==========================================
def calculate_damage(
    attacker: Dict[str, Any],
    defender: Dict[str, Any],
    move_name: str,
    field: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Comprehensive 16-roll damage calculator supporting:
    - Weather (Sun, Rain, Sandstorm, Snow)
    - Terrains (Electric, Grassy, Psychic, Misty)
    - Treasures of Ruin auras (Sword, Tablets, Beads, Vessel)
    - Intimidate stages (-1 Atk)
    - Screens (Reflect, Light Screen, Aurora Veil)
    - Helping Hand & Friend Guard
    - Burn (0.5x physical damage)
    - Spread moves (0.75x in doubles)
    - Critical hit (1.5x)
    - Tera offensive & defensive typing
    - Mega stats & abilities
    - Dynamax (doubled HP)
    """
    engine = ShowdownEngine.get_instance()
    field = field or {}

    move_data = engine.get_move(move_name) or BUILTIN_MOVES.get(engine._clean_key(move_name), BUILTIN_MOVES["shadowball"])
    category = move_data.get("category", "Special")
    base_power = move_data.get("basePower", 80)

    if category == "Status" or base_power == 0:
        return {
            "rolls": [0] * 16,
            "min_damage": 0, "max_damage": 0,
            "defender_hp": 100,
            "min_pct": 0.0, "max_pct": 0.0,
            "ohko_chance": 0.0, "two_hko_chance": 0.0,
            "type_multiplier": 1.0,
            "desc": f"{move_name} is a Status move (deals 0 damage)."
        }

    level = attacker.get("level", 50)
    att_is_sp = attacker.get("is_sp", False)
    def_is_sp = defender.get("is_sp", False)

    # Resolve Attacker Stats
    att_form_stats, att_types, att_ability = resolve_form_change(
        attacker.get("name", ""),
        attacker.get("gimmick", "Standard/None"),
        attacker.get("is_transformed", False)
    )
    # Resolve Defender Stats
    def_form_stats, def_types, def_ability = resolve_form_change(
        defender.get("name", ""),
        defender.get("gimmick", "Standard/None"),
        defender.get("is_transformed", False)
    )

    # Handle Terastallization on Defender
    if defender.get("is_tera", False) and defender.get("tera_type"):
        def_types = [defender.get("tera_type")]

    # Calculate Raw Stats
    att_nature = attacker.get("nature", "Hardy")
    def_nature = defender.get("nature", "Hardy")
    att_evs = attacker.get("evs", {})
    def_evs = defender.get("evs", {})

    att_base_atk = att_form_stats.get("atk", 100)
    att_base_spa = att_form_stats.get("spa", 100)
    def_base_hp  = def_form_stats.get("hp", 100)
    def_base_def = def_form_stats.get("def", 100)
    def_base_spd = def_form_stats.get("spd", 100)

    raw_hp = calculate_stat(def_base_hp, "hp", def_evs.get("hp", 0), 31, def_nature, level, def_is_sp)
    if defender.get("is_dynamax", False):
        raw_hp *= 2

    # Attack stat selection
    is_physical = (category == "Physical")
    if move_name.lower() == "body press":
        attack_stat = calculate_stat(att_form_stats.get("def", 100), "def", att_evs.get("def", 0), 31, att_nature, level, att_is_sp)
    elif move_name.lower() == "foul play":
        target_atk_ev = def_evs.get("atk", 0)
        attack_stat = calculate_stat(def_base_atk := def_form_stats.get("atk", 100), "atk", target_atk_ev, 31, def_nature, level, def_is_sp)
    elif is_physical:
        attack_stat = calculate_stat(att_base_atk, "atk", att_evs.get("atk", 0), 31, att_nature, level, att_is_sp)
    else:
        attack_stat = calculate_stat(att_base_spa, "spa", att_evs.get("spa", 0), 31, att_nature, level, att_is_sp)

    # Defense stat selection
    if move_name.lower() in ["psyshock", "psystrike"]:
        defense_stat = calculate_stat(def_base_def, "def", def_evs.get("def", 0), 31, def_nature, level, def_is_sp)
    elif is_physical:
        defense_stat = calculate_stat(def_base_def, "def", def_evs.get("def", 0), 31, def_nature, level, def_is_sp)
    else:
        defense_stat = calculate_stat(def_base_spd, "spd", def_evs.get("spd", 0), 31, def_nature, level, def_is_sp)

    # Assault Vest Boost on Defender
    if defender.get("item", "").lower() == "assault vest" and not is_physical:
        defense_stat = int(defense_stat * 1.5)

    # Choice Items on Attacker
    if attacker.get("item", "").lower() == "choice band" and is_physical:
        attack_stat = int(attack_stat * 1.5)
    elif attacker.get("item", "").lower() == "choice specs" and not is_physical:
        attack_stat = int(attack_stat * 1.5)

    # Intimidate on Attacker
    if is_physical and field.get("intimidate", False):
        if attacker.get("item", "").lower() != "clear amulet" and attacker.get("ability", "").lower() not in ["clear body", "defiant", "inner focus"]:
            attack_stat = int(attack_stat * 2 / 3)

    # Ruin Auras
    if field.get("sword_of_ruin", False) and is_physical:
        defense_stat = int(defense_stat * 0.75)
    if field.get("tablets_of_ruin", False) and is_physical:
        attack_stat = int(attack_stat * 0.75)
    if field.get("beads_of_ruin", False) and not is_physical:
        defense_stat = int(defense_stat * 0.75)
    if field.get("vessel_of_ruin", False) and not is_physical:
        attack_stat = int(attack_stat * 0.75)

    # Base formula before modifiers
    base_calc = math.floor(math.floor(math.floor(2 * level / 5 + 2) * base_power * attack_stat / max(1, defense_stat)) / 50 + 2)

    # Modifiers
    modifier = 1.0

    # Weather
    weather = field.get("weather", "None")
    m_type = move_data.get("type", "Normal")
    if weather == "Sun":
        if m_type == "Fire": modifier *= 1.5
        elif m_type == "Water": modifier *= 0.5
    elif weather == "Rain":
        if m_type == "Water": modifier *= 1.5
        elif m_type == "Fire": modifier *= 0.5
    elif weather == "Snow" and "Ice" in def_types and is_physical:
        modifier *= 0.67
    elif weather == "Sandstorm" and "Rock" in def_types and not is_physical:
        modifier *= 0.67

    # Terrain
    terrain = field.get("terrain", "None")
    if terrain == "Electric" and m_type == "Electric": modifier *= 1.3
    elif terrain == "Grassy":
        if m_type == "Grass": modifier *= 1.3
        elif move_name.lower() in ["earthquake", "bulldoze", "magnitude"]: modifier *= 0.5
    elif terrain == "Psychic" and m_type == "Psychic": modifier *= 1.3
    elif terrain == "Misty" and m_type == "Dragon": modifier *= 0.5

    # STAB
    is_tera = attacker.get("is_tera", False)
    tera_type = attacker.get("tera_type", "")
    stab_bonus = 1.0
    if is_tera:
        if m_type == tera_type and m_type in att_types:
            stab_bonus = 2.0
        elif m_type == tera_type or m_type in att_types:
            stab_bonus = 1.5
    else:
        if m_type in att_types:
            stab_bonus = 1.5
    modifier *= stab_bonus

    # Type Effectiveness
    type_mult = get_type_effectiveness(m_type, def_types)
    modifier *= type_mult

    # Spread Move Reduction (Doubles)
    is_spread = field.get("is_spread", False) or move_data.get("target") in ["allAdjacentFoes", "allAdjacent"]
    if is_spread and field.get("is_doubles", True):
        modifier *= 0.75

    # Screens
    if is_physical and field.get("reflect", False):
        modifier *= 0.67 if field.get("is_doubles", True) else 0.5
    elif not is_physical and field.get("light_screen", False):
        modifier *= 0.67 if field.get("is_doubles", True) else 0.5
    elif field.get("aurora_veil", False):
        modifier *= 0.67 if field.get("is_doubles", True) else 0.5

    # Helping Hand & Friend Guard
    if field.get("helping_hand", False):
        modifier *= 1.5
    if field.get("friend_guard", False):
        modifier *= 0.75

    # Burn
    if is_physical and field.get("is_burned", False) and attacker.get("ability", "").lower() != "guts" and move_name.lower() != "facade":
        modifier *= 0.5

    # Critical Hit
    if field.get("is_critical", False) or move_data.get("critRatio", 0) >= 90:
        modifier *= 1.5

    # Life Orb
    if attacker.get("item", "").lower() == "life orb":
        modifier *= 1.3

    # 16 Random Rolls (85% to 100%)
    rolls = [max(1, int(math.floor(base_calc * modifier * (r / 100.0)))) for r in range(85, 101)]
    min_damage = rolls[0]
    max_damage = rolls[-1]

    min_pct = round((min_damage / raw_hp) * 100, 1)
    max_pct = round((max_damage / raw_hp) * 100, 1)

    ohko_count = sum(1 for r in rolls if r >= raw_hp)
    ohko_chance = round((ohko_count / 16.0) * 100, 1)

    two_hko_count = 0
    for r1 in rolls:
        for r2 in rolls:
            if (r1 + r2) >= raw_hp:
                two_hko_count += 1
    two_hko_chance = round((two_hko_count / 256.0) * 100, 1)

    eff_str = ""
    if type_mult > 1: eff_str = " (Super-effective!)"
    elif type_mult == 0: eff_str = " (Immune)"
    elif type_mult < 1: eff_str = " (Resisted)"

    desc = f"{move_name}: {min_damage}-{max_damage} ({min_pct}% - {max_pct}%){eff_str} | OHKO: {ohko_chance}% | 2HKO: {two_hko_chance}%"

    return {
        "rolls": rolls,
        "min_damage": min_damage,
        "max_damage": max_damage,
        "defender_hp": raw_hp,
        "min_pct": min_pct,
        "max_pct": max_pct,
        "ohko_chance": ohko_chance,
        "two_hko_chance": two_hko_chance,
        "type_multiplier": type_mult,
        "desc": desc
    }

# ==========================================
# Universal Showdown / PokePaste Parser & Exporter
# ==========================================
def parse_showdown_paste(text: str, default_is_sp: bool = False) -> List[Dict[str, Any]]:
    """
    Parses Showdown export text or PokePaste into team list.
    Supports both standard EVs/IVs and Champions Stat Points (0-32 SP).
    """
    engine = ShowdownEngine.get_instance()
    teams: List[Dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", text.strip())

    for block in blocks:
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        if not lines:
            continue

        header = lines[0]
        item = ""
        species = header
        if "@" in header:
            parts = header.split("@")
            species = parts[0].strip()
            item = parts[1].strip()

        # Check for nickname: 'Nickname (Species)'
        nickname = ""
        m = re.match(r"^(.*?)\s*\((.*?)\)$", species)
        if m:
            nickname = m.group(1).strip()
            species = m.group(2).strip()

        # Strip gender if present like (M) or (F)
        species = re.sub(r"\s*\([MF]\)$", "", species).strip()

        mon: Dict[str, Any] = {
            "name": species,
            "nickname": nickname,
            "item": item,
            "ability": "",
            "level": 50,
            "tera_type": "",
            "nature": "Hardy",
            "evs": {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "moves": [],
            "is_sp": default_is_sp,
            "gimmick": "Standard/None"
        }

        for line in lines[1:]:
            if line.startswith("Ability:"):
                mon["ability"] = line.replace("Ability:", "").strip()
            elif line.startswith("Level:"):
                try:
                    mon["level"] = int(line.replace("Level:", "").strip())
                except Exception:
                    pass
            elif line.startswith("Tera Type:"):
                mon["tera_type"] = line.replace("Tera Type:", "").strip()
            elif line.endswith("Nature"):
                mon["nature"] = line.replace("Nature", "").strip()
            elif line.startswith("EVs:") or line.startswith("SPs:") or line.startswith("Stat Points:"):
                is_sp_detected = line.startswith("SPs:") or line.startswith("Stat Points:")
                if is_sp_detected:
                    mon["is_sp"] = True
                cleaned_evs = re.sub(r"^(EVs:|SPs:|Stat Points:)", "", line).strip()
                for part in cleaned_evs.split("/"):
                    p = part.strip()
                    m_ev = re.match(r"^(\d+)\s+([a-zA-Z]+)$", p)
                    if m_ev:
                        val = int(m_ev.group(1))
                        stat = m_ev.group(2).lower()
                        if stat in ["hp", "atk", "def", "spa", "spd", "spe"]:
                            mon["evs"][stat] = val
            elif line.startswith("IVs:"):
                cleaned_ivs = line.replace("IVs:", "").strip()
                for part in cleaned_ivs.split("/"):
                    p = part.strip()
                    m_iv = re.match(r"^(\d+)\s+([a-zA-Z]+)$", p)
                    if m_iv:
                        val = int(m_iv.group(1))
                        stat = m_iv.group(2).lower()
                        if stat in ["hp", "atk", "def", "spa", "spd", "spe"]:
                            mon["ivs"][stat] = val
            elif line.startswith("-"):
                move_name = line.lstrip("- ").strip()
                if move_name and len(mon["moves"]) < 4:
                    mon["moves"].append(move_name)

        if mon["name"]:
            teams.append(mon)

    return teams

def export_showdown_paste(team: List[Dict[str, Any]], export_as_sp: bool = False) -> str:
    """Exports roster into universal Showdown / PokePaste format."""
    blocks: List[str] = []
    for mon in team:
        name = mon.get("name", "Unknown")
        item = mon.get("item", "").strip()
        header = f"{name} @ {item}" if item else name

        lines = [header]
        if mon.get("ability"):
            lines.append(f"Ability: {mon['ability']}")
        if mon.get("level") and mon.get("level") != 100:
            lines.append(f"Level: {mon['level']}")
        if mon.get("tera_type"):
            lines.append(f"Tera Type: {mon['tera_type']}")

        # EVs or SPs
        evs = mon.get("evs", {})
        ev_parts = []
        is_sp = export_as_sp or mon.get("is_sp", False)
        prefix = "SPs: " if is_sp else "EVs: "

        order = ["hp", "atk", "def", "spa", "spd", "spe"]
        labels = {"hp": "HP", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD", "spe": "Spe"}
        for k in order:
            v = evs.get(k, 0)
            if v > 0:
                ev_parts.append(f"{v} {labels[k]}")

        if ev_parts:
            lines.append(prefix + " / ".join(ev_parts))

        nature = mon.get("nature", "Hardy")
        lines.append(f"{nature} Nature")

        # IVs check
        ivs = mon.get("ivs", {})
        iv_parts = []
        for k in order:
            v = ivs.get(k, 31)
            if v < 31:
                iv_parts.append(f"{v} {labels[k]}")
        if iv_parts:
            lines.append("IVs: " + " / ".join(iv_parts))

        # Moves
        for m in mon.get("moves", []):
            if m:
                lines.append(f"- {m}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)

# ==========================================
# Local Multi-Team Storage (data/saved_teams.json)
# ==========================================
class SavedTeamsManager:
    def __init__(self):
        self.file_path = get_data_dir() / "saved_teams.json"
        self._ensure_storage()

    def _ensure_storage(self):
        if not self.file_path.exists():
            default_data = {
                "Balance Core - Urshifu & Rillaboom": [
                    {
                        "name": "Rillaboom", "item": "Miracle Seed", "ability": "Grassy Surge", "level": 50,
                        "tera_type": "Fire", "nature": "Adamant",
                        "evs": {"hp": 252, "atk": 252, "def": 4, "spa": 0, "spd": 0, "spe": 0},
                        "moves": ["Grassy Glide", "Wood Hammer", "Fake Out", "U-turn"], "is_sp": False
                    },
                    {
                        "name": "Incineroar", "item": "Sitrus Berry", "ability": "Intimidate", "level": 50,
                        "tera_type": "Grass", "nature": "Careful",
                        "evs": {"hp": 252, "atk": 4, "def": 156, "spa": 0, "spd": 96, "spe": 4},
                        "moves": ["Flare Blitz", "Knock Off", "Parting Shot", "Fake Out"], "is_sp": False
                    },
                    {
                        "name": "Flutter Mane", "item": "Booster Energy", "ability": "Protosynthesis", "level": 50,
                        "tera_type": "Fairy", "nature": "Timid",
                        "evs": {"hp": 116, "atk": 0, "def": 156, "spa": 116, "spd": 4, "spe": 116},
                        "moves": ["Moonblast", "Shadow Ball", "Dazzling Gleam", "Protect"], "is_sp": False
                    },
                    {
                        "name": "Urshifu-Rapid-Strike", "item": "Choice Scarf", "ability": "Unseen Fist", "level": 50,
                        "tera_type": "Water", "nature": "Jolly",
                        "evs": {"hp": 4, "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252},
                        "moves": ["Surging Strikes", "Close Combat", "Aqua Jet", "U-turn"], "is_sp": False
                    },
                    {
                        "name": "Kingambit", "item": "Assault Vest", "ability": "Defiant", "level": 50,
                        "tera_type": "Flying", "nature": "Adamant",
                        "evs": {"hp": 252, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 0},
                        "moves": ["Kowtow Cleave", "Sucker Punch", "Iron Head", "Low Kick"], "is_sp": False
                    },
                    {
                        "name": "Whimsicott", "item": "Focus Sash", "ability": "Prankster", "level": 50,
                        "tera_type": "Ghost", "nature": "Timid",
                        "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252},
                        "moves": ["Tailwind", "Moonblast", "Encore", "Protect"], "is_sp": False
                    }
                ]
            }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2)

    def load_all_teams(self) -> Dict[str, List[Dict[str, Any]]]:
        self._ensure_storage()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_team(self, name: str, team: List[Dict[str, Any]]) -> bool:
        teams = self.load_all_teams()
        teams[name] = team
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(teams, f, indent=2)
            return True
        except Exception:
            return False

    def delete_team(self, name: str) -> bool:
        teams = self.load_all_teams()
        if name in teams:
            del teams[name]
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(teams, f, indent=2)
                return True
            except Exception:
                return False
        return False

# ==========================================
# Showdown Replay Importer
# ==========================================
def parse_showdown_replay(replay_url: str, meta_db: Any = None) -> List[Dict[str, Any]]:
    """
    Fetches <replay_url>.json (or logs), extracts the opponent's 6 Pokémon
    (species, revealed moves, items, abilities, forms/gimmicks),
    and fills unrevealed sets with top meta spreads from vgc_meta.db.
    """
    clean_url = replay_url.strip()
    if not clean_url.endswith(".json"):
        clean_url = clean_url.rstrip("/") + ".json"

    resp = requests.get(clean_url, timeout=8, headers={"User-Agent": f"VGCShowdownStudio/{APP_VERSION}"})
    if resp.status_code != 200:
        raise ValueError(f"Could not load Showdown replay (HTTP {resp.status_code})")

    data = resp.json()
    log = data.get("log", "")
    p2 = data.get("p2", "Player 2")

    discovered: Dict[str, Dict[str, Any]] = {}
    lines = log.split("\n")

    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        tag = parts[1]

        # Switch line: |switch|p2a: Nickname|Species, L50, M|...
        if tag in ["switch", "drag"]:
            target_side = parts[2]
            if target_side.startswith("p2"):
                species_raw = parts[3].split(",")[0].strip()
                clean_sp = ShowdownEngine.get_instance()._clean_key(species_raw)
                if clean_sp not in discovered:
                    discovered[clean_sp] = {
                        "name": species_raw,
                        "moves": set(),
                        "item": "",
                        "ability": "",
                        "tera_type": "",
                        "gimmick": "Standard/None"
                    }

        # Move line: |move|p2a: ...|MoveName|...
        elif tag == "move":
            target_side = parts[2]
            if target_side.startswith("p2") and len(parts) > 3:
                move_name = parts[3].strip()
                # Find matching species
                for sp_k, sp_dict in discovered.items():
                    if len(sp_dict["moves"]) < 4:
                        sp_dict["moves"].add(move_name)

        # Item reveal: |-item|p2a: ...|ItemName
        elif tag == "-item":
            target_side = parts[2]
            if target_side.startswith("p2") and len(parts) > 3:
                item_name = parts[3].strip()
                for sp_dict in discovered.values():
                    if not sp_dict["item"]:
                        sp_dict["item"] = item_name

        # Ability reveal: |-ability|p2a: ...|AbilityName
        elif tag == "-ability":
            target_side = parts[2]
            if target_side.startswith("p2") and len(parts) > 3:
                ab_name = parts[3].strip()
                for sp_dict in discovered.values():
                    if not sp_dict["ability"]:
                        sp_dict["ability"] = ab_name

        # Terastallize: |-terastallize|p2a: ...|TeraType
        elif tag == "-terastallize":
            target_side = parts[2]
            if target_side.startswith("p2") and len(parts) > 3:
                tera_t = parts[3].strip()
                for sp_dict in discovered.values():
                    sp_dict["tera_type"] = tera_t
                    sp_dict["gimmick"] = "Terastallization"

    # Assemble complete 6-mon team with top meta spreads
    result_team: List[Dict[str, Any]] = []
    for sp_k, info in discovered.items():
        base_dex = ShowdownEngine.get_instance().get_pokemon(info["name"]) or BUILTIN_POKEMON.get(sp_k, {})
        display_name = base_dex.get("name", info["name"])
        moves = list(info["moves"])

        # Query top meta defaults if moves/item/spread missing
        default_item = info["item"] or "Sitrus Berry"
        default_ability = info["ability"] or (base_dex.get("abilities", {}).get("0", "None") if base_dex else "None")
        default_evs = {"hp": 252, "atk": 4, "def": 124, "spa": 4, "spd": 124, "spe": 0}
        default_nature = "Hardy"

        if meta_db:
            try:
                top_data = meta_db.get_top_meta_for_pokemon(display_name)
                if top_data:
                    if not info["item"] and top_data.get("top_item"):
                        default_item = top_data["top_item"]
                    if not info["ability"] and top_data.get("top_ability"):
                        default_ability = top_data["top_ability"]
                    if top_data.get("top_spread"):
                        default_nature = top_data["top_spread"].get("nature", default_nature)
                        default_evs = top_data["top_spread"].get("evs", default_evs)
                    for m in top_data.get("top_moves", []):
                        if len(moves) < 4 and m not in moves:
                            moves.append(m)
            except Exception:
                pass

        # Pad remaining moves with Protect or standard attacks
        fallback_moves = ["Protect", "Fake Out", "U-turn", "Shadow Ball", "Moonblast", "Flare Blitz"]
        for fm in fallback_moves:
            if len(moves) < 4 and fm not in moves:
                moves.append(fm)

        result_team.append({
            "name": display_name,
            "item": default_item,
            "ability": default_ability,
            "level": 50,
            "tera_type": info.get("tera_type") or "Fairy",
            "nature": default_nature,
            "evs": default_evs,
            "ivs": {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
            "moves": moves[:4],
            "is_sp": False,
            "gimmick": info.get("gimmick", "Standard/None")
        })

    return result_team

# ==========================================
# Dynamic Multi-Year Format Discovery
# ==========================================
def discover_formats() -> List[Dict[str, Any]]:
    """
    Auto-discovers active and historical VGC, Pokémon Champions,
    and Smogon Singles/Doubles formats from Showdown formats-data.js and
    the latest YYYY-MM directory on https://www.smogon.com/stats/.
    """
    discovered: List[Dict[str, Any]] = [
        {"id": "gen9championsvgc2026regmc", "name": "Champions VGC Reg M-C (SP Spreads)", "is_sp": True, "gimmick": "Mega Evolution", "type": "champions"},
        {"id": "gen9championsvgc2026regmcbo3", "name": "Champions VGC Reg M-C (Bo3 OTS)", "is_sp": True, "gimmick": "Mega Evolution", "type": "champions"},
        {"id": "gen9championsbssregmc", "name": "Champions Battle Stadium Singles (Reg M-C)", "is_sp": True, "gimmick": "Mega Evolution", "type": "champions"},
        {"id": "gen9vgc2024regg", "name": "VGC 2024 Regulation G (1 Restricted)", "is_sp": False, "gimmick": "Terastallization", "type": "vgc"},
        {"id": "gen9vgc2024regh", "name": "VGC 2024 Regulation H (No Restr/Sub-Legend)", "is_sp": False, "gimmick": "Terastallization", "type": "vgc"},
        {"id": "gen9vgc2024regf", "name": "VGC 2024 Regulation F", "is_sp": False, "gimmick": "Terastallization", "type": "vgc"},
        {"id": "gen9doublesou", "name": "Gen 9 Doubles OU", "is_sp": False, "gimmick": "Terastallization", "type": "doubles"},
        {"id": "gen9ou", "name": "Gen 9 OU Singles", "is_sp": False, "gimmick": "Terastallization", "type": "singles"},
        {"id": "gen8vgc2022", "name": "VGC 2022 (Series 12 Dynamax)", "is_sp": False, "gimmick": "Dynamax", "type": "vgc"},
        {"id": "gen7vgc2019", "name": "VGC 2019 Ultra Series (Mega/Z-Moves)", "is_sp": False, "gimmick": "Mega Evolution", "type": "vgc"},
    ]

    try:
        r = requests.get("https://www.smogon.com/stats/", timeout=4, headers={"User-Agent": f"VGCShowdownStudio/{APP_VERSION}"})
        if r.status_code == 200:
            dates = sorted(set(re.findall(r"(\d{4}-\d{2})/?", r.text)))
            if dates:
                latest_m = dates[-1]
                r2 = requests.get(f"https://www.smogon.com/stats/{latest_m}/", timeout=4, headers={"User-Agent": f"VGCShowdownStudio/{APP_VERSION}"})
                if r2.status_code == 200:
                    found_formats = re.findall(r'href=[\'"]([a-zA-Z0-9_\-]+)\-0\.txt[\'"]', r2.text)
                    for fmt_str in found_formats:
                        fmt_lower = fmt_str.lower()
                        is_champions = "champion" in fmt_lower
                        is_vgc = "vgc" in fmt_lower
                        is_doubles = "doubles" in fmt_lower
                        
                        if is_vgc or is_champions or is_doubles:
                            # Avoid duplicates
                            if not any(d["id"] == fmt_lower for d in discovered):
                                name_label = fmt_str.replace("gen9", "Gen 9 ").replace("champions", "Champions ").replace("vgc", "VGC ")
                                discovered.append({
                                    "id": fmt_lower,
                                    "name": name_label,
                                    "is_sp": is_champions,
                                    "gimmick": "Mega Evolution" if is_champions else ("Terastallization" if "gen9" in fmt_lower else "Standard/None"),
                                    "type": "champions" if is_champions else ("vgc" if is_vgc else "doubles")
                                })
    except Exception:
        pass

    return discovered
