"""
VGC & Showdown Studio - Offline Co-Pilot Engine
Local rule/heuristic conversational assistant for rogue team building,
EV benchmark optimization, combo discovery, and board control audits.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple

from core.mechanics import ShowdownEngine, export_showdown_paste, BUILTIN_POKEMON
from core.combo_lab import MechanicInteractionMiner, EvolutionaryTeamMutator
from core.simulator import BattleSimulator
from core.planner import TeamAnalyticsEngine, TeamGameplanEngine, EVBenchmarkOptimizer
from scrapers.meta_fetcher import MetaDatabase

class StudioCopilot:
    def __init__(self, format_id: str = "gen9vgc2024regg"):
        self.format_id = format_id
        self.engine = ShowdownEngine.get_instance()
        self.db = MetaDatabase.get_instance()
        self.miner = MechanicInteractionMiner()
        self.analytics = TeamAnalyticsEngine(format_id)
        self.gameplan = TeamGameplanEngine(format_id)
        self.benchmarks = EVBenchmarkOptimizer(format_id)
        self.simulator = BattleSimulator(format_id)

    def set_format(self, format_id: str):
        self.format_id = format_id
        self.analytics = TeamAnalyticsEngine(format_id)
        self.gameplan = TeamGameplanEngine(format_id)
        self.benchmarks = EVBenchmarkOptimizer(format_id)
        self.simulator = BattleSimulator(format_id)

    def process_query(self, user_msg: str, current_team: List[Dict[str, Any]]) -> str:
        """Processes user natural language commands and returns formatted markdown."""
        msg = user_msg.strip().lower()

        # 1. Discover weird combos: "discover weird combos for [Pokemon]" or "find combos for [Pokemon]"
        m_combo = re.search(r"(?:discover|find|show|weird)?\s*combos?\s*(?:for|around)?\s*([a-zA-Z0-9_-]+)", msg)
        if "combo" in msg and m_combo:
            target = m_combo.group(1).strip()
            # If target was 'for' or empty, use first mon from team
            if target in ["for", "around", "my", "this", ""] and current_team:
                target = current_team[0].get("name", "Incineroar")
            elif target in ["for", "around", "my", "this", ""]:
                target = "Incineroar"
            
            combos = self.miner.discover_combos(target, limit=4)
            res = [f"### 🔬 Rogue Synergy & Mechanics Lab for **{target.capitalize()}**\n"]
            for c in combos:
                res.append(f"**⚡ {c['combo_name']}** (Viability: {c['viability_score']}/100)")
                res.append(f"- **Category**: {c['category']}")
                res.append(f"- **Partner**: `{c.get('partner')}` holding `{c.get('partner_item', 'Item')}`")
                res.append(f"- **Tactics**: {c['tactical_breakdown']}")
                res.append(f"- **Turn-1 Playbook**: `{c['script']}`\n")
            return "\n".join(res)

        # 2. Build anti-meta team: "build an anti-meta team around [Pokemon]"
        m_build = re.search(r"build\s*(?:an)?\s*anti[- ]?meta\s*team\s*(?:around)?\s*([a-zA-Z0-9_-]+)", msg)
        if m_build:
            anchor = m_build.group(1).strip()
            dex_entry = self.engine.get_pokemon(anchor) or BUILTIN_POKEMON.get(self.engine._clean_key(anchor), BUILTIN_POKEMON["incineroar"])
            anchor_name = dex_entry.get("name", anchor.capitalize())
            
            anchor_mon = {
                "name": anchor_name,
                "item": "Sitrus Berry",
                "ability": dex_entry.get("abilities", {}).get("0", "Standard"),
                "moves": ["Protect", "Fake Out", "U-turn", "Shadow Ball"],
                "nature": "Adamant",
                "evs": {"hp": 252, "atk": 252, "def": 4, "spa": 0, "spd": 0, "spe": 0}
            }

            mutator = EvolutionaryTeamMutator(self.format_id)
            best_team, win_score, _ = mutator.run_evolutionary_search(anchor_mon, num_generations=15, population_size=8)
            paste_str = export_showdown_paste(best_team)

            return (
                f"### 🧬 Anti-Meta Evolutionary Build for **{anchor_name}**\n"
                f"**Simulated Win Rate**: `{win_score}%` across top tournament archetypes.\n\n"
                f"```text\n{paste_str}\n```\n"
                f"*(Click 'Copy Paste' or load into Team Builder to customize spreads)*"
            )

        # 3. Off-meta counters: "suggest off-meta counters under 5% usage"
        if "off-meta" in msg or "hidden gem" in msg or "counters" in msg:
            gems = self.simulator.find_offmeta_counters(current_team, max_usage_pct=5.0, limit=5)
            res = ["### 💎 Anti-Meta Hidden Gems (<5% Tournament Usage)\n"]
            for g in gems:
                res.append(f"**🛡️ {g['name']}** (Synergy Rating: {g['synergy_score']}/100)")
                res.append(f"- **Key Ability**: `{g['ability']}` | **Typing**: `{' / '.join(g['types'])}`")
                res.append(f"- **Answers**: `{', '.join(g['targets_answered']) if g['targets_answered'] else 'Top meta threats'}`")
                res.append(f"- **Why It Works**: {g['why']}")
                res.append(f"- **Suggested Tech**: `{', '.join(g['suggested_moves'])}`\n")
            return "\n".join(res)

        # 4. Creep speed above standard [Target]: "creep speed above standard [Target]"
        m_creep = re.search(r"creep\s*speed\s*(?:above)?\s*(?:standard)?\s*([a-zA-Z0-9_-]+)", msg)
        if m_creep:
            target = m_creep.group(1).strip()
            user_mon = current_team[0] if current_team else {"name": "Incineroar", "nature": "Careful", "evs": {}}
            opt = self.benchmarks.optimize_speed_creep(user_mon, target)
            return (
                f"### ⚡ Speed Creep Optimizer vs. Standard **{target.capitalize()}**\n"
                f"- **Target Standard Speed**: `{opt['target_speed']} Spe` (Level 50)\n"
                f"- **Creep Benchmark Target**: `{opt['desired_speed']} Spe` (+1 Spe)\n"
                f"- **Solution for {user_mon.get('name', 'Your Pokémon')}**: {opt['desc']}\n"
            )

        # 5. Optimize OHKO: "optimize OHKO on standard [Target]"
        m_ohko = re.search(r"optimize\s*ohko\s*(?:on)?\s*(?:standard)?\s*([a-zA-Z0-9_-]+)", msg)
        if m_ohko:
            target = m_ohko.group(1).strip()
            user_mon = current_team[0] if current_team else {"name": "Flutter Mane", "nature": "Timid", "evs": {}}
            move_candidate = user_mon.get("moves", ["Moonblast"])[0] if user_mon.get("moves") else "Moonblast"
            opt = self.benchmarks.optimize_ohko_punish(user_mon, target, move_candidate)
            return (
                f"### 💥 Guaranteed OHKO Benchmark vs. Standard **{target.capitalize()}**\n"
                f"- **Attacker**: `{user_mon.get('name')}` using `{move_candidate}`\n"
                f"- **Target**: Standard tournament bulk `{target.capitalize()}`\n"
                f"- **Result**: {opt['desc']}\n"
            )

        # 6. Rate my synergy: "rate my synergy"
        if "synergy" in msg or "report card" in msg or "rate team" in msg:
            rep = self.analytics.generate_report_card(current_team)
            return (
                f"### 📊 Team Report Card & Synergy Audit\n"
                f"- **Synergy Score**: `{rep['synergy_score']}/100`\n"
                f"- **Defensive Cores**: FWG (`{'Active' if rep['fwg_core'] else 'Missing'}`) | DFS (`{'Active' if rep['dfs_core'] else 'Missing'}`)\n"
                f"- **Offensive Pressure**: `{rep['offense_pressure']}/100` | **Bulk Rating**: `{rep['defense_bulk']}/100`\n"
                f"- **Damage Split**: `{rep['physical_ratio']}% Physical` / `{rep['special_ratio']}% Special`\n"
                f"- **Pilot Difficulty**: `{rep['pilot_difficulty_stars']} ★` ({rep['pilot_difficulty_label']})\n"
                f"- **Bo3 OTS Resiliency**: `{rep['ots_resiliency_score']}/100` | **CTS Surprise**: `{rep['cts_surprise_score']}/100`\n"
            )

        # 7. Check board control: "check board control"
        if "board control" in msg or "control" in msg or "disruption" in msg:
            rep = self.analytics.generate_report_card(current_team)
            tools = rep["tools_found"]
            res = [f"### ♟️ Board Control & Disruption Audit (`{rep['board_control_score']}/100`)\n"]
            for cat, items in tools.items():
                status = f"✅ ({len(items)})" if items else "⚠️ (0 - Missing)"
                res.append(f"**{cat}** {status}: {', '.join(items) if items else 'None detected'}")
            res.append(f"\n- **Protect Density**: `{rep['protect_count']}/6 Pokémon` have Protect-family moves.")
            if rep['protect_count'] < 3:
                res.append("> ⚠️ *Recommendation*: In VGC/Doubles, aim for at least 3-4 Protects to safely navigate positioning and stall opposing Tailwind/Trick Room turns.")
            return "\n".join(res)

        # 8. Check OTS Bo3 Resiliency: "check OTS Bo3 resiliency"
        if "ots" in msg or "resiliency" in msg or "bo3" in msg:
            rep = self.analytics.generate_report_card(current_team)
            return (
                f"### 📋 Open Team Sheet (OTS) & Best-of-3 Resiliency\n"
                f"- **OTS Bo3 Resiliency Rating**: `{rep['ots_resiliency_score']}/100`\n"
                f"- **CTS Surprise Rating**: `{rep['cts_surprise_score']}/100`\n\n"
                f"**Why this matters in tournament play**:\n"
                f"- In Open Team Sheet Best-of-3, opponents know all 24 moves, 6 items, and 6 abilities prior to Game 1.\n"
                f"- Teams with high OTS Resiliency rely on robust defensive pivot cores, positioning, and versatile answers rather than one-time gimmick surprise."
            )

        # Default help
        return (
            "### 🤖 VGC & Showdown Studio Co-Pilot Commands\n"
            "Try asking or clicking one of the following prompt commands:\n"
            "- `rate my synergy` (computes complete Team Report Card)\n"
            "- `check board control` (audits Fake Out, Redirection, Speed Control & Protect)\n"
            "- `check OTS Bo3 resiliency` (evaluates Open Team Sheet stability)\n"
            "- `discover weird combos for [Pokemon]` (scans 2-mon rogue synergies)\n"
            "- `build an anti-meta team around [Pokemon]` (genetic evolutionary search)\n"
            "- `suggest off-meta counters under 5% usage` (finds high-impact rogue gems)\n"
            "- `creep speed above standard [Target]` (calculates exact +1 Spe EV/SP)\n"
            "- `optimize OHKO on standard [Target]` (finds minimum Atk/SpA EVs/SP)\n"
        )
