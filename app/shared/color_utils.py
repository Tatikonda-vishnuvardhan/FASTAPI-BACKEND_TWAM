"""
color_utils.py
TWAM color search — pv."Color" stores hex values (e.g. #1a1a1a).

Flow:
1. User searches "black" -> resolve to anchor hex #000000
2. Query ProductColor table: find all rows whose HexValue is within 
   perceptual distance of #000000
3. Return those ColorName values (which ARE the hex values stored in pv.Color)
4. SQL: pv."Color" = '#1a1a1a' OR pv."Color" = '#1b2a4a'
"""
import math
from typing import Optional

# ── User-typed color name -> anchor hex ────────────────────────────────────────
# Used to resolve what the user typed into a hex for proximity search
COLOR_NAME_TO_HEX: dict[str, str] = {
    "black": "#000000", "dark black": "#000000", "jet black": "#000000",
    "onyx": "#000000", "ebony": "#000000", "raven": "#000000",
    "charcoal": "#333333", "graphite": "#444444",
    "grey": "#808080", "gray": "#808080", "silver": "#C0C0C0",
    "ash": "#B2BEB5", "slate": "#708090", "smoke": "#738276",
    "mist": "#C4C3D0", "cloud": "#F5F5F5", "fog": "#D3D3D3",
    "white": "#FFFFFF", "ivory": "#FFFFF0", "cream": "#FFFDD0",
    "snow": "#FFFFFF", "pearl": "#F0EAD6", "off-white": "#FAF9F6",
    "off white": "#FAF9F6",
    "nude": "#E3BC9A", "skin": "#FFCBA4", "beige": "#F5DEB3",
    "tan": "#D2B48C", "sand": "#C2B280", "peach": "#FFCBA4",
    "champagne": "#F7E7CE", "wheat": "#F5DEB3",
    "desert_rose": "#C48B9F", "desert rose": "#C48B9F",
    "dusty rose": "#C48B9F", "dusty pink": "#C48B9F",
    "mauve": "#E0B0FF", "rose gold": "#B76E79", "blush": "#DE5D83",
    "pink": "#FFC0CB", "light pink": "#FFB6C1", "hot pink": "#FF69B4",
    "baby pink": "#FFB6C1", "flamingo": "#FC8EAC",
    "magenta": "#FF00FF", "fuchsia": "#FF00FF",
    "rose": "#FF007F", "deep pink": "#FF1493",
    "red": "#FF0000", "dark red": "#8B0000", "crimson": "#DC143C",
    "scarlet": "#FF2400", "coral": "#FF7F50", "brick": "#CB4154",
    "ruby": "#9B111E", "cherry": "#DE3163",
    "wine": "#722F37", "maroon": "#800000", "burgundy": "#800020",
    "bordeaux": "#5C0033", "dark wine": "#600020", "claret": "#722F37",
    "oxblood": "#800020", "sangria": "#7B1C2E",
    "orange": "#FF7F00", "rust": "#B7410E", "tangerine": "#F28500",
    "amber": "#FFBF00", "burnt orange": "#CC5500", "terracotta": "#E2725B",
    "gold": "#FFD700", "yellow": "#FFFF00", "mustard": "#FFDB58",
    "navy": "#000080", "dark blue": "#00008B", "navy blue": "#000080",
    "midnight blue": "#191970", "indigo": "#4B0082",
    "cobalt": "#0047AB", "sapphire": "#0F52BA", "denim": "#1560BD",
    "teal": "#008080", "dark teal": "#006666", "sea green": "#2E8B57",
    "jade": "#00A86B", "turquoise": "#40E0D0", "aqua": "#00FFFF",
    "green": "#008000", "olive": "#808000", "forest": "#228B22",
    "purple": "#800080", "violet": "#8B00FF", "plum": "#DDA0DD",
    "lavender": "#E6E6FA", "lilac": "#C8A2C8", "grape": "#6F2DA8",
    "orchid": "#DA70D6", "amethyst": "#9966CC",
    "brown": "#964B00", "chocolate": "#7B3F00", "mocha": "#967259",
    "caramel": "#C68642",
}

THRESHOLD = 160  # Redmean distance — works well for grouping similar shades


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _redmean_distance(hex_a: str, hex_b: str) -> float:
    """Perceptually-weighted RGB distance."""
    r1, g1, b1 = _hex_to_rgb(hex_a)
    r2, g2, b2 = _hex_to_rgb(hex_b)
    rm = (r1 + r2) / 2
    dr, dg, db = r1 - r2, g1 - g2, b1 - b2
    return math.sqrt((2 + rm/256)*dr*dr + 4*dg*dg + (2 + (255-rm)/256)*db*db)


