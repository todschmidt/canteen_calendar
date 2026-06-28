"""Normalize menu price and ABV values for editor storage and TV display."""


def parse_price(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if s.startswith("$"):
        s = s[1:].strip()
    return s


def format_price(raw: str) -> str:
    s = parse_price(raw)
    if not s:
        return ""
    return f"${s}"


def parse_abv(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if s.endswith("%"):
        s = s[:-1].strip()
    return s


def format_abv(raw: str) -> str:
    s = parse_abv(raw)
    if not s:
        return ""
    try:
        return f"{float(s):.1f}%"
    except ValueError:
        return raw.strip()
