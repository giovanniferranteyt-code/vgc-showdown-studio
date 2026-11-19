"""
VGC & Showdown Studio - Asynchronous Sprite Loader & Disk Cache
Fetches PNG sprites from Showdown dex sprites with PokeAPI fallback.
"""

from __future__ import annotations
import os
import sys
import re
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image, ImageDraw
import customtkinter as ctk

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def get_sprite_cache_dir() -> Path:
    d = get_base_dir() / "data" / "sprites"
    d.mkdir(parents=True, exist_ok=True)
    return d

class SpriteLoader:
    _instance: Optional[SpriteLoader] = None

    def __init__(self):
        self.cache_dir = get_sprite_cache_dir()
        self.executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="SpriteWorker")
        self.memory_cache: Dict[str, Image.Image] = {}
        self.ctk_cache: Dict[str, ctk.CTkImage] = {}
        self.lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> SpriteLoader:
        if cls._instance is None:
            cls._instance = SpriteLoader()
        return cls._instance

    def _clean_name(self, name: str) -> str:
        clean = re.sub(r"[^a-z0-9]", "", name.lower())
        # Showdown sprite filenames
        replacements = {
            "urshifurapidstrike": "urshifu-rapidstrike",
            "calyrexshadow": "calyrex-shadow",
            "calyrexice": "calyrex-ice",
            "landorustherian": "landorus-therian",
            "thundurustherian": "thundurus-therian",
            "tornadustherian": "tornadus-therian",
            "ogerponwellspring": "ogerpon-wellspring",
            "ogerponhearthflame": "ogerpon-hearthflame",
            "ogerponcornerstone": "ogerpon-cornerstone",
            "ursalunabloodmoon": "ursaluna-bloodmoon",
            "charizardmegay": "charizard-megay",
            "charizardmegax": "charizard-megax",
            "kangaskhanmega": "kangaskhan-mega",
            "salamencemega": "salamence-mega",
            "gengarmega": "gengar-mega",
            "terapagosterastal": "terapagos-terastal",
            "terapagosstellar": "terapagos-stellar",
            "indeedee": "indeedee-f",
        }
        return replacements.get(clean, clean)

    def _create_placeholder(self, size: Tuple[int, int] = (64, 64)) -> Image.Image:
        """Create a Pokéball-style circular placeholder icon."""
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        w, h = size
        # Top half red, bottom half white
        draw.pieslice([4, 4, w - 4, h - 4], 180, 360, fill=(220, 53, 69, 230), outline=(30, 30, 30, 255), width=2)
        draw.pieslice([4, 4, w - 4, h - 4], 0, 180, fill=(245, 245, 245, 230), outline=(30, 30, 30, 255), width=2)
        # Center dividing band
        draw.line([(4, h // 2), (w - 4, h // 2)], fill=(30, 30, 30, 255), width=3)
        # Center button
        btn_r = max(4, w // 7)
        draw.ellipse([w // 2 - btn_r, h // 2 - btn_r, w // 2 + btn_r, h // 2 + btn_r], fill=(255, 255, 255, 255), outline=(30, 30, 30, 255), width=2)
        return img

    def get_pil_image_sync(self, pokemon_name: str, size: Tuple[int, int] = (64, 64)) -> Image.Image:
        """Synchronous loader: checks memory, disk, then falls back to placeholder."""
        if not pokemon_name:
            return self._create_placeholder(size)

        sprite_id = self._clean_name(pokemon_name)
        mem_key = f"{sprite_id}_{size[0]}x{size[1]}"

        with self.lock:
            if mem_key in self.memory_cache:
                return self.memory_cache[mem_key]

        disk_path = self.cache_dir / f"{sprite_id}.png"
        if disk_path.exists():
            try:
                img = Image.open(disk_path).convert("RGBA")
                resized = img.resize(size, Image.Resampling.LANCZOS)
                with self.lock:
                    self.memory_cache[mem_key] = resized
                return resized
            except Exception:
                pass

        # Trigger background download if not present
        self.executor.submit(self._download_sprite, pokemon_name)
        return self._create_placeholder(size)

    def _download_sprite(self, pokemon_name: str) -> Optional[Path]:
        sprite_id = self._clean_name(pokemon_name)
        disk_path = self.cache_dir / f"{sprite_id}.png"
        if disk_path.exists() and disk_path.stat().st_size > 50:
            return disk_path

        urls = [
            f"https://play.pokemonshowdown.com/sprites/dex/{sprite_id}.png",
            f"https://play.pokemonshowdown.com/sprites/gen5/{sprite_id}.png",
            f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/{sprite_id}.png",
            f"https://play.pokemonshowdown.com/sprites/dex/{re.sub(r'[^a-z0-9]', '', pokemon_name.lower())}.png",
        ]

        for url in urls:
            try:
                r = requests.get(url, timeout=4, headers={"User-Agent": "VGCShowdownStudio/1.0.0"})
                if r.status_code == 200 and len(r.content) > 100:
                    with open(disk_path, "wb") as f:
                        f.write(r.content)
                    return disk_path
            except Exception:
                continue

        return None

    def load_ctk_image_async(
        self,
        pokemon_name: str,
        size: Tuple[int, int] = (64, 64),
        on_loaded: Optional[Callable[[ctk.CTkImage], None]] = None
    ) -> ctk.CTkImage:
        """
        Asynchronously loads a sprite.
        Returns immediate cached/placeholder CTkImage, then calls on_loaded(ctk_image) upon fetch.
        """
        sprite_id = self._clean_name(pokemon_name) if pokemon_name else "empty"
        ctk_key = f"{sprite_id}_{size[0]}x{size[1]}"

        with self.lock:
            if ctk_key in self.ctk_cache:
                return self.ctk_cache[ctk_key]

        # Initial fallback image
        pil_img = self.get_pil_image_sync(pokemon_name, size)
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
        with self.lock:
            self.ctk_cache[ctk_key] = ctk_img

        def _bg_task():
            path = self._download_sprite(pokemon_name)
            if path and path.exists():
                try:
                    loaded_pil = Image.open(path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                    new_ctk = ctk.CTkImage(light_image=loaded_pil, dark_image=loaded_pil, size=size)
                    with self.lock:
                        self.memory_cache[f"{sprite_id}_{size[0]}x{size[1]}"] = loaded_pil
                        self.ctk_cache[ctk_key] = new_ctk
                    if on_loaded:
                        on_loaded(new_ctk)
                except Exception:
                    pass

        self.executor.submit(_bg_task)
        return ctk_img