def resolve_hex(color_name: str) -> Optional[str]:
    """
    Resolve a user-typed color name OR hex string to a hex value.
    e.g. "black" -> "#000000", "#722f37" -> "#722f37"
    """
    c = color_name.strip().lower()
    # Already a hex value
    if c.startswith("#") and len(c) in (4, 7):
        return c.upper() if len(c) == 4 else c
    # Name lookup
    return COLOR_NAME_TO_HEX.get(c)


def is_color_query(query: str) -> bool:
    """True if query is a recognised color name (>=3 chars)."""
    if len(query.strip()) < 3:
        return False
    return resolve_hex(query) is not None


# Per-color thresholds — calibrated against actual DB hex values
# Wider = more shades included. Results always sorted closest-first.
COLOR_THRESHOLDS = {
    # Dark tones — mathematically derived from actual DB hex distances
    'black':       174,  'charcoal':    174,  'dark black':  174,
    'navy':        158,  'dark blue':   158,  'midnight':    158,
    # Neutrals
    'grey':        104,  'gray':        104,  'silver':      104,
    'white':       127,  'ivory':       127,  'cream':       127,
    'off-white':   127,  'off white':   127,  'snow':        127,
    # Wine/burgundy family
    'wine':        132,  'burgundy':    132,  'bordeaux':    132,  'claret': 132,
    # Maroon/red-dark
    'maroon':      160,  'oxblood':     132,  'dark red':    160,
    # Reds
    'red':         162,  'crimson':     162,  'scarlet':     162,  'ruby': 162,
    # Pinks
    'pink':        114,  'light pink':  114,  'hot pink':    114,  'baby pink': 114,
    'rose':        129,  'blush':       129,  'flamingo':    129,
    # Nudes/skin tones
    'nude':        123,  'skin':        123,  'peach':       123,
    'beige':       123,  'tan':         123,  'sand':        123,
    'desert_rose': 123,  'desert rose': 123,  'dusty rose':  123,  'dusty pink': 123,
    # Teal/green
    'teal':        138,  'dark teal':   138,  'sea green':   138,  'jade': 138,
    'turquoise':   138,  'aqua':        138,
    # Orange
    'orange':      138,  'rust':        138,  'burnt orange': 138,  'terracotta': 138,
    # Purple
    'purple':      133,  'violet':      133,  'lavender':    133,
    'lilac':       133,  'plum':        133,  'grape':       133,
}
DEFAULT_COLOR_THRESHOLD = 200


def get_matching_db_colors(db, query: str) -> list[str]:
    """
    Query ProductColor table to find all DB pv.Color hex values
    that are perceptually close to the user's query color.
    Returns list of hex strings sorted by distance (closest first).
    """
    from sqlalchemy import text

    anchor_hex = resolve_hex(query)
    if not anchor_hex:
        return []  # not a color query

    threshold = COLOR_THRESHOLDS.get(query.lower().strip(), DEFAULT_COLOR_THRESHOLD)

    try:
        rows = db.execute(text(
            'SELECT "ColorName", "HexValue" FROM twam."ProductColor"' 
            ' WHERE "HexValue" IS NOT NULL AND "HexValue" != \'#808080\'' 
        )).fetchall()
    except Exception:
        return []

    # Exclusion zones: colors that look close mathematically but are different families
    # Key: anchor_hex, Value: set of hex values to exclude from results
    EXCLUSIONS: dict[str, set] = {
        '#722F37': {'#1b2a4a', '#1a1a1a'},  # wine: exclude navy/black
        '#800000': {'#1b2a4a'},              # maroon: exclude navy
        '#000000': {},                        # black: include dark shades
        '#000080': {'#1a1a1a'},              # navy: exclude black
    }
    # Normalize anchor for lookup
    anchor_upper = anchor_hex.upper()
    exclude_set = EXCLUSIONS.get(anchor_hex, EXCLUSIONS.get(anchor_upper, set()))

    matched = []
    for color_name, hex_val in rows:   # color_name = ColorName (may be word or hex), hex_val = HexValue
        try:
            if hex_val.lower() in {e.lower() for e in exclude_set}:  # exclude by HexValue
                continue
            d = _redmean_distance(anchor_hex, hex_val)
            if d <= threshold:
                matched.append((d, color_name))  # return ColorName so ILIKE filter matches pv."Color"
        except Exception:
            pass

    # Sort by distance — most similar first
    matched.sort(key=lambda x: x[0])
    return [color_name for _, color_name in matched] if matched else []


def get_color_hex(color_name: str) -> Optional[str]:
    """Get display hex for UI swatch."""
    return resolve_hex(color_name)