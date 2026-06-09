"""Shared path helpers for cdr_mtn_tv."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent


def root_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)


def load_config() -> dict:
    import json

    with open(root_path("config.json"), encoding="utf-8") as f:
        return json.load(f)
