"""
VGC & Showdown Studio (APP_VERSION = "1.0.0")
100% Free Desktop Application for Pokémon VGC, Pokémon Champions, and Smogon Formats.
Engineered for all past, current, and future generations and tournament regulations.
"""

from __future__ import annotations
import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Any, Dict, List, Optional

import customtkinter as ctk
from PIL import Image

from core.mechanics import (
    APP_VERSION,
    ShowdownEngine,
    SavedTeamsManager,
    discover_formats,
    calculate_stat,
    calculate_damage,
    get_type_effectiveness,
    validate_tournament_roster,
    parse_showdown_paste,
    export_showdown_paste,
    parse_showdown_replay,
    resolve_form_change,
    BUILTIN_POKEMON,
    BUILTIN_MOVES,
    BUILTIN_ITEMS,
    NATURES,
    ALL_TYPES,
    TYPE_CHART
)
from core.sprite_loader import SpriteLoader
from scrapers.meta_fetcher import MetaDatabase, pull_cloud_db, check_github_release
from core.simulator import BattleSimulator, BUILTIN_ARCHETYPES
from core.combo_lab import MechanicInteractionMiner, EvolutionaryTeamMutator
from core.planner import TeamAnalyticsEngine, TeamGameplanEngine, EVBenchmarkOptimizer
from core.ots_exporter import export_ots_png, TYPE_COLORS
from core.copilot import StudioCopilot

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class VGCStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"VGC & Showdown Studio v{APP_VERSION} - [Champions & Multi-Era Edition]")
        self.geometry("1560x960")
        self.minsize(1280, 800)

        # Core Engines Initialization
        self.engine = ShowdownEngine.get_instance()
        self.db = MetaDatabase.get_instance()
        self.teams_mgr = SavedTeamsManager()
        self.sprite_loader = SpriteLoader.get_instance()

        # State Variables
        self.formats_list = discover_formats()
        self.active_format_id = self.formats_list[0]["id"] if self.formats_list else "gen9vgc2024regg"
        self.is_sp_mode = bool(self.formats_list[0].get("is_sp", False)) if self.formats_list else False
        self.active_gimmick = self.formats_list[0].get("gimmick", "Standard/None") if self.formats_list else "Standard/None"
        self.anti_meta_mode = False
        self.selected_slot = 0  # 0 to 5

        # Initialize Sub-engines
        self._init_sub_engines()

        # Active Team Data (6 Pokémon)
        self.saved_teams = self.teams_mgr.load_all_teams()
        default_team_name = list(self.saved_teams.keys())[0] if self.saved_teams else "New Team"
        self.current_team_name = default_team_name
        self.current_team = self.saved_teams.get(default_team_name, self._create_blank_team())

        # Build GUI
        self._build_layout()
        self._refresh_all_views()

        # Startup background tasks
        threading.Thread(target=self._check_startup_release, daemon=True).start()

    def _init_sub_engines(self):
        self.copilot = StudioCopilot(self.active_format_id)
        self.analytics = TeamAnalyticsEngine(self.active_format_id)
        self.gameplan = TeamGameplanEngine(self.active_format_id)
        self.benchmarks = EVBenchmarkOptimizer(self.active_format_id)
        self.simulator = BattleSimulator(self.active_format_id)
        self.miner = MechanicInteractionMiner()
        self.mutator = EvolutionaryTeamMutator(self.active_format_id)

    def _create_blank_team(self) -> List[Dict[str, Any]]:
        return [
            {"name": "Incineroar", "item": "Sitrus Berry", "ability": "Intimidate", "level": 50, "tera_type": "Grass", "nature": "Careful", "evs": {"hp": 252, "atk": 4, "def": 156, "spa": 0, "spd": 96, "spe": 4}, "moves": ["Fake Out", "Parting Shot", "Knock Off", "Flare Blitz"], "is_sp": self.is_sp_mode},
            {"name": "Rillaboom", "item": "Miracle Seed", "ability": "Grassy Surge", "level": 50, "tera_type": "Fire", "nature": "Adamant", "evs": {"hp": 252, "atk": 252, "def": 4, "spa": 0, "spd": 0, "spe": 0}, "moves": ["Grassy Glide", "Wood Hammer", "Fake Out", "U-turn"], "is_sp": self.is_sp_mode},
            {"name": "Flutter Mane", "item": "Booster Energy", "ability": "Protosynthesis", "level": 50, "tera_type": "Fairy", "nature": "Timid", "evs": {"hp": 116, "atk": 0, "def": 156, "spa": 116, "spd": 4, "spe": 116}, "moves": ["Moonblast", "Shadow Ball", "Dazzling Gleam", "Protect"], "is_sp": self.is_sp_mode},
            {"name": "Urshifu-Rapid-Strike", "item": "Choice Scarf", "ability": "Unseen Fist", "level": 50, "tera_type": "Water", "nature": "Jolly", "evs": {"hp": 4, "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252}, "moves": ["Surging Strikes", "Close Combat", "Aqua Jet", "U-turn"], "is_sp": self.is_sp_mode},
            {"name": "Kingambit", "item": "Assault Vest", "ability": "Defiant", "level": 50, "tera_type": "Flying", "nature": "Adamant", "evs": {"hp": 252, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 0}, "moves": ["Kowtow Cleave", "Sucker Punch", "Iron Head", "Low Kick"], "is_sp": self.is_sp_mode},
            {"name": "Whimsicott", "item": "Focus Sash", "ability": "Prankster", "level": 50, "tera_type": "Ghost", "nature": "Timid", "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252}, "moves": ["Tailwind", "Moonblast", "Encore", "Protect"], "is_sp": self.is_sp_mode},
        ]

    # ==========================================
    # Top Banner & Release Checker
    # ==========================================
    def _check_startup_release(self):
        try:
            rel = check_github_release(current_version=APP_VERSION)
            if rel.get("update_available"):
                self.after(500, lambda: self._show_update_banner(rel["latest_version"], rel["release_url"]))
        except Exception:
            pass

    def _show_update_banner(self, latest_ver: str, url: str):
        self.banner_frame.pack(side="top", fill="x", padx=10, pady=(6, 0), before=self.header_frame)
        self.banner_label.configure(text=f"🚀 A newer version of VGC & Showdown Studio is available: v{latest_ver}! Click to view release updates.")
        self.banner_frame.bind("<Button-1>", lambda e: os.system(f"start {url}"))
        self.banner_label.bind("<Button-1>", lambda e: os.system(f"start {url}"))

    # ==========================================
    # Layout Builder
    # ==========================================
    def _build_layout(self):
        # Update Banner Frame (Hidden by default)
        self.banner_frame = ctk.CTkFrame(self, fg_color="#e67e22", corner_radius=6, height=36, cursor="hand2")
        self.banner_label = ctk.CTkLabel(self.banner_frame, text="", text_color="white", font=ctk.CTkFont(size=13, weight="bold"))
        self.banner_label.pack(side="left", padx=15, pady=4)
        close_btn = ctk.CTkButton(self.banner_frame, text="✕", width=26, height=24, fg_color="#d35400", command=self.banner_frame.pack_forget)
        close_btn.pack(side="right", padx=10, pady=4)

        # Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="#1e222d", corner_radius=0, height=54)
        self.header_frame.pack(side="top", fill="x")
        self._build_header()

        # Live Report Card Strip
        self.report_strip_frame = ctk.CTkFrame(self, fg_color="#181b24", corner_radius=0, height=44)
        self.report_strip_frame.pack(side="top", fill="x", padx=0, pady=0)
        self._build_report_strip()

        # 6 Pokémon Visual Cards Strip
        self.cards_strip_frame = ctk.CTkFrame(self, fg_color="#13151c", corner_radius=0, height=135)
        self.cards_strip_frame.pack(side="top", fill="x", padx=10, pady=(6, 4))
        self._build_cards_strip()

        # Main Central Panes (Tabs on Left, Docked Co-Pilot on Right)
        self.main_pane = ctk.CTkFrame(self, fg_color="transparent")
        self.main_pane.pack(side="bottom", fill="both", expand=True, padx=10, pady=(0, 6))

        # Right Docked Co-Pilot Sidebar
        self.copilot_frame = ctk.CTkFrame(self.main_pane, fg_color="#1c1f2b", corner_radius=10, width=370)
        self.copilot_frame.pack(side="right", fill="y", padx=(6, 0), pady=0)
        self.copilot_frame.pack_propagate(False)
        self._build_copilot_sidebar()

        # Left Tabview
        self.tabview = ctk.CTkTabview(self.main_pane, fg_color="#181a24", segmented_button_selected_color="#5865f2")
        self.tabview.pack(side="left", fill="both", expand=True)

        # 9 Tabs
        self.tab_builder = self.tabview.add("Team Builder")
        self.tab_combo = self.tabview.add("Rogue Combo Lab")
        self.tab_plan = self.tabview.add("Overall Plan & Leads")
        self.tab_optimizer = self.tabview.add("EV/SP Optimizer")
        self.tab_matrix = self.tabview.add("Type Coverage Matrix")
        self.tab_simulator = self.tabview.add("Matchup & Threat Sim")
        self.tab_damage = self.tabview.add("Damage Calc")
        self.tab_speed = self.tabview.add("Speed Tiers")
        self.tab_tournament = self.tabview.add("Tournament Explorer")

        self._build_tab_builder()
        self._build_tab_combo()
        self._build_tab_plan()
        self._build_tab_optimizer()
        self._build_tab_matrix()
        self._build_tab_simulator()
        self._build_tab_damage()
        self._build_tab_speed()
        self._build_tab_tournament()

    # ==========================================
    # Header Construction
    # ==========================================
    def _build_header(self):
        f = self.header_frame

        # App Brand
        brand_lbl = ctk.CTkLabel(f, text="⚔️ VGC & SHOWDOWN STUDIO", font=ctk.CTkFont(size=17, weight="bold"), text_color="#5865f2")
        brand_lbl.pack(side="left", padx=(15, 12))

        # Dynamic Format Selector
        fmt_names = [f["name"] for f in self.formats_list]
        self.fmt_combo = ctk.CTkComboBox(f, values=fmt_names, width=240, command=self._on_format_changed)
        self.fmt_combo.set(fmt_names[0] if fmt_names else "VGC 2024 Reg G")
        self.fmt_combo.pack(side="left", padx=4)

        # Custom Format Entry
        self.custom_fmt_entry = ctk.CTkEntry(f, placeholder_text="Custom Format ID", width=125)
        self.custom_fmt_entry.pack(side="left", padx=3)
        cust_btn = ctk.CTkButton(f, text="Set", width=42, fg_color="#34495e", command=self._on_custom_format_set)
        cust_btn.pack(side="left", padx=(0, 8))

        # Stat Mode Toggle (Classic EVs vs Champions SPs)
        self.stat_mode_btn = ctk.CTkButton(
            f, text="Mode: Champions SP (0-32)" if self.is_sp_mode else "Mode: Classic EVs (0-252)",
            width=175, fg_color="#8e44ad" if self.is_sp_mode else "#2980b9",
            command=self._toggle_stat_mode
        )
        self.stat_mode_btn.pack(side="left", padx=4)

        # Gimmick Selector
        gimmicks = ["Standard/None", "Terastallization", "Mega Evolution", "Dynamax"]
        self.gimmick_combo = ctk.CTkComboBox(f, values=gimmicks, width=155, command=self._on_gimmick_changed)
        self.gimmick_combo.set(self.active_gimmick)
        self.gimmick_combo.pack(side="left", padx=4)

        # Anti-Meta Mode Switch
        self.anti_meta_switch = ctk.CTkSwitch(f, text="Anti-Meta", command=self._on_anti_meta_toggled)
        self.anti_meta_switch.pack(side="left", padx=6)

        # Action Buttons (Right Aligned)
        btn_paste = ctk.CTkButton(f, text="📋 Paste", width=70, fg_color="#2c3e50", command=self._open_showdown_paste_dialog)
        btn_paste.pack(side="right", padx=(2, 12))

        btn_replay = ctk.CTkButton(f, text="🎬 Replay", width=70, fg_color="#27ae60", command=self._open_replay_importer_dialog)
        btn_replay.pack(side="right", padx=2)

        btn_ots = ctk.CTkButton(f, text="🖼️ OTS PNG", width=85, fg_color="#d35400", command=self._export_ots_action)
        btn_ots.pack(side="right", padx=2)

        btn_legal = ctk.CTkButton(f, text="⚖️ Legal", width=70, fg_color="#16a085", command=self._check_legality_action)
        btn_legal.pack(side="right", padx=2)

        btn_cloud = ctk.CTkButton(f, text="☁️ Cloud", width=65, fg_color="#7f8c8d", command=self._open_cloud_sync_dialog)
        btn_cloud.pack(side="right", padx=2)

        # Saved Teams Selector
        team_names = list(self.saved_teams.keys())
        self.team_combo = ctk.CTkComboBox(f, values=team_names if team_names else ["Default Team"], width=150, command=self._on_saved_team_selected)
        if team_names:
            self.team_combo.set(team_names[0])
        self.team_combo.pack(side="right", padx=4)

        btn_save = ctk.CTkButton(f, text="💾", width=34, fg_color="#2980b9", command=self._save_current_team_action)
        btn_save.pack(side="right", padx=1)

    # ==========================================
    # Live Team Report Card Strip
    # ==========================================
    def _build_report_strip(self):
        f = self.report_strip_frame

        # Synergy Badge & Progress
        self.synergy_label = ctk.CTkLabel(f, text="Synergy: 85/100", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2ecc71")
        self.synergy_label.pack(side="left", padx=(15, 6))
        self.synergy_bar = ctk.CTkProgressBar(f, width=90, height=10, progress_color="#2ecc71")
        self.synergy_bar.pack(side="left", padx=4)
        self.synergy_bar.set(0.85)

        # Offense / Defense Rating
        self.offense_def_label = ctk.CTkLabel(f, text="Offense: 75 | Bulk: 80", font=ctk.CTkFont(size=12))
        self.offense_def_label.pack(side="left", padx=14)

        # Pilot Difficulty Stars
        self.difficulty_label = ctk.CTkLabel(f, text="Difficulty: ★★★☆☆ (Balanced)", font=ctk.CTkFont(size=12), text_color="#f39c12")
        self.difficulty_label.pack(side="left", padx=14)

        # Board Control Index
        self.board_control_label = ctk.CTkLabel(f, text="Board Control: 78/100", font=ctk.CTkFont(size=12), text_color="#9b59b6")
        self.board_control_label.pack(side="left", padx=14)

        # CTS Surprise vs OTS Resiliency Badges
        self.resiliency_label = ctk.CTkLabel(f, text="OTS Bo3: 84/100 | CTS Surprise: 62/100", font=ctk.CTkFont(size=12), text_color="#3498db")
        self.resiliency_label.pack(side="left", padx=14)

    # ==========================================
    # 6 Pokémon Visual Cards Strip
    # ==========================================
    def _build_cards_strip(self):
        self.card_widgets = []
        for i in range(6):
            card = ctk.CTkFrame(
                self.cards_strip_frame,
                fg_color="#1c202c" if i == 0 else "#161922",
                border_width=2 if i == 0 else 1,
                border_color="#5865f2" if i == 0 else "#2d3345",
                corner_radius=8,
                cursor="hand2"
            )
            card.pack(side="left", fill="both", expand=True, padx=4, pady=4)
            card.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            # Inner content
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(side="top", fill="x", padx=4, pady=(2, 0))
            top_row.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            slot_lbl = ctk.CTkLabel(top_row, text=f"#{i+1}", font=ctk.CTkFont(size=10, weight="bold"), text_color="#7f8c8d")
            slot_lbl.pack(side="left")
            slot_lbl.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            name_lbl = ctk.CTkLabel(top_row, text="Species", font=ctk.CTkFont(size=12, weight="bold"), text_color="white")
            name_lbl.pack(side="left", padx=4)
            name_lbl.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            # Sprite label
            sprite_lbl = ctk.CTkLabel(card, text="", width=48, height=48)
            sprite_lbl.pack(side="left", padx=(6, 2), pady=2)
            sprite_lbl.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            # Details block
            details_f = ctk.CTkFrame(card, fg_color="transparent")
            details_f.pack(side="left", fill="both", expand=True, padx=2, pady=2)
            details_f.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            item_lbl = ctk.CTkLabel(details_f, text="Item: None", font=ctk.CTkFont(size=10), anchor="w")
            item_lbl.pack(fill="x")
            item_lbl.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            ab_lbl = ctk.CTkLabel(details_f, text="Ability: None", font=ctk.CTkFont(size=10), anchor="w")
            ab_lbl.pack(fill="x")
            ab_lbl.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            tera_lbl = ctk.CTkLabel(details_f, text="Tera: None", font=ctk.CTkFont(size=10), text_color="#f1c40f", anchor="w")
            tera_lbl.pack(fill="x")
            tera_lbl.bind("<Button-1>", lambda e, slot=i: self._select_slot(slot))

            self.card_widgets.append({
                "frame": card,
                "name": name_lbl,
                "sprite": sprite_lbl,
                "item": item_lbl,
                "ability": ab_lbl,
                "tera": tera_lbl
            })

    def _select_slot(self, slot: int):
        self.selected_slot = slot
        for idx, cw in enumerate(self.card_widgets):
            if idx == slot:
                cw["frame"].configure(fg_color="#1e2230", border_width=2, border_color="#5865f2")
            else:
                cw["frame"].configure(fg_color="#161922", border_width=1, border_color="#2d3345")
        self._load_slot_into_builder(slot)

    # ==========================================
    # Docked Co-Pilot Sidebar
    # ==========================================
    def _build_copilot_sidebar(self):
        f = self.copilot_frame

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(side="top", fill="x", padx=10, pady=(10, 4))
        title = ctk.CTkLabel(header, text="🤖 STUDIO CO-PILOT", font=ctk.CTkFont(size=14, weight="bold"), text_color="#5865f2")
        title.pack(side="left")
        status = ctk.CTkLabel(header, text="● Offline Ready", font=ctk.CTkFont(size=10), text_color="#2ecc71")
        status.pack(side="right")

        # Chat Text Display
        self.copilot_text = ctk.CTkTextbox(f, wrap="word", font=ctk.CTkFont(size=12), fg_color="#14161f")
        self.copilot_text.pack(side="top", fill="both", expand=True, padx=8, pady=4)
        self.copilot_text.insert("end", (
            "Welcome to **VGC & Showdown Studio Co-Pilot**!\n\n"
            "I can audit synergy, discover rogue combos, optimize EV benchmarks, and find off-meta counters.\n\n"
            "Click a prompt chip below or type your request:\n"
        ))
        self.copilot_text.configure(state="disabled")

        # Quick Action Chips
        chips_frame = ctk.CTkFrame(f, fg_color="transparent")
        chips_frame.pack(side="top", fill="x", padx=8, pady=2)

        chips = [
            ("Rate Synergy", "rate my synergy"),
            ("Board Control", "check board control"),
            ("Off-Meta Gems", "suggest off-meta counters under 5% usage"),
            ("Find Combos", "discover weird combos for my team"),
            ("OTS Resiliency", "check OTS Bo3 resiliency")
        ]
        for label, cmd in chips:
            btn = ctk.CTkButton(
                chips_frame, text=label, font=ctk.CTkFont(size=10),
                height=22, fg_color="#2c3e50", hover_color="#34495e",
                command=lambda c=cmd: self._send_copilot_query(c)
            )
            btn.pack(side="left", padx=2, pady=2)

        # Input Row
        input_row = ctk.CTkFrame(f, fg_color="transparent")
        input_row.pack(side="bottom", fill="x", padx=8, pady=(4, 8))

        self.copilot_entry = ctk.CTkEntry(input_row, placeholder_text="Ask Co-Pilot anything...", font=ctk.CTkFont(size=12))
        self.copilot_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.copilot_entry.bind("<Return>", lambda e: self._send_copilot_query(self.copilot_entry.get()))

        send_btn = ctk.CTkButton(input_row, text="Send", width=55, fg_color="#5865f2", command=lambda: self._send_copilot_query(self.copilot_entry.get()))
        send_btn.pack(side="right")

    def _send_copilot_query(self, query_text: str):
        q = query_text.strip()
        if not q:
            return
        self.copilot_entry.delete(0, "end")

        self.copilot_text.configure(state="normal")
        self.copilot_text.insert("end", f"\n\n**You**: {q}\n\n")
        self.copilot_text.insert("end", "**Co-Pilot**: Analyzing...\n")
        self.copilot_text.see("end")
        self.copilot_text.configure(state="disabled")

        def _bg():
            resp = self.copilot.process_query(q, self.current_team)
            self.after(0, lambda: self._append_copilot_response(resp))

        threading.Thread(target=_bg, daemon=True).start()

    def _append_copilot_response(self, text: str):
        self.copilot_text.configure(state="normal")
        # Remove placeholder line
        last_idx = self.copilot_text.index("end-2l")
        self.copilot_text.delete(last_idx, "end")
        self.copilot_text.insert("end", f"\n{text}\n")
        self.copilot_text.see("end")
        self.copilot_text.configure(state="disabled")

    # ==========================================
    # Tab 1: Team Builder
    # ==========================================
    def _build_tab_builder(self):
        tab = self.tab_builder

        # Top Control Row
        top_ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        top_ctrl.pack(side="top", fill="x", padx=12, pady=(10, 4))

        self.builder_slot_lbl = ctk.CTkLabel(top_ctrl, text="Editing Slot #1: Incineroar", font=ctk.CTkFont(size=15, weight="bold"))
        self.builder_slot_lbl.pack(side="left")

        # Species Entry & Autocomplete
        species_names = self.engine.get_all_pokemon_names()
        self.species_combo = ctk.CTkComboBox(top_ctrl, values=species_names[:60], width=200, command=self._on_builder_species_changed)
        self.species_combo.pack(side="left", padx=15)

        # Held Item
        item_names = self.engine.get_all_item_names()
        self.item_combo = ctk.CTkComboBox(top_ctrl, values=item_names[:50], width=180, command=self._on_builder_field_changed)
        self.item_combo.pack(side="left", padx=5)

        # Ability
        self.ability_combo = ctk.CTkComboBox(top_ctrl, values=["Intimidate", "Blaze"], width=160, command=self._on_builder_field_changed)
        self.ability_combo.pack(side="left", padx=5)

        # Tera Type
        self.tera_combo = ctk.CTkComboBox(top_ctrl, values=ALL_TYPES, width=120, command=self._on_builder_field_changed)
        self.tera_combo.pack(side="left", padx=5)

        # Nature
        nature_list = list(NATURES.keys())
        self.nature_combo = ctk.CTkComboBox(top_ctrl, values=nature_list, width=120, command=self._on_builder_field_changed)
        self.nature_combo.pack(side="left", padx=5)

        # Middle Content Split (Left: Moves & Stats, Right: Sliders & Live Calcs)
        content_split = ctk.CTkFrame(tab, fg_color="transparent")
        content_split.pack(side="top", fill="both", expand=True, padx=12, pady=6)

        # Left Column: 4 Moves
        left_col = ctk.CTkFrame(content_split, fg_color="#1b1d28", width=380, corner_radius=8)
        left_col.pack(side="left", fill="both", padx=(0, 6), pady=4)

        ctk.CTkLabel(left_col, text="4 MOVE SELECTIONS", font=ctk.CTkFont(size=13, weight="bold"), text_color="#5865f2").pack(anchor="w", padx=15, pady=(10, 6))

        all_moves = self.engine.get_all_move_names()
        self.move_combos = []
        for mi in range(4):
            mf = ctk.CTkFrame(left_col, fg_color="transparent")
            mf.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(mf, text=f"Move {mi+1}:", width=55, anchor="w").pack(side="left")
            mc = ctk.CTkComboBox(mf, values=all_moves[:60], width=260, command=lambda v, idx=mi: self._on_builder_move_changed(idx, v))
            mc.pack(side="left", padx=4)
            self.move_combos.append(mc)

        # Gimmick Transformation Toggle in Builder
        self.transform_switch = ctk.CTkSwitch(left_col, text="Battle Transformed (Palafin-Hero / Form-Change)", command=self._on_builder_field_changed)
        self.transform_switch.pack(anchor="w", padx=15, pady=(15, 6))

        # Right Column: EV / SP Sliders & Stat Progress
        right_col = ctk.CTkFrame(content_split, fg_color="#1b1d28", corner_radius=8)
        right_col.pack(side="right", fill="both", expand=True, padx=(6, 0), pady=4)

        slider_hdr = ctk.CTkFrame(right_col, fg_color="transparent")
        slider_hdr.pack(fill="x", padx=15, pady=(10, 4))
        self.ev_title_lbl = ctk.CTkLabel(slider_hdr, text="EV / STAT POINT ALLOCATION", font=ctk.CTkFont(size=13, weight="bold"), text_color="#5865f2")
        self.ev_title_lbl.pack(side="left")
        self.ev_total_lbl = ctk.CTkLabel(slider_hdr, text="Total: 508 / 510 EVs", font=ctk.CTkFont(size=13, weight="bold"), text_color="#2ecc71")
        self.ev_total_lbl.pack(side="right")

        # 6 Stat Sliders
        stats_order = [("HP", "hp"), ("Attack", "atk"), ("Defense", "def"), ("Sp. Atk", "spa"), ("Sp. Def", "spd"), ("Speed", "spe")]
        self.stat_sliders = {}
        self.stat_val_labels = {}
        self.stat_calc_labels = {}

        for label_text, skey in stats_order:
            row = ctk.CTkFrame(right_col, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=4)

            name_l = ctk.CTkLabel(row, text=label_text, width=70, anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
            name_l.pack(side="left")

            val_l = ctk.CTkLabel(row, text="0", width=42, anchor="e")
            val_l.pack(side="left", padx=4)
            self.stat_val_labels[skey] = val_l

            slider = ctk.CTkSlider(row, from_=0, to=252, number_of_steps=63, command=lambda v, s=skey: self._on_slider_moved(s, v))
            slider.pack(side="left", fill="x", expand=True, padx=8)
            self.stat_sliders[skey] = slider

            calc_l = ctk.CTkLabel(row, text="Stat: 100", width=80, anchor="e", text_color="#3498db", font=ctk.CTkFont(size=12, weight="bold"))
            calc_l.pack(side="right")
            self.stat_calc_labels[skey] = calc_l

    def _load_slot_into_builder(self, slot: int):
        if slot >= len(self.current_team):
            return
        mon = self.current_team[slot]
        self.builder_slot_lbl.configure(text=f"Editing Slot #{slot+1}: {mon.get('name', 'Unknown')}")
        self.species_combo.set(mon.get("name", "Incineroar"))
        self.item_combo.set(mon.get("item", "None") or "None")
        self.ability_combo.set(mon.get("ability", "None") or "None")
        self.tera_combo.set(mon.get("tera_type", "Normal") or "Normal")
        self.nature_combo.set(mon.get("nature", "Hardy") or "Hardy")

        moves = mon.get("moves", [])
        for mi in range(4):
            mv = moves[mi] if mi < len(moves) else ""
            self.move_combos[mi].set(mv)

        # Refresh Sliders
        is_sp = self.is_sp_mode or mon.get("is_sp", False)
        max_val = 32 if is_sp else 252
        steps = 32 if is_sp else 63

        for skey, slider in self.stat_sliders.items():
            slider.configure(to=max_val, number_of_steps=steps)
            val = mon.get("evs", {}).get(skey, 0)
            slider.set(val)
            self.stat_val_labels[skey].configure(text=str(val))

        self._update_builder_calculations()

    def _on_slider_moved(self, stat_key: str, value: float):
        mon = self.current_team[self.selected_slot]
        is_sp = self.is_sp_mode or mon.get("is_sp", False)
        int_val = int(round(value))
        if not is_sp:
            int_val = (int_val // 4) * 4
        mon.setdefault("evs", {})[stat_key] = int_val
        self.stat_val_labels[stat_key].configure(text=str(int_val))
        self._update_builder_calculations()
        self._refresh_cards_strip()
        self._refresh_report_strip()

    def _update_builder_calculations(self):
        mon = self.current_team[self.selected_slot]
        is_sp = self.is_sp_mode or mon.get("is_sp", False)
        evs = mon.get("evs", {})
        total_pts = sum(evs.values())
        max_legal = 66 if is_sp else 510
        unit = "SPs" if is_sp else "EVs"

        self.ev_title_lbl.configure(text=f"{'CHAMPIONS STAT POINTS' if is_sp else 'CLASSIC EV'} ALLOCATION")
        color = "#2ecc71" if total_pts <= max_legal else "#e74c3c"
        self.ev_total_lbl.configure(text=f"Total: {total_pts} / {max_legal} {unit}", text_color=color)

        # Calculate final level 50 stats
        stats, _, _ = resolve_form_change(mon.get("name", ""), is_transformed=self.transform_switch.get())
        for skey in ["hp", "atk", "def", "spa", "spd", "spe"]:
            base = stats.get(skey, 100)
            calc = calculate_stat(base, skey, evs.get(skey, 0), 31, mon.get("nature", "Hardy"), 50, is_sp)
            self.stat_calc_labels[skey].configure(text=f"Stat: {calc}")

    def _on_builder_species_changed(self, new_species: str):
        mon = self.current_team[self.selected_slot]
        mon["name"] = new_species
        dex = self.engine.get_pokemon(new_species) or BUILTIN_POKEMON.get(self.engine._clean_key(new_species), {})
        
        # Populate abilities
        ab_list = list(dex.get("abilities", {}).values())
        if ab_list:
            self.ability_combo.configure(values=ab_list)
            self.ability_combo.set(ab_list[0])
            mon["ability"] = ab_list[0]

        self._update_builder_calculations()
        self._refresh_cards_strip()
        self._refresh_report_strip()

    def _on_builder_move_changed(self, move_idx: int, move_name: str):
        mon = self.current_team[self.selected_slot]
        moves = mon.setdefault("moves", [])
        while len(moves) <= move_idx:
            moves.append("")
        moves[move_idx] = move_name
        self._refresh_cards_strip()
        self._refresh_report_strip()

    def _on_builder_field_changed(self, *args):
        mon = self.current_team[self.selected_slot]
        mon["item"] = self.item_combo.get()
        mon["ability"] = self.ability_combo.get()
        mon["tera_type"] = self.tera_combo.get()
        mon["nature"] = self.nature_combo.get()
        self._update_builder_calculations()
        self._refresh_cards_strip()
        self._refresh_report_strip()

    # ==========================================
    # Tab 2: Rogue Combo Lab
    # ==========================================
    def _build_tab_combo(self):
        tab = self.tab_combo

        # Top controls
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.pack(side="top", fill="x", padx=12, pady=10)

        ctk.CTkLabel(top_bar, text="Anchor Pokémon:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=4)
        self.combo_anchor_combo = ctk.CTkComboBox(top_bar, values=[m.get("name", "Incineroar") for m in self.current_team], width=160)
        self.combo_anchor_combo.pack(side="left", padx=4)

        btn_mine = ctk.CTkButton(top_bar, text="⚡ Discover Rogue Synergies", fg_color="#e67e22", command=self._run_combo_mining)
        btn_mine.pack(side="left", padx=8)

        btn_evolve = ctk.CTkButton(top_bar, text="🧬 Run 40-Gen Evolutionary Search", fg_color="#9b59b6", command=self._run_evolutionary_search)
        btn_evolve.pack(side="left", padx=8)

        self.combo_progress = ctk.CTkProgressBar(top_bar, width=180)
        self.combo_progress.pack(side="left", padx=8)
        self.combo_progress.set(0)

        self.btn_apply_evolved = ctk.CTkButton(top_bar, text="Apply Evolved Roster", fg_color="#27ae60", state="disabled", command=self._apply_evolved_team)
        self.btn_apply_evolved.pack(side="right", padx=6)

        # Output text
        self.combo_text = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=13))
        self.combo_text.pack(fill="both", expand=True, padx=12, pady=8)
        self.combo_text.insert("end", "Select an anchor Pokémon and click 'Discover Rogue Synergies' or 'Run 40-Gen Evolutionary Search'.")

    def _run_combo_mining(self):
        anchor = self.combo_anchor_combo.get()
        combos = self.miner.discover_combos(anchor)
        self.combo_text.delete("1.0", "end")
        self.combo_text.insert("end", f"=== 🔬 ROGUE SYNERGIES & INTERACTIONS FOR {anchor.upper()} ===\n\n")
        for idx, c in enumerate(combos, 1):
            self.combo_text.insert("end", f"[{idx}] {c['combo_name']} (Viability: {c['viability_score']}/100)\n")
            self.combo_text.insert("end", f"   Category:   {c['category']}\n")
            self.combo_text.insert("end", f"   Partner:    {c.get('partner')} holding {c.get('partner_item', 'Item')}\n")
            self.combo_text.insert("end", f"   Tactics:    {c['tactical_breakdown']}\n")
            self.combo_text.insert("end", f"   Turn 1:     {c['script']}\n\n")

    def _run_evolutionary_search(self):
        anchor = self.combo_anchor_combo.get()
        anchor_mon = self.current_team[0]
        self.combo_text.delete("1.0", "end")
        self.combo_text.insert("end", f"🧬 Starting 40-Generation Genetic Algorithm Optimization around {anchor}...\n\n")
        self.combo_progress.set(0)

        def _bg():
            def _prog(gen, score, team):
                pct = gen / 40.0
                self.after(0, lambda: self.combo_progress.set(pct))
                if gen % 10 == 0 or gen == 40:
                    self.after(0, lambda: self.combo_text.insert("end", f"Generation {gen}/40: Best Fitness = {score}%\n"))

            best_team, best_score, _ = self.mutator.run_evolutionary_search(
                anchor_mon, num_generations=40, population_size=10, progress_callback=_prog
            )
            self.last_evolved_team = best_team
            self.after(0, lambda: self._on_evolution_done(best_score, best_team))

        threading.Thread(target=_bg, daemon=True).start()

    def _on_evolution_done(self, best_score: float, team: List[Dict[str, Any]]):
        self.btn_apply_evolved.configure(state="normal")
        paste = export_showdown_paste(team)
        self.combo_text.insert("end", f"\n🏆 EVOLUTION COMPLETED! Simulated Win Rate: {best_score}%\n\n{paste}\n")

    def _apply_evolved_team(self):
        if hasattr(self, "last_evolved_team") and self.last_evolved_team:
            self.current_team = self.last_evolved_team
            self._refresh_all_views()
            messagebox.showinfo("Success", "Evolved Anti-Meta Team loaded into Team Builder!")

    # ==========================================
    # Tab 3: Overall Plan & Leads
    # ==========================================
    def _build_tab_plan(self):
        tab = self.tab_plan
        self.plan_text = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=13))
        self.plan_text.pack(fill="both", expand=True, padx=12, pady=12)

    def _refresh_plan_tab(self):
        plan = self.gameplan.generate_overall_plan(self.current_team)
        self.plan_text.delete("1.0", "end")
        self.plan_text.insert("end", "=== 📋 DYNAMIC TOURNAMENT TEAM GAMEPLAN ===\n\n")
        self.plan_text.insert("end", f"🎯 Primary Win Condition:\n   {plan['primary_win_con']}\n\n")
        self.plan_text.insert("end", f"🛡️ Secondary Win Condition:\n   {plan['secondary_win_con']}\n\n")
        self.plan_text.insert("end", f"⚡ Speed Control Gameplan:\n   {plan['speed_control_plan']}\n\n")

        self.plan_text.insert("end", "--- TOP LEAD PAIRS & TURN-1 SCRIPTS ---\n")
        for idx, lp in enumerate(plan.get("leads", []), 1):
            self.plan_text.insert("end", f"Lead Pair #{idx}: {lp['pair'][0]} + {lp['pair'][1]} ({lp['name']})\n")
            self.plan_text.insert("end", f" -> Turn 1 Script: {lp['turn1_script']}\n")
            self.plan_text.insert("end", f" -> Recommended Back-2: {', '.join(lp['back2'])}\n")
            self.plan_text.insert("end", f" -> Ideal Target: {lp['preferred_against']}\n\n")

        self.plan_text.insert("end", "--- BEST-OF-3 OTS ADAPTATIONS (GAME 2 & GAME 3) ---\n")
        for b in plan.get("bo3_adaptations", []):
            self.plan_text.insert("end", f"[{b['phase']}]\n{b['advice']}\n\n")

        self.plan_text.insert("end", "--- SPECIFIC COUNTER-GAMEPLANS ---\n")
        for cg in plan.get("counter_gameplans", []):
            self.plan_text.insert("end", f"{cg['matchup']}:\n{cg['gameplan']}\n\n")

    # ==========================================
    # Tab 4: EV/SP Optimizer
    # ==========================================
    def _build_tab_optimizer(self):
        tab = self.tab_optimizer

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(side="top", fill="x", padx=12, pady=10)

        # Creep Speed Tool
        creep_box = ctk.CTkFrame(row, fg_color="#1c202c", corner_radius=8)
        creep_box.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=4)
        ctk.CTkLabel(creep_box, text="⚡ SPEED CREEP OPTIMIZER", font=ctk.CTkFont(size=13, weight="bold"), text_color="#f1c40f").pack(padx=10, pady=8)

        ctk.CTkLabel(creep_box, text="Select Opposing Target to Creep +1:").pack(padx=10, pady=2)
        self.opt_speed_target = ctk.CTkComboBox(creep_box, values=["Incineroar", "Rillaboom", "Urshifu-Rapid-Strike", "Flutter Mane", "Kingambit", "Farigiraf"])
        self.opt_speed_target.pack(padx=10, pady=4)

        btn_calc_creep = ctk.CTkButton(creep_box, text="Calculate Speed Benchmark", fg_color="#2980b9", command=self._run_speed_creep_calc)
        btn_calc_creep.pack(padx=10, pady=8)
        self.creep_res_lbl = ctk.CTkLabel(creep_box, text="", wraplength=320)
        self.creep_res_lbl.pack(padx=10, pady=4)

        # OHKO Optimizer Tool
        ohko_box = ctk.CTkFrame(row, fg_color="#1c202c", corner_radius=8)
        ohko_box.pack(side="right", fill="both", expand=True, padx=(6, 0), pady=4)
        ctk.CTkLabel(ohko_box, text="💥 GUARANTEED OHKO OPTIMIZER", font=ctk.CTkFont(size=13, weight="bold"), text_color="#e74c3c").pack(padx=10, pady=8)

        ctk.CTkLabel(ohko_box, text="Target Standard Bulk Species:").pack(padx=10, pady=2)
        self.opt_ohko_target = ctk.CTkComboBox(ohko_box, values=["Incineroar", "Rillaboom", "Flutter Mane", "Urshifu-Rapid-Strike", "Kingambit"])
        self.opt_ohko_target.pack(padx=10, pady=4)

        btn_calc_ohko = ctk.CTkButton(ohko_box, text="Calculate 16/16 OHKO EVs/SP", fg_color="#c0392b", command=self._run_ohko_calc)
        btn_calc_ohko.pack(padx=10, pady=8)
        self.ohko_res_lbl = ctk.CTkLabel(ohko_box, text="", wraplength=320)
        self.ohko_res_lbl.pack(padx=10, pady=4)

    def _run_speed_creep_calc(self):
        target = self.opt_speed_target.get()
        active_mon = self.current_team[self.selected_slot]
        res = self.benchmarks.optimize_speed_creep(active_mon, target)
        self.creep_res_lbl.configure(text=res["desc"])

    def _run_ohko_calc(self):
        target = self.opt_ohko_target.get()
        active_mon = self.current_team[self.selected_slot]
        mv = active_mon.get("moves", ["Moonblast"])[0] if active_mon.get("moves") else "Moonblast"
        res = self.benchmarks.optimize_ohko_punish(active_mon, target, mv)
        self.ohko_res_lbl.configure(text=f"Using {mv}: {res['desc']}")

    # ==========================================
    # Tab 5: Type Coverage Matrix
    # ==========================================
    def _build_tab_matrix(self):
        tab = self.tab_matrix
        self.matrix_text = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=12))
        self.matrix_text.pack(fill="both", expand=True, padx=12, pady=12)

    def _refresh_matrix_tab(self):
        self.matrix_text.delete("1.0", "end")
        self.matrix_text.insert("end", "=== 🛡️ 18-TYPE DEFENSIVE WEAKNESS & OFFENSIVE COVERAGE MATRIX ===\n\n")

        # Table Header
        self.matrix_text.insert("end", f"{'Type':<12} | " + " | ".join(f"{m.get('name', 'P')[:8]:<8}" for m in self.current_team) + " | Team Verdict\n")
        self.matrix_text.insert("end", "-" * 88 + "\n")

        for t in ALL_TYPES:
            if t == "Stellar":
                continue
            row_mults = []
            weak_count = 0
            resist_count = 0
            immune_count = 0

            for m in self.current_team:
                dex = self.engine.get_pokemon(m.get("name", "")) or BUILTIN_POKEMON.get(self.engine._clean_key(m.get("name", "")), {})
                types = dex.get("types", ["Normal"])
                if m.get("is_tera", False) and m.get("tera_type"):
                    types = [m.get("tera_type")]
                mult = get_type_effectiveness(t, types)
                row_mults.append(f"{mult:<8.1f}")
                if mult > 1.0: weak_count += 1
                elif mult == 0.0: immune_count += 1
                elif mult < 1.0: resist_count += 1

            verdict = ""
            if weak_count >= 3:
                verdict = f"⚠️ Critical Hole ({weak_count}x Weak)"
            elif immune_count > 0:
                verdict = f"✅ Immune ({immune_count}x)"
            elif resist_count > weak_count:
                verdict = f"🛡️ Solid Resistance ({resist_count}x)"
            else:
                verdict = "Neutral"

            self.matrix_text.insert("end", f"{t:<12} | " + " | ".join(row_mults) + f" | {verdict}\n")

    # ==========================================
    # Tab 6: Matchup & Threat Simulator
    # ==========================================
    def _build_tab_simulator(self):
        tab = self.tab_simulator

        top_ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        top_ctrl.pack(side="top", fill="x", padx=12, pady=8)

        btn_run = ctk.CTkButton(top_ctrl, text="⚔️ Run Monte Carlo Tournament Simulation", fg_color="#5865f2", command=self._run_simulation)
        btn_run.pack(side="left", padx=4)

        self.sim_status_lbl = ctk.CTkLabel(top_ctrl, text="Ready to simulate against active meta archetypes.")
        self.sim_status_lbl.pack(side="left", padx=15)

        # Output Text
        self.sim_text = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=13))
        self.sim_text.pack(fill="both", expand=True, padx=12, pady=8)

    def _run_simulation(self):
        self.sim_status_lbl.configure(text="Simulating 240+ Monte Carlo battles across archetypes...")
        self.sim_text.delete("1.0", "end")

        def _bg():
            match_res = self.simulator.analyze_matchup_spread(self.current_team)
            threats = self.simulator.scan_threats(self.current_team, limit=12)
            self.after(0, lambda: self._on_sim_done(match_res, threats))

        threading.Thread(target=_bg, daemon=True).start()

    def _on_sim_done(self, match_res: Dict[str, Any], threats: List[Dict[str, Any]]):
        self.sim_status_lbl.configure(text="Simulation Complete!")
        t = self.sim_text
        t.insert("end", "=== 🏆 MONTE CARLO MATCHUP SPREAD ANALYSIS ===\n\n")

        for tier in ["Favored", "Slight Edge", "Even", "Unfavorable"]:
            items = match_res.get(tier, [])
            t.insert("end", f"--- {tier.upper()} MATCHUPS ({len(items)}) ---\n")
            for item in items:
                t.insert("end", f"• {item['archetype']}: {item['win_rate']}% Win Rate\n")
                t.insert("end", f"  Explanation: {item['explanation']}\n\n")

        t.insert("end", "\n=== ⚠️ BAD POKÉMON THREAT SCANNER (TOP 12 DANGEROUS FOES) ===\n\n")
        for th in threats:
            t.insert("end", f"[{th['status'].upper()}] {th['name']} (Meta Usage: {th['usage_pct']}% | Danger Score: {th['danger_score']}/100)\n")
            checks_str = ", ".join(th['checks']) if th['checks'] else "No clean counter - relies on Tera/positioning"
            t.insert("end", f"   Threatens {th['ohko_threat_count']} members of your roster. Checks on your team: {checks_str}\n\n")

    # ==========================================
    # Tab 7: Damage Calc
    # ==========================================
    def _build_tab_damage(self):
        tab = self.tab_damage

        # Split pane: Attacker, Defender, Field & Results
        ctrl_f = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl_f.pack(side="top", fill="x", padx=12, pady=8)

        # Attacker Box
        att_box = ctk.CTkFrame(ctrl_f, fg_color="#1c202c", corner_radius=8)
        att_box.pack(side="left", fill="both", expand=True, padx=(0, 4), pady=4)
        ctk.CTkLabel(att_box, text="ATTACKER", font=ctk.CTkFont(size=13, weight="bold"), text_color="#e74c3c").pack(pady=4)

        all_pkmn = self.engine.get_all_pokemon_names()
        self.calc_att_mon = ctk.CTkComboBox(att_box, values=all_pkmn[:60], width=180)
        self.calc_att_mon.set("Flutter Mane")
        self.calc_att_mon.pack(pady=3)

        all_moves = self.engine.get_all_move_names()
        self.calc_att_move = ctk.CTkComboBox(att_box, values=all_moves[:60], width=180)
        self.calc_att_move.set("Moonblast")
        self.calc_att_move.pack(pady=3)

        self.calc_att_item = ctk.CTkComboBox(att_box, values=self.engine.get_all_item_names()[:40], width=180)
        self.calc_att_item.set("Choice Specs")
        self.calc_att_item.pack(pady=3)

        self.calc_att_tera = ctk.CTkCheckBox(att_box, text="Terastallized (Tera Fairy)")
        self.calc_att_tera.pack(pady=3)

        # Defender Box
        def_box = ctk.CTkFrame(ctrl_f, fg_color="#1c202c", corner_radius=8)
        def_box.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        ctk.CTkLabel(def_box, text="DEFENDER", font=ctk.CTkFont(size=13, weight="bold"), text_color="#3498db").pack(pady=4)

        self.calc_def_mon = ctk.CTkComboBox(def_box, values=all_pkmn[:60], width=180)
        self.calc_def_mon.set("Incineroar")
        self.calc_def_mon.pack(pady=3)

        self.calc_def_item = ctk.CTkComboBox(def_box, values=self.engine.get_all_item_names()[:40], width=180)
        self.calc_def_item.set("Sitrus Berry")
        self.calc_def_item.pack(pady=3)

        self.calc_def_tera = ctk.CTkCheckBox(def_box, text="Tera Grass")
        self.calc_def_tera.pack(pady=3)

        self.calc_def_dynamax = ctk.CTkCheckBox(def_box, text="Dynamax (2x HP)")
        self.calc_def_dynamax.pack(pady=3)

        # Field Toggles Box
        field_box = ctk.CTkFrame(ctrl_f, fg_color="#1c202c", corner_radius=8)
        field_box.pack(side="right", fill="both", expand=True, padx=(4, 0), pady=4)
        ctk.CTkLabel(field_box, text="FIELD CONDITIONS", font=ctk.CTkFont(size=13, weight="bold"), text_color="#f39c12").pack(pady=4)

        self.calc_weather = ctk.CTkComboBox(field_box, values=["None", "Sun", "Rain", "Snow", "Sandstorm"], width=130)
        self.calc_weather.set("None")
        self.calc_weather.pack(pady=2)

        self.calc_terrain = ctk.CTkComboBox(field_box, values=["None", "Electric", "Grassy", "Psychic", "Misty"], width=130)
        self.calc_terrain.set("None")
        self.calc_terrain.pack(pady=2)

        self.calc_intimidate = ctk.CTkCheckBox(field_box, text="Intimidate (-1 Atk)")
        self.calc_intimidate.pack(pady=2)

        self.calc_screens = ctk.CTkCheckBox(field_box, text="Screens / Aurora Veil")
        self.calc_screens.pack(pady=2)

        # Calculate Button & Output
        btn_calc = ctk.CTkButton(tab, text="💥 Calculate 16-Roll Damage", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#e74c3c", command=self._run_damage_calc)
        btn_calc.pack(padx=12, pady=6)

        self.calc_output_text = ctk.CTkTextbox(tab, wrap="word", height=180, font=ctk.CTkFont(size=13))
        self.calc_output_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    def _run_damage_calc(self):
        att = {
            "name": self.calc_att_mon.get(),
            "item": self.calc_att_item.get(),
            "nature": "Timid",
            "evs": {"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252},
            "is_tera": self.calc_att_tera.get(),
            "tera_type": "Fairy"
        }
        df = {
            "name": self.calc_def_mon.get(),
            "item": self.calc_def_item.get(),
            "nature": "Careful",
            "evs": {"hp": 252, "atk": 4, "def": 156, "spa": 0, "spd": 96, "spe": 4},
            "is_tera": self.calc_def_tera.get(),
            "tera_type": "Grass",
            "is_dynamax": self.calc_def_dynamax.get()
        }
        field = {
            "weather": self.calc_weather.get(),
            "terrain": self.calc_terrain.get(),
            "intimidate": self.calc_intimidate.get(),
            "light_screen": self.calc_screens.get(),
            "reflect": self.calc_screens.get(),
            "is_doubles": True
        }

        calc = calculate_damage(att, df, self.calc_att_move.get(), field)
        t = self.calc_output_text
        t.delete("1.0", "end")
        t.insert("end", f"=== 16-ROLL DAMAGE CALCULATION RESULT ===\n\n")
        t.insert("end", f"{calc['desc']}\n\n")
        t.insert("end", f"Defender Total HP: {calc['defender_hp']} HP\n")
        t.insert("end", f"16 Random Rolls (85%-100%): {calc['rolls']}\n")
        t.insert("end", f"Damage Spread: {calc['min_damage']} - {calc['max_damage']} ({calc['min_pct']}% - {calc['max_pct']}%)\n")
        t.insert("end", f"OHKO Chance: {calc['ohko_chance']}%\n")
        t.insert("end", f"2HKO Chance: {calc['two_hko_chance']}%\n")

    # ==========================================
    # Tab 8: Speed Tiers
    # ==========================================
    def _build_tab_speed(self):
        tab = self.tab_speed
        self.speed_text = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=13))
        self.speed_text.pack(fill="both", expand=True, padx=12, pady=12)

    def _refresh_speed_tab(self):
        t = self.speed_text
        t.delete("1.0", "end")
        t.insert("end", "=== 🏁 COMPETITIVE SPEED TIER LADDER (LEVEL 50) ===\n\n")

        # Compile list of team members and meta benchmarks
        speed_entries = []
        for m in self.current_team:
            stats, _, _ = resolve_form_change(m.get("name", ""))
            raw_spe = calculate_stat(stats.get("spe", 100), "spe", m.get("evs", {}).get("spe", 0), 31, m.get("nature", "Hardy"), 50, m.get("is_sp", False))
            speed_entries.append((raw_spe, f"⭐ YOUR TEAM: {m.get('name')} (Neutral)", True))
            speed_entries.append((int(raw_spe * 2), f"⚡ YOUR TEAM: {m.get('name')} (Tailwind / +2)", True))

        # Add top meta benchmarks
        benchmarks = [
            (205, "Timid Booster Energy Flutter Mane (+1 Spe)"),
            (200, "Jolly Max Speed Chien-Pao / Weavile"),
            (150, "Jolly Max Speed Urshifu-Rapid-Strike"),
            (145, "Modest Max Speed Chi-Yu"),
            (117, "Adamant 252 Spe Rillaboom"),
            (80, "Careful Standard 4 Spe Incineroar"),
            (49, "Min Speed Bloodmoon Ursaluna"),
            (22, "Min Speed Quiet Torkoal (Trick Room King)"),
        ]
        for spe, desc in benchmarks:
            speed_entries.append((spe, desc, False))

        speed_entries.sort(key=lambda x: x[0], reverse=True)

        for spe, label, is_mine in speed_entries:
            prefix = ">>> " if is_mine else "    "
            t.insert("end", f"{prefix}{spe:>4} Spe | {label}\n")

    # ==========================================
    # Tab 9: Tournament Explorer
    # ==========================================
    def _build_tab_tournament(self):
        tab = self.tab_tournament
        self.tourney_text = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=13))
        self.tourney_text.pack(fill="both", expand=True, padx=12, pady=12)

    def _refresh_tournament_tab(self):
        t = self.tourney_text
        t.delete("1.0", "end")
        t.insert("end", "=== 🌐 RECENT TOURNAMENT ROSTERS & POKEPASTES ===\n\n")

        rosters = self.db.get_tournament_teams(self.active_format_id)
        if not rosters:
            rosters = self.db.get_tournament_teams()

        for r in rosters:
            t.insert("end", f"🏆 {r.get('tournament_name', 'Regional')} - {r.get('placement', 'Top Cut')}\n")
            t.insert("end", f"Trainer: {r.get('player_name')} | Date: {r.get('date')}\n")
            t.insert("end", "PokePaste Roster:\n")
            t.insert("end", f"{r.get('paste_text', '')}\n")
            t.insert("end", "=" * 70 + "\n\n")

    # ==========================================
    # Format & State Actions
    # ==========================================
    def _on_format_changed(self, selected_name: str):
        for f in self.formats_list:
            if f["name"] == selected_name:
                self.active_format_id = f["id"]
                self.is_sp_mode = bool(f.get("is_sp", False))
                self.active_gimmick = f.get("gimmick", "Standard/None")
                self.stat_mode_btn.configure(
                    text="Mode: Champions SP (0-32)" if self.is_sp_mode else "Mode: Classic EVs (0-252)",
                    fg_color="#8e44ad" if self.is_sp_mode else "#2980b9"
                )
                self.gimmick_combo.set(self.active_gimmick)
                self._init_sub_engines()
                self._refresh_all_views()
                break

    def _on_custom_format_set(self):
        cust_id = self.custom_fmt_entry.get().strip().lower()
        if not cust_id:
            return
        self.active_format_id = cust_id
        is_champions = "champion" in cust_id
        self.is_sp_mode = is_champions
        self.stat_mode_btn.configure(
            text="Mode: Champions SP (0-32)" if self.is_sp_mode else "Mode: Classic EVs (0-252)",
            fg_color="#8e44ad" if self.is_sp_mode else "#2980b9"
        )
        self._init_sub_engines()
        self._refresh_all_views()
        messagebox.showinfo("Format Updated", f"Active format set to custom Showdown ID: '{cust_id}'. Future generations ready!")

    def _toggle_stat_mode(self):
        self.is_sp_mode = not self.is_sp_mode
        self.stat_mode_btn.configure(
            text="Mode: Champions SP (0-32)" if self.is_sp_mode else "Mode: Classic EVs (0-252)",
            fg_color="#8e44ad" if self.is_sp_mode else "#2980b9"
        )
        for m in self.current_team:
            m["is_sp"] = self.is_sp_mode
        self._load_slot_into_builder(self.selected_slot)
        self._refresh_cards_strip()
        self._refresh_report_strip()

    def _on_gimmick_changed(self, val: str):
        self.active_gimmick = val

    def _on_anti_meta_toggled(self):
        self.anti_meta_mode = self.anti_meta_switch.get()
        if self.anti_meta_mode:
            self._send_copilot_query("suggest off-meta counters under 5% usage")

    def _on_saved_team_selected(self, team_name: str):
        if team_name in self.saved_teams:
            self.current_team_name = team_name
            self.current_team = self.saved_teams[team_name]
            self._refresh_all_views()

    def _save_current_team_action(self):
        dialog = ctk.CTkInputDialog(text="Enter Team Name:", title="Save Team")
        name = dialog.get_input()
        if name and name.strip():
            self.current_team_name = name.strip()
            self.teams_mgr.save_team(self.current_team_name, self.current_team)
            self.saved_teams = self.teams_mgr.load_all_teams()
            self.team_combo.configure(values=list(self.saved_teams.keys()))
            self.team_combo.set(self.current_team_name)
            messagebox.showinfo("Saved", f"Team '{self.current_team_name}' saved to data/saved_teams.json!")

    # ==========================================
    # Global Refresh Helpers
    # ==========================================
    def _refresh_all_views(self):
        self._refresh_cards_strip()
        self._refresh_report_strip()
        self._load_slot_into_builder(self.selected_slot)
        self._refresh_plan_tab()
        self._refresh_matrix_tab()
        self._refresh_speed_tab()
        self._refresh_tournament_tab()

    def _refresh_cards_strip(self):
        for idx in range(6):
            if idx < len(self.current_team):
                m = self.current_team[idx]
                cw = self.card_widgets[idx]
                cw["name"].configure(text=m.get("name", "Unknown"))
                cw["item"].configure(text=f"Item: {m.get('item', 'None') or 'None'}")
                cw["ability"].configure(text=f"Abil: {m.get('ability', 'None') or 'None'}")
                cw["tera"].configure(text=f"Tera: {m.get('tera_type', 'None') or 'None'}")

                # Load sprite async
                sp_img = self.sprite_loader.load_ctk_image_async(
                    m.get("name", ""), size=(44, 44),
                    on_loaded=lambda img, w=cw["sprite"]: w.configure(image=img)
                )
                cw["sprite"].configure(image=sp_img)

    def _refresh_report_strip(self):
        rep = self.analytics.generate_report_card(self.current_team)
        self.synergy_label.configure(text=f"Synergy: {rep['synergy_score']}/100")
        self.synergy_bar.set(rep["synergy_score"] / 100.0)
        self.offense_def_label.configure(text=f"Offense: {rep['offense_pressure']} | Bulk: {rep['defense_bulk']}")
        self.difficulty_label.configure(text=f"Difficulty: {rep['pilot_difficulty_stars']} ★ ({rep['pilot_difficulty_label']})")
        self.board_control_label.configure(text=f"Board Control: {rep['board_control_score']}/100")
        self.resiliency_label.configure(text=f"OTS Bo3: {rep['ots_resiliency_score']}/100 | CTS Surprise: {rep['cts_surprise_score']}/100")

    # ==========================================
    # Modal Dialogs (Showdown Paste, Replay, OTS, Legality, Cloud)
    # ==========================================
    def _open_showdown_paste_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("Universal Showdown / PokePaste Importer & Exporter")
        win.geometry("640x580")

        ctk.CTkLabel(win, text="Showdown Format Paste", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=10, pady=8)

        text_area = ctk.CTkTextbox(win, wrap="none", font=ctk.CTkFont(family="Consolas", size=12))
        text_area.pack(fill="both", expand=True, padx=12, pady=6)
        text_area.insert("end", export_showdown_paste(self.current_team, export_as_sp=self.is_sp_mode))

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=10)

        def _import():
            parsed = parse_showdown_paste(text_area.get("1.0", "end"), default_is_sp=self.is_sp_mode)
            if parsed:
                self.current_team = parsed[:6]
                self._refresh_all_views()
                win.destroy()
                messagebox.showinfo("Imported", f"Successfully imported {len(self.current_team)} Pokémon!")
            else:
                messagebox.showerror("Error", "Could not parse any valid Pokémon from paste.")

        ctk.CTkButton(btn_row, text="📥 Import into Builder", fg_color="#27ae60", command=_import).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📋 Copy to Clipboard", fg_color="#2980b9", command=lambda: [self.clipboard_clear(), self.clipboard_append(text_area.get('1.0', 'end')), messagebox.showinfo('Copied', 'Copied paste to clipboard!')]).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Close", fg_color="#7f8c8d", command=win.destroy).pack(side="right", padx=4)

    def _open_replay_importer_dialog(self):
        dialog = ctk.CTkInputDialog(text="Enter Showdown Replay URL\n(e.g. https://replay.pokemonshowdown.com/...):", title="Showdown Replay Importer")
        url = dialog.get_input()
        if url and url.strip():
            try:
                imported = parse_showdown_replay(url.strip(), self.db)
                if imported:
                    self.current_team = imported[:6]
                    self._refresh_all_views()
                    messagebox.showinfo("Replay Imported", f"Successfully extracted opponent roster ({len(imported)} Pokémon) and filled top meta spreads!")
                else:
                    messagebox.showwarning("Empty", "Could not extract opponent Pokémon from replay log.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to parse replay: {e}")

    def _export_ots_action(self):
        try:
            saved_p = export_ots_png(
                team=self.current_team,
                team_name=self.current_team_name,
                trainer_name="Trainer",
                format_label=self.fmt_combo.get()
            )
            messagebox.showinfo("OTS Exported", f"Tournament Open Team Sheet (OTS) saved cleanly to:\n{saved_p}")
            os.system(f'explorer /select,"{saved_p}"')
        except Exception as e:
            messagebox.showerror("Error", f"Could not export OTS PNG: {e}")

    def _check_legality_action(self):
        is_legal, issues, warnings = validate_tournament_roster(self.current_team, self.active_format_id)
        msg_lines = []
        if is_legal:
            msg_lines.append("✅ TOURNAMENT LEGAL ROSTER!\nThis roster complies with Species Clause, Item Clause, and standard limits.")
        else:
            msg_lines.append("❌ LEGALITY VIOLATIONS DETECTED:\n")
            for iss in issues:
                msg_lines.append(f" • {iss}")

        if warnings:
            msg_lines.append("\n⚠️ WARNINGS / INCOMPLETE SLOTS:\n")
            for w in warnings:
                msg_lines.append(f" • {w}")

        if is_legal:
            messagebox.showinfo("Tournament Legality Result", "\n".join(msg_lines))
        else:
            messagebox.showwarning("Tournament Legality Result", "\n".join(msg_lines))

    def _open_cloud_sync_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("GitHub Cloud DB Synchronization")
        win.geometry("450x260")

        ctk.CTkLabel(win, text="Pull Latest Pre-Scraped Database from GitHub", font=ctk.CTkFont(size=13, weight="bold")).pack(padx=10, pady=10)
        ctk.CTkLabel(win, text="Downloads vgc_meta.db directly in ~1s without opening web scrapers.").pack(padx=10, pady=2)

        user_entry = ctk.CTkEntry(win, placeholder_text="GitHub Username (default: giovafab)", width=280)
        user_entry.pack(padx=10, pady=6)
        user_entry.insert(0, "giovafab")

        repo_entry = ctk.CTkEntry(win, placeholder_text="Repository Name (default: vgc_studio)", width=280)
        repo_entry.pack(padx=10, pady=6)
        repo_entry.insert(0, "vgc_studio")

        status_lbl = ctk.CTkLabel(win, text="")
        status_lbl.pack(pady=4)

        def _do_pull():
            status_lbl.configure(text="Pulling latest database from GitHub main branch...")
            def _bg():
                ok = pull_cloud_db(user_entry.get().strip(), repo_entry.get().strip())
                if ok:
                    self.db = MetaDatabase.get_instance()
                    self._init_sub_engines()
                    self.after(0, lambda: [status_lbl.configure(text="Cloud Sync Successful!"), messagebox.showinfo("Success", "Updated local vgc_meta.db from GitHub!")])
                else:
                    self.after(0, lambda: status_lbl.configure(text="Could not reach GitHub raw repository."))
            threading.Thread(target=_bg, daemon=True).start()

        ctk.CTkButton(win, text="☁️ Pull Latest DB Now", fg_color="#2980b9", command=_do_pull).pack(pady=10)

def main():
    app = VGCStudioApp()
    app.mainloop()

if __name__ == "__main__":
    main()
