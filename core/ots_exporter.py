"""
VGC & Showdown Studio - Tournament Open Team Sheet (OTS) PNG Exporter
Renders standard 1920x1080 official OTS sheets omitting private EVs/SPs/IVs/Natures.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from core.mechanics import ShowdownEngine, BUILTIN_POKEMON
from core.sprite_loader import SpriteLoader

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        parent = Path(sys.executable).parent
        if (parent / "data").exists():
            return parent
        if (parent / "_internal" / "data").exists():
            return parent / "_internal"
        return parent
    return Path(__file__).resolve().parent.parent

def get_exports_dir() -> Path:
    d = get_base_dir() / "data" / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d

TYPE_COLORS = {
    "Normal": (168, 168, 120),
    "Fire": (240, 128, 48),
    "Water": (104, 144, 240),
    "Grass": (120, 200, 80),
    "Electric": (248, 208, 48),
    "Ice": (152, 216, 216),
    "Fighting": (192, 48, 40),
    "Poison": (160, 64, 160),
    "Ground": (224, 192, 104),
    "Flying": (168, 144, 240),
    "Psychic": (248, 88, 136),
    "Bug": (168, 184, 32),
    "Rock": (184, 160, 56),
    "Ghost": (112, 88, 152),
    "Dragon": (112, 56, 248),
    "Steel": (184, 184, 208),
    "Dark": (112, 88, 72),
    "Fairy": (238, 153, 172),
    "Stellar": (80, 190, 240)
}

def export_ots_png(
    team: List[Dict[str, Any]],
    team_name: str = "Tournament Roster",
    trainer_name: str = "Player 1",
    format_label: str = "VGC 2024 / Champions",
    dest_path: Optional[Path] = None
) -> Path:
    """
    Renders 1920x1080 official Open Team Sheet (OTS) PNG.
    Strictly omits private EVs/SPs, IVs, and Natures per official tournament rules.
    """
    if dest_path is None:
        safe_name = "".join(c for c in team_name if c.isalnum() or c in (" ", "_", "-")).strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = get_exports_dir() / f"OTS_{safe_name or 'Team'}_{timestamp}.png"

    width, height = 1920, 1080
    im = Image.new("RGBA", (width, height), (18, 20, 26, 255))
    draw = ImageDraw.Draw(im)

    # Fonts (Load standard TTF or use default)
    try:
        title_font = ImageFont.truetype("arial.ttf", 36)
        header_font = ImageFont.truetype("arialbd.ttf", 22)
        card_name_font = ImageFont.truetype("arialbd.ttf", 24)
        body_font = ImageFont.truetype("arial.ttf", 18)
        bold_font = ImageFont.truetype("arialbd.ttf", 18)
        small_font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        title_font = ImageFont.load_default()
        header_font = title_font
        card_name_font = title_font
        body_font = title_font
        bold_font = title_font
        small_font = title_font

    # Background Header Gradient Bar
    draw.rectangle([0, 0, width, 110], fill=(28, 32, 45, 255))
    draw.line([(0, 110), (width, 110)], fill=(88, 101, 242, 255), width=4)

    # Header Titles
    draw.text((40, 18), "VGC & SHOWDOWN STUDIO", fill=(88, 101, 242, 255), font=header_font)
    draw.text((40, 48), "OFFICIAL TOURNAMENT OPEN TEAM SHEET (OTS)", fill=(255, 255, 255, 255), font=title_font)

    # Metadata block (Right side of header)
    meta_x = 1250
    draw.text((meta_x, 18), f"Trainer: {trainer_name}", fill=(240, 240, 240, 255), font=header_font)
    draw.text((meta_x, 46), f"Team: {team_name}", fill=(220, 220, 220, 255), font=body_font)
    draw.text((meta_x, 72), f"Format: {format_label}", fill=(180, 190, 210, 255), font=small_font)
    draw.text((1650, 72), f"Date: {datetime.now().strftime('%Y-%m-%d')}", fill=(150, 160, 175, 255), font=small_font)

    # 6 Pokémon Cards: 2 Rows x 3 Columns
    col_width = 590
    row_height = 430
    margin_x = 40
    margin_y = 140
    gap_x = 35
    gap_y = 35

    sprite_loader = SpriteLoader.get_instance()
    engine = ShowdownEngine.get_instance()

    for i in range(6):
        col = i % 3
        row = i // 3
        cx = margin_x + col * (col_width + gap_x)
        cy = margin_y + row * (row_height + gap_y)

        # Card Frame
        draw.rounded_rectangle([cx, cy, cx + col_width, cy + row_height], radius=12, fill=(28, 31, 40, 255), outline=(48, 54, 70, 255), width=2)

        if i < len(team):
            mon = team[i]
            species = mon.get("name", "Unknown")
            dex_entry = engine.get_pokemon(species) or BUILTIN_POKEMON.get(engine._clean_key(species), {})
            display_name = dex_entry.get("name", species)
            types = dex_entry.get("types", ["Normal"])

            # Left side: Sprite Container
            draw.rounded_rectangle([cx + 15, cy + 15, cx + 185, cy + 185], radius=10, fill=(38, 42, 54, 255), outline=(60, 66, 85, 255), width=1)
            
            # Draw Sprite
            pil_sprite = sprite_loader.get_pil_image_sync(species, size=(160, 160))
            im.paste(pil_sprite, (cx + 20, cy + 20), pil_sprite)

            # Species Name & Types
            draw.text((cx + 200, cy + 20), display_name, fill=(255, 255, 255, 255), font=card_name_font)

            # Type Badges
            badge_x = cx + 200
            for t in types:
                c_color = TYPE_COLORS.get(t, (120, 120, 120))
                draw.rounded_rectangle([badge_x, cy + 55, badge_x + 75, cy + 78], radius=6, fill=c_color)
                draw.text((badge_x + 8, cy + 58), t.upper(), fill=(255, 255, 255, 255), font=small_font)
                badge_x += 85

            # Held Item, Ability, Tera/Form
            item_val = mon.get("item", "None") or "None"
            ability_val = mon.get("ability", "Standard") or "Standard"
            tera_val = mon.get("tera_type") or ("Mega Evolution" if "mega" in species.lower() else "Standard")

            info_y = cy + 90
            draw.text((cx + 200, info_y), "Held Item:", fill=(160, 170, 190, 255), font=small_font)
            draw.text((cx + 280, info_y), item_val, fill=(245, 245, 245, 255), font=bold_font)

            draw.text((cx + 200, info_y + 30), "Ability:", fill=(160, 170, 190, 255), font=small_font)
            draw.text((cx + 280, info_y + 30), ability_val, fill=(245, 245, 245, 255), font=bold_font)

            draw.text((cx + 200, info_y + 60), "Tera/Form:", fill=(160, 170, 190, 255), font=small_font)
            draw.text((cx + 280, info_y + 60), tera_val, fill=(241, 196, 15, 255), font=bold_font)

            # 4 Moves Box
            moves_box_y = cy + 200
            draw.rounded_rectangle([cx + 15, moves_box_y, cx + col_width - 15, moves_box_y + 175], radius=8, fill=(22, 24, 32, 255), outline=(42, 46, 60, 255), width=1)
            draw.text((cx + 25, moves_box_y + 8), "REVEALED MOVESET (4 MOVES)", fill=(130, 140, 160, 255), font=small_font)

            moves = mon.get("moves", [])
            for m_idx in range(4):
                mx = cx + 25
                my = moves_box_y + 32 + m_idx * 33
                m_name = moves[m_idx] if m_idx < len(moves) and moves[m_idx] else "--"
                draw.text((mx, my), f"{m_idx + 1}.", fill=(88, 101, 242, 255), font=bold_font)
                draw.text((mx + 25, my), m_name, fill=(240, 240, 240, 255), font=bold_font)

            # Rules Notice
            draw.text((cx + 20, cy + row_height - 32), "[OTS] EVs / SPs / IVs / Natures withheld for Bo3 tournament play.", fill=(110, 120, 140, 255), font=small_font)
        else:
            # Empty slot card
            draw.text((cx + col_width // 2 - 50, cy + row_height // 2 - 10), "[ Empty Slot ]", fill=(90, 95, 110, 255), font=header_font)

    # Bottom Footer
    draw.line([(0, height - 35), (width, height - 35)], fill=(45, 50, 65, 255), width=1)
    draw.text((40, height - 25), "Generated by VGC & Showdown Studio v1.0.0 | Verified for Play! Pokémon VGC & Champions Regional Tournament Standards", fill=(120, 130, 150, 255), font=small_font)

    im.save(dest_path, "PNG")
    return dest_path
