"""
TWAM Lingerie Platform -- Full Seed Script v2  (fixed)
=======================================================
Run from your project root (same folder as database.py):

    cd D:\\project3\\twam_backend
    py seed_v2.py

What this script does:
    1. Deletes ALL old product data (ProductImage, ProductVariantDetail,
       ProductVariants, Products, ProductColor, brands)
    2. Resets sequences to 1
    3. Inserts 6 brands, 18 products, 67 variants, 717 stock rows,
       345 images, 27 colours
    4. Does NOT touch mdm.Size or mdm.CupSize (already in DB)

Fix vs original:
    - print(colour count) was at wrong indent level, breaking out of the
      `with engine.begin()` block before sequences were updated → conn closed.
      Moved back inside the with block (8-space indent).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import engine


# -----------------------------------------------------------------------------
# SIZE / CUP REFERENCE  (already seeded in mdm.Size & mdm.CupSize -- read-only)
# -----------------------------------------------------------------------------
# Alpha sizes (mdm.Size.SizeId):
#   1=XS  2=S  3=M  4=L  5=XL  6=2XL  7=3XL
# Numeric band sizes (mdm.Size.SizeId):
#   10=28  11=30  12=32  13=34  14=36  15=38  16=40  17=42  18=44
# Cup sizes (mdm.CupSize.CupSizeId):
#   1=A  2=B  3=C  4=D  5=DD  6=DDD  7=E  8=F  9=FF  10=G

COLOR_HEX = {
    # ── seed-defined colours ──────────────────────────────────────────────────
    "aqua":         "#00BCD4",
    "ash grey":     "#9E9E9E",
    "bark":         "#C8A882",
    "beige":        "#C8A882",
    "black":        "#1A1A1A",
    "blue":         "#1565C0",
    "chocolate":    "#7B3F00",
    "cinnamon":     "#D2691E",
    "cloud":        "#E8E0D8",
    "coffee":       "#6F4E37",
    "coffee cream": "#D4A574",
    "coral":        "#E53935",
    "coral red":    "#E53935",
    "dark skin":    "#A0522D",
    "deep blue":    "#1B2A4A",
    "desert rose":  "#E8A598",
    "earth red":    "#8B4513",
    "fudge":        "#7D5A4F",
    "grass":        "#558B2F",
    "grey":         "#9E9E9E",
    "gray":         "#9E9E9E",
    "lemon":        "#FFF176",
    "maroon":       "#800000",
    "midnight":     "#1A237E",
    "mist":         "#B0BEC5",
    "nude":         "#F5CBA7",
    "purple":       "#9C27B0",
    "red":          "#D32F2F",
    "skin":         "#F5CBA7",
    "teal":         "#00695C",
    "waffle":       "#C9B99A",
    "white":        "#F5F5F5",
    # ── additional standard colours ───────────────────────────────────────────
    "navy":         "#000080",
    "green":        "#2E7D32",
    "yellow":       "#F9A825",
    "orange":       "#E65100",
    "pink":         "#E91E8C",
    "rose":         "#FF007F",
    "silver":       "#C0C0C0",
    "brown":        "#6D4C41",
    "burgundy":     "#800020",
    "wine":         "#722F37",
    "peach":        "#FFCBA4",
    "lavender":     "#E6E6FA",
    "ivory":        "#FFFFF0",
    "cream":        "#FFFDD0",
    "gold":         "#FFD700",
    "mustard":      "#FFDB58",
    "cyan":         "#00BCD4",
    "magenta":      "#FF00FF",
    "mint":         "#98FF98",
    "lilac":        "#C8A2C8",
    "mauve":        "#E0B0FF",
    "olive":        "#808000",
    "sage":         "#BCB88A",
    "sand":         "#C2B280",
    "taupe":        "#483C32",
    "tan":          "#D2B48C",
    "rust":         "#B7410E",
    "indigo":       "#4B0082",
    "violet":       "#EE82EE",
    "charcoal":     "#36454F",
    "smoke":        "#738276",
    "pearl":        "#EAE0C8",
    "caramel":      "#C68642",
    "mocha":        "#967117",
    "copper":       "#B87333",
}

# HEX → NAME  (built automatically — first entry wins for duplicate hexes)
HEX_TO_NAME: dict = {}
for _name, _hex in COLOR_HEX.items():
    _key = _hex.upper()
    if _key not in HEX_TO_NAME:
        HEX_TO_NAME[_key] = _name.title()


def _hex_to_rgb(hex_str: str):
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def resolve_color(name: str = "", hex_val: str = "") -> tuple:
    """
    Resolve a (colorName, colorHex) pair — filling in whichever is missing.
    Returns: (colorName: str, colorHex: str)
    """
    import re
    HEX_RE = r"^#[0-9a-fA-F]{3,8}$"
    has_hex  = bool(hex_val and re.match(HEX_RE, hex_val.strip()))
    has_name = bool(name and name.strip())

    if has_hex and has_name:
        return name.strip(), hex_val.strip()

    if has_name and not has_hex:
        lower = name.strip().lower()
        resolved_hex = COLOR_HEX.get(lower)
        if not resolved_hex:
            for k, v in COLOR_HEX.items():
                if lower in k or k in lower:
                    resolved_hex = v
                    break
        return name.strip(), resolved_hex or "#9E6070"

    if has_hex and not has_name:
        upper = hex_val.strip().upper()
        if upper in HEX_TO_NAME:
            return HEX_TO_NAME[upper], hex_val.strip()
        rgb = _hex_to_rgb(hex_val.strip())
        if rgb:
            best_name, best_dist = "", float("inf")
            for k, v in COLOR_HEX.items():
                candidate = _hex_to_rgb(v)
                if not candidate:
                    continue
                dist = sum((a - b) ** 2 for a, b in zip(rgb, candidate)) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_name = k.title()
            return best_name, hex_val.strip()
        return "", hex_val.strip()

    return "", "#9E6070"


# -----------------------------------------------------------------------------
# BRAND DATA
# -----------------------------------------------------------------------------
BRANDS = [
    {"id": 1, "name": "TWAM",     "desc": "Our in-house brand, every body, every day",         "img": "/uploads/brand-twam.png"},
    {"id": 2, "name": "Soie",     "desc": "Premium comfort innerwear crafted in India",          "img": "/uploads/brand-soie.png"},
    {"id": 3, "name": "Amante",   "desc": "Luxury lingerie designed for the modern woman",       "img": "/uploads/brand-amante.png"},
    {"id": 4, "name": "Enamor",   "desc": "Fashion-forward lingerie since 1998",                 "img": "/uploads/brand-enamor.png"},
    {"id": 5, "name": "Triumph",  "desc": "World-class comfort and support for every woman",     "img": "/uploads/brand-triumph.png"},
    {"id": 6, "name": "Blossoms", "desc": "Everyday comfort blossoming from nature",             "img": "/uploads/brand-blossoms.png"},
]


# -----------------------------------------------------------------------------
# PRODUCT CATALOGUE
# -----------------------------------------------------------------------------
# Category IDs  (twam.Category -- already seeded, untouched)
#   1 = Bras            |  Sub-cats: 7=Seamless, 8=T-Shirt, 11=Minimizer,
#                       |            13=Non-padded, 16=Sports, 19=Cotton
#   2 = Panties         |  Sub-cats: 22=Hipster, 28=Cycling Shorts,
#                       |            29=High-Waist, 30=Bikini
#   3 = Essentials      |  NO sub-category (ccat = None)
#
# is_cup = False  ->  alpha sizing: sizes[] + stocks[]
# is_cup = True   ->  band x cup matrix: bands[] x cups[], stock_cup per combo
#
# IMPORTANT: v["name"] is stored in ProductVariants.Color (NOT hex).
#            The exact hex lives in twam.ProductColor via COLOR_HEX above.
# -----------------------------------------------------------------------------

PRODUCTS = [

    # ── BRAS ──────────────────────────────────────────────────────────────────

    {
        "id": 1, "code": "BNB-01",
        "name": "Everyday Non-Wired Bra",
        "desc": (
            "Experience all-day comfort with our Everyday Non-Wired Bra. "
            "Crafted from ultra-soft breathable fabric, this wire-free design gently supports "
            "without restriction. Features adjustable straps, a U-shaped back, and a hook closure "
            "for a customised fit. No underwire, no padding, simply pure relaxed comfort all day "
            "long. Ideal for those who love a natural silhouette."
        ),
        "cat": 1, "ccat": 13,
        "brand": 1,
        "tag": "non-wired, everyday, breathable, wire-free, best-seller",
        "mrp": 699, "price": 499, "disc": 29,
        "is_cup": False,
        "sizes":  [2, 3,  4,  5,  6,  7],
        "stocks": [5, 8, 12, 12,  8,  5],
        "variants": [
            {
                "name": "Beige", "hex": "#C8A882", "folder": "BNB-01", "best": True,
                "imgs": ["beig-1", "beig-2", "beig-3", "beig-4", "beig-5", "beig-6"],
            },
            {
                "name": "Black", "hex": "#1A1A1A", "folder": "BNB-01", "best": True,
                "imgs": ["black-1", "black-2", "black-3", "black-4", "black-5"],
            },
            {
                "name": "Coffee Cream", "hex": "#D4A574", "folder": "BNB-01", "best": False,
                "imgs": ["coffe -1", "coffe -7", "coffe cream-2", "coffe cream-4", "coffe cream-5"],
            },
        ],
    },

    {
        "id": 2, "code": "BNB-02",
        "name": "Comfort Non-Wired Bra",
        "desc": (
            "Designed for effortless comfort, our Comfort Non-Wired Bra offers a relaxed "
            "wire-free fit that moves with you all day. Made from soft stretch fabric with a "
            "smooth finish, it provides gentle lift and support without the restriction of "
            "underwire. A rich palette of beautiful colours makes this an everyday essential "
            "redefined."
        ),
        "cat": 1, "ccat": 13,
        "brand": 1,
        "tag": "non-wired, comfort, stretch, soft, best-seller",
        "mrp": 799, "price": 599, "disc": 25,
        "is_cup": False,
        "sizes":  [2, 3,  4,  5,  6,  7],
        "stocks": [5, 8, 12, 12,  8,  5],
        "variants": [
            {"name": "Beige",        "hex": "#C8A882", "folder": "BNB-02", "best": True,
             "imgs": ["beig-1", "beig-2", "beig-3", "beig-4", "beig-5", "beig-6"]},
            {"name": "Black",        "hex": "#1A1A1A", "folder": "BNB-02", "best": True,
             "imgs": ["black-1", "black-2", "black-3", "black-4", "black-5"]},
            {"name": "Cinnamon",     "hex": "#D2691E", "folder": "BNB-02", "best": False,
             "imgs": ["Cinamen-1", "cinamen-2", "cinamen-3", "cinamen-4", "cinamen-5"]},
            {"name": "Coffee",       "hex": "#6F4E37", "folder": "BNB-02", "best": False,
             "imgs": ["coffe -1", "coffe -7"]},
            {"name": "Coffee Cream", "hex": "#D4A574", "folder": "BNB-02", "best": False,
             "imgs": ["coffe cream-2", "coffe cream-4", "coffe cream-5"]},
            {"name": "Grey",         "hex": "#9E9E9E", "folder": "BNB-02", "best": False,
             "imgs": ["grey-1", "grey-2", "grey-3", "grey-4", "grey-5"]},
        ],
    },

    {
        "id": 3, "code": "BNB-07",
        "name": "Soft Non-Padded Bra",
        "desc": (
            "Simplicity meets support with our Soft Non-Padded Bra. Lightweight and breathable, "
            "this wire-free bra is perfect for those who prefer a natural shape without extra "
            "padding. Smooth non-padded cups offer gentle coverage, while adjustable straps allow "
            "a personalised fit. A minimalist wardrobe essential for everyday confidence."
        ),
        "cat": 1, "ccat": 13,
        "brand": 1,
        "tag": "non-padded, soft, lightweight, everyday, new-arrival",
        "mrp": 699, "price": 499, "disc": 29,
        "is_cup": False,
        "sizes":  [2, 3,  4,  5,  6,  7],
        "stocks": [5, 8, 12, 12,  8,  5],
        "variants": [
            {"name": "Black",     "hex": "#1A1A1A", "folder": "BNB-07", "best": True,
             "imgs": ["black-1", "black-2", "black-3", "black-4", "black-5", "black-6"]},
            {"name": "Chocolate", "hex": "#7B3F00", "folder": "BNB-07", "best": True,
             "imgs": ["Choco-1", "choco-2", "choco-3", "choco-4", "choco-5", "choco-6"]},
            {"name": "Lemon",     "hex": "#FFF176", "folder": "BNB-07", "best": False,
             "imgs": ["lemon-1", "lemon-2", "lemon-3", "lemon-4", "lemon-5"]},
        ],
    },

    {
        "id": 4, "code": "CB-129",
        "name": "Full Coverage Seamless Bra",
        "desc": (
            "Discover invisible comfort with our Full Coverage Seamless Bra by Soie. Engineered "
            "with advanced seamless microfibre technology, this bra leaves zero trace under any "
            "outfit. Full coverage moulded cups provide superior modesty while the second-skin "
            "fabric moulds perfectly to your shape. Available in an everyday palette across a wide "
            "band and cup range."
        ),
        "cat": 1, "ccat": 7,
        "brand": 2,
        "tag": "seamless, full-coverage, microfibre, invisible, best-seller",
        "mrp": 1290, "price": 999, "disc": 23,
        "is_cup": True,
        "bands": [12, 13, 14, 15, 16],
        "cups":  [1, 2, 3, 4, 5],
        "stock_cup": 6,
        "variants": [
            {"name": "Bark",        "hex": "#C8A882", "folder": "CB-129", "best": True,
             "imgs": ["bark -1", "bark -2", "bark -3", "bark -4", "bark -5", "bark -6"]},
            {"name": "Black",       "hex": "#1A1A1A", "folder": "CB-129", "best": True,
             "imgs": ["black -1", "black -2", "black -3", "black -4", "black -5", "black -6", "black -7"]},
            {"name": "Cloud",       "hex": "#E8E0D8", "folder": "CB-129", "best": True,
             "imgs": ["cloud -1", "cloud -2", "cloud -3", "cloud -4", "cloud -5", "cloud -6"]},
            {"name": "Mist",        "hex": "#B0BEC5", "folder": "CB-129", "best": False,
             "imgs": ["mist -1", "mist -2", "mist -3", "mist -4", "mist -5"]},
            {"name": "Desert Rose", "hex": "#E8A598", "folder": "CB-129", "best": False,
             "imgs": ["rose -1", "rose -2", "rose -3", "rose -4", "rose -5", "rose -6"]},
        ],
    },

    {
        "id": 5, "code": "CB-132",
        "name": "Cotton Comfort Bra",
        "desc": (
            "Stay fresh and comfortable all day with our Cotton Comfort Bra by Blossoms. Made "
            "from premium breathable cotton, this bra is gentle on skin and naturally "
            "moisture-wicking. Structured cups offer a great shape with full coverage, a timeless "
            "essential that keeps you cool and confident through every season."
        ),
        "cat": 1, "ccat": 19,
        "brand": 6,
        "tag": "cotton, comfort, breathable, moisture-wicking, new-arrival",
        "mrp": 999, "price": 749, "disc": 25,
        "is_cup": True,
        "bands": [12, 13, 14, 15, 16],
        "cups":  [2, 3, 4],
        "stock_cup": 5,
        "variants": [
            {"name": "Bark", "hex": "#C8A882", "folder": "CB-132", "best": True,
             "imgs": ["Bark -2", "bark -3", "bark -4", "bark -5", "bark -6", "bark-1"]},
            {"name": "Mist", "hex": "#B0BEC5", "folder": "CB-132", "best": True,
             "imgs": ["mist -1", "mist -2", "mist -3", "mist -4", "mist -5", "mist -6"]},
            {"name": "Red",  "hex": "#D32F2F", "folder": "CB-132", "best": False,
             "imgs": ["red - 1", "red - 3", "red-2", "red-4", "red-5", "red-6"]},
        ],
    },

    {
        "id": 6, "code": "CB-328",
        "name": "Full Support Minimizer Bra",
        "desc": (
            "Redefine your silhouette with our Full Support Minimizer Bra by Triumph. Expertly "
            "designed to redistribute bust fullness for a one-cup-smaller appearance, it delivers "
            "exceptional support without sacrificing comfort. Wide-set straps, reinforced side "
            "panels, and full coverage cups work in perfect harmony, ideal for fuller figures "
            "seeking all-day ease."
        ),
        "cat": 1, "ccat": 11,
        "brand": 5,
        "tag": "minimizer, full-support, fuller-figure, coverage, best-seller",
        "mrp": 1799, "price": 1299, "disc": 28,
        "is_cup": True,
        "bands": [13, 14, 15, 16, 17],
        "cups":  [3, 4, 5],
        "stock_cup": 5,
        "variants": [
            {"name": "Black",     "hex": "#1A1A1A", "folder": "CB-328", "best": True,
             "imgs": ["balck -1", "black -2", "black -3", "black -4", "black -5", "black -6"]},
            {"name": "Blue",      "hex": "#1565C0", "folder": "CB-328", "best": True,
             "imgs": ["Blue -1", "Blue -2", "Blue -3", "Blue -4", "Blue -5", "Blue -6"]},
            {"name": "Coral Red", "hex": "#E53935", "folder": "CB-328", "best": False,
             "imgs": ["c red - 1", "C red -2", "c red -3", "c red -4", "C red -5"]},
            {"name": "Nude",      "hex": "#F5CBA7", "folder": "CB-328", "best": False,
             "imgs": ["Nude -1", "Nude -2", "Nude -3", "Nude -4", "Nude -5"]},
            {"name": "Waffle",    "hex": "#C9B99A", "folder": "CB-328", "best": False,
             "imgs": ["waffle -1", "waffle -2", "waffle -3", "waffle -4", "waffle -5", "waffle -6"]},
            {"name": "White",     "hex": "#F5F5F5", "folder": "CB-328", "best": False,
             "imgs": ["white -1", "white -2", "White -3", "White -5", "White -6", "White -7", "White -8"]},
        ],
    },

    {
        "id": 7, "code": "CB-334",
        "name": "Front-Open Zip Bra",
        "desc": (
            "Discover ultimate ease with our Front-Open Zip Bra by Triumph. A smooth front zipper "
            "closure makes wearing effortless, ideal for those seeking extra convenience. Moulded "
            "cups provide a flattering supportive shape, while the wide back band and adjustable "
            "straps ensure a secure comfortable fit from morning to night. A game-changer in "
            "everyday lingerie."
        ),
        "cat": 1, "ccat": 8,
        "brand": 5,
        "tag": "front-zip, easy-wear, moulded, support, new-arrival",
        "mrp": 1599, "price": 1199, "disc": 25,
        "is_cup": True,
        "bands": [12, 13, 14, 15, 16],
        "cups":  [2, 3, 4, 5],
        "stock_cup": 5,
        "variants": [
            {"name": "Aqua",  "hex": "#00BCD4", "folder": "CB-334", "best": True,
             "imgs": ["Aqua -1", "aqua-2", "aqua-3", "aqua-4", "aqua-5", "aqua-6"]},
            {"name": "Black", "hex": "#1A1A1A", "folder": "CB-334", "best": True,
             "imgs": ["black -1", "black-2", "black-3", "black-4", "black-5", "black-6"]},
            {"name": "Fudge", "hex": "#7D5A4F", "folder": "CB-334", "best": False,
             "imgs": ["fudge-1", "fudge-2", "fudge-3", "fudge -4", "fudge -6", "fudge-5"]},
            {"name": "Nude",  "hex": "#F5CBA7", "folder": "CB-334", "best": False,
             "imgs": ["nude -1", "nude-2", "nude -3", "nude -4", "nude -5"]},
        ],
    },

    {
        "id": 8, "code": "CB-336",
        "name": "Full Coverage Everyday Bra",
        "desc": (
            "Our Full Coverage Everyday Bra by Enamor delivers reliable support and full modesty "
            "all day long. Crafted from soft breathable fabric with wide straps and a full coverage "
            "cup design, it minimises bounce and maximises comfort. The sturdy back closure and "
            "adjustable straps allow a perfect personalised fit for every body."
        ),
        "cat": 1, "ccat": 19,
        "brand": 4,
        "tag": "full-coverage, everyday, support, breathable, cotton, best-seller",
        "mrp": 1199, "price": 899, "disc": 25,
        "is_cup": True,
        "bands": [12, 13, 14, 15, 16],
        "cups":  [2, 3, 4],
        "stock_cup": 6,
        "variants": [
            {"name": "Black",     "hex": "#1A1A1A", "folder": "CB-336", "best": True,
             "imgs": ["Black -1", "Black-2", "black-3", "black-4", "black-5", "black -6"]},
            {"name": "Dark Skin", "hex": "#A0522D", "folder": "CB-336", "best": True,
             "imgs": ["DArk skin -1", "Dark skin -2", "Dark skin -3", "Dark skin -4", "Dark skin -5", "Dark skin -6"]},
            {"name": "Earth Red", "hex": "#8B4513", "folder": "CB-336", "best": False,
             "imgs": ["earthred -1", "earthred -2", "earthred-3", "Earthred-4", "Earthred-5", "Earthred-6"]},
            {"name": "Midnight",  "hex": "#1A237E", "folder": "CB-336", "best": False,
             "imgs": ["Midnight -1", "Midnight -2", "Midnight -3", "Midnight -4", "Midnight -5"]},
            {"name": "White",     "hex": "#F5F5F5", "folder": "CB-336", "best": False,
             "imgs": ["White -1", "white -2", "White -3", "White -4", "white-5", "white-6"]},
        ],
    },

    {
        "id": 9, "code": "CB-910",
        "name": "Medium Support Sports Bra",
        "desc": (
            "Stay active and comfortable with our Medium Support Sports Bra by Amante. Designed "
            "for yoga, pilates, and moderate-intensity workouts, it features moisture-wicking "
            "fabric, a wide underband for stability, and a cropped silhouette for a modern "
            "athletic look. Lightweight, breathable, and built to move with you every step of "
            "the way."
        ),
        "cat": 1, "ccat": 16,
        "brand": 3,
        "tag": "sports, medium-support, yoga, pilates, moisture-wicking, best-seller",
        "mrp": 899, "price": 649, "disc": 28,
        "is_cup": False,
        "sizes":  [1, 2,  3,  4,  5,  6],
        "stocks": [4, 6, 10, 10,  6,  4],
        "variants": [
            {"name": "Black",  "hex": "#1A1A1A", "folder": "CB-910", "best": True,
             "imgs": ["Black -1", "Black -2", "Black -3", "Black -4", "Black -5"]},
            {"name": "Grey",   "hex": "#9E9E9E", "folder": "CB-910", "best": True,
             "imgs": ["Grey -1", "grey -2", "grey -5", "grey-3", "grey-4"]},
            {"name": "Maroon", "hex": "#800000", "folder": "CB-910", "best": False,
             "imgs": ["Maroon -1", "Maroon -2", "Maroon -3", "Maroon -4", "Maroon -5"]},
            {"name": "Nude",   "hex": "#F5CBA7", "folder": "CB-910", "best": False,
             "imgs": ["Nude -1", "nude -2", "Nude -3", "Nude -4", "Nude -5"]},
            {"name": "White",  "hex": "#F5F5F5", "folder": "CB-910", "best": False,
             "imgs": ["White -1", "White -2", "White -3", "white -4", "White -5"]},
        ],
    },

    {
        "id": 10, "code": "CB-911",
        "name": "High Support Sports Bra",
        "desc": (
            "Push your limits with our High Support Sports Bra by TWAM. Built for high-intensity "
            "workouts including running, HIIT, and aerobics, this performance bra features maximum "
            "encapsulation support, wide padded straps, and a double-layer construction for minimal "
            "bounce. Moisture-wicking fabric and a ventilated racerback keep you cool through "
            "every rep."
        ),
        "cat": 1, "ccat": 16,
        "brand": 1,
        "tag": "sports, high-support, running, HIIT, performance, new-arrival",
        "mrp": 999, "price": 699, "disc": 30,
        "is_cup": False,
        "sizes":  [1,  2,  3,  4,  5],
        "stocks": [4,  6, 10,  6,  4],
        "variants": [
            {"name": "Black",     "hex": "#1A1A1A", "folder": "CB-911", "best": True,
             "imgs": ["Black -1", "Black -2", "black -3", "Black -4", "Black -5"]},
            {"name": "Deep Blue", "hex": "#1B2A4A", "folder": "CB-911", "best": True,
             "imgs": ["Deep blue-1", "Deep blue-2", "Deep blue-3", "Deep blue-4", "Deep blue-5"]},
            {"name": "Maroon",    "hex": "#800000", "folder": "CB-911", "best": False,
             "imgs": ["Maroon -1", "Maroon -2", "Maroon -3", "Maroon -4", "Maroon -5"]},
        ],
    },

    {
        "id": 11, "code": "FB-709",
        "name": "Full Cup Minimizer Bra",
        "desc": (
            "Experience exceptional support with our Full Cup Minimizer Bra by Amante. Expertly "
            "designed with full cup construction and premium lace overlay, this bra provides a "
            "supportive fit that gently minimises the bust for a balanced silhouette. Reinforced "
            "underwire, cushioned straps, and a wide back band ensure all-day comfort, designed "
            "for the fuller figure."
        ),
        "cat": 1, "ccat": 11,
        "brand": 3,
        "tag": "full-cup, minimizer, lace, underwire, fuller-figure, new-arrival",
        "mrp": 1799, "price": 1399, "disc": 22,
        "is_cup": True,
        "bands": [13, 14, 15, 16, 17],
        "cups":  [4, 5, 7, 8],
        "stock_cup": 4,
        "variants": [
            {"name": "Ash Grey", "hex": "#9E9E9E", "folder": "FB-709", "best": True,
             "imgs": ["Ash Grey -1", "Ash grey -2", "Ash Grey -3", "Ash Grey -4", "Ash Grey -5"]},
            {"name": "Grass",    "hex": "#558B2F", "folder": "FB-709", "best": True,
             "imgs": ["Grass -1", "Grass -2", "Grass -3", "Grass -4", "Grass -5"]},
        ],
    },

    {
        "id": 12, "code": "SCBRA-01",
        "name": "Seamless Crop Bra",
        "desc": (
            "Experience second-skin comfort with our Seamless Crop Bra by Soie. Crafted from "
            "ultra-soft smooth fabric with zero seams for invisible wear under any outfit. The "
            "wide elastic underband provides gentle support while the cropped design offers a "
            "flattering modern silhouette. Ideal for layering, lounging, yoga, or everyday wear."
        ),
        "cat": 1, "ccat": 7,
        "brand": 2,
        "tag": "seamless, crop-bra, comfort, invisible, new-arrival",
        "mrp": 899, "price": 649, "disc": 28,
        "is_cup": False,
        "sizes":  [1,  2,  3,  4,  5,  6],
        "stocks": [4,  6, 10, 10,  6,  4],
        "variants": [
            {"name": "Black", "hex": "#1A1A1A", "folder": "replacing", "best": True,
             "imgs": ["black-1", "black-2", "black-3 (1)", "black-4", "black-5"]},
            {"name": "Grey",  "hex": "#9E9E9E", "folder": "replacing", "best": True,
             "imgs": ["grey-1", "grey-2", "grey-3", "grey-4"]},
            {"name": "Skin",  "hex": "#F5CBA7", "folder": "replacing", "best": False,
             "imgs": ["skin-1", "skin-2", "skin-3", "skin-4", "skin-5"]},
        ],
    },

    # ── PANTIES ───────────────────────────────────────────────────────────────

    {
        "id": 13, "code": "CP-1132",
        "name": "Lace Hipster Panty",
        "desc": (
            "Add a touch of everyday elegance with our Lace Hipster Panty by Enamor. Featuring "
            "beautiful lace detailing with a comfortable cotton gusset, this hipster sits just "
            "below the natural waist for a flattering mid-rise fit. Soft elastic waistband and "
            "seamless leg openings ensure all-day comfort without riding up."
        ),
        "cat": 2, "ccat": 22,
        "brand": 4,
        "tag": "hipster, lace, cotton, mid-rise, comfortable, best-seller",
        "mrp": 599, "price": 449, "disc": 25,
        "is_cup": False,
        "sizes":  [1,  2,  3,  4,  5,  6,  7],
        "stocks": [3,  5,  8,  8,  5,  4,  3],
        "variants": [
            {"name": "Bark",   "hex": "#C8A882", "folder": "CP-1132", "best": True,
             "imgs": ["Bark -1", "Bark -2", "Bark -3", "Bark -5", "Barrk -4"]},
            {"name": "Black",  "hex": "#1A1A1A", "folder": "CP-1132", "best": True,
             "imgs": ["Black -1", "Black -2", "Black -3", "Black -4", "Black -5", "Black -6"]},
            {"name": "Maroon", "hex": "#800000", "folder": "CP-1132", "best": False,
             "imgs": ["Maroon -1", "Maroon -2", "Maroon -3", "Maroon -4", "Maroon -5"]},
            {"name": "Mist",   "hex": "#B0BEC5", "folder": "CP-1132", "best": False,
             "imgs": ["Mist -1", "Mist -2", "Mist -3", "Mist -4"]},
            {"name": "White",  "hex": "#F5F5F5", "folder": "CP-1132", "best": False,
             "imgs": ["White -1", "White -2", "White -4", "White3"]},
        ],
    },

    {
        "id": 14, "code": "CS-3",
        "name": "Long Cycling Shorts",
        "desc": (
            "Our Long Cycling Shorts by TWAM offer maximum coverage and anti-chafing comfort "
            "under dresses, skirts, or as loungewear. Made from smooth stretchy fabric that moves "
            "freely with your body, these knee-length shorts provide a seamless finish and stay "
            "in place all day. A wardrobe essential for comfort and confidence on the go."
        ),
        "cat": 2, "ccat": 28,
        "brand": 1,
        "tag": "cycling-shorts, long, anti-chafe, coverage, best-seller",
        "mrp": 799, "price": 599, "disc": 25,
        "is_cup": False,
        "sizes":  [1,  2,  3,  4,  5,  6,  7],
        "stocks": [3,  5,  8,  8,  5,  4,  3],
        "variants": [
            {"name": "Black", "hex": "#1A1A1A", "folder": "CS-3", "best": True,
             "imgs": ["Black -1", "Black -2", "Black -3", "Black -4", "Black -5"]},
            {"name": "Nude",  "hex": "#F5CBA7", "folder": "CS-3", "best": True,
             "imgs": ["Nude -1", "Nude -2", "Nude -3", "Nude -4", "Nude -5"]},
            {"name": "White", "hex": "#F5F5F5", "folder": "CS-3", "best": False,
             "imgs": ["White -1", "White -2", "White -3", "White -4", "White -5"]},
        ],
    },

    {
        "id": 15, "code": "CS-4",
        "name": "Short Cycling Shorts",
        "desc": (
            "Stay comfortable and covered with our Short Cycling Shorts by TWAM. Sitting at "
            "mid-thigh length, these lightweight shorts are perfect for wearing under dresses or "
            "as standalone loungewear. The soft elastic waistband and stretch fabric ensure a "
            "secure flattering fit with zero chafing throughout the day."
        ),
        "cat": 2, "ccat": 28,
        "brand": 1,
        "tag": "cycling-shorts, short, anti-chafe, mid-thigh, new-arrival",
        "mrp": 699, "price": 499, "disc": 29,
        "is_cup": False,
        "sizes":  [1,  2,  3,  4,  5,  6,  7],
        "stocks": [3,  5,  8,  8,  5,  4,  3],
        "variants": [
            {"name": "Black", "hex": "#1A1A1A", "folder": "CS-4", "best": True,
             "imgs": ["Black -1", "Black -2", "Black -3", "Black -4", "Black -5"]},
            {"name": "Nude",  "hex": "#F5CBA7", "folder": "CS-4", "best": True,
             "imgs": ["Nude -1", "Nude -2", "Nude -3", "Nude -4", "Nude -5"]},
            {"name": "White", "hex": "#F5F5F5", "folder": "CS-4", "best": False,
             "imgs": ["White -1", "White -2", "White -3", "White -4", "White -5"]},
        ],
    },

    {
        "id": 16, "code": "FP-1705",
        "name": "High-Waist Full Panty",
        "desc": (
            "Our High-Waist Full Panty by Amante combines comfort and coverage in one elegant "
            "design. The premium lace waistband sits high on the waist for a flattering "
            "tummy-smoothing effect, while full rear coverage ensures all-day confidence. A "
            "must-have essential for pairing with high-waist outfits, understated elegance meets "
            "everyday practicality."
        ),
        "cat": 2, "ccat": 29,
        "brand": 3,
        "tag": "high-waist, full-panty, lace, tummy-control, coverage, new-arrival",
        "mrp": 699, "price": 549, "disc": 21,
        "is_cup": False,
        "sizes":  [1,  2,  3,  4,  5,  6,  7],
        "stocks": [3,  5,  8,  8,  5,  4,  3],
        "variants": [
            {"name": "Ash Grey", "hex": "#9E9E9E", "folder": "FP-1705", "best": True,
             "imgs": ["Ash grey -1", "Ash grey -2", "Ash grey -3", "Ash grey -4"]},
            {"name": "Grass",    "hex": "#558B2F", "folder": "FP-1705", "best": True,
             "imgs": ["Grass -1", "Grass -2", "Grass -3", "Grass -4", "Grass -5"]},
        ],
    },

    {
        "id": 17, "code": "3BF-14",
        "name": "Printed Bikini Brief",
        "desc": (
            "Brighten up your everyday with our Printed Bikini Brief by TWAM. Made from soft "
            "stretch fabric with a comfortable elastic waistband, this brief offers a classic "
            "bikini fit with full rear coverage and smooth leg openings. Fun, fresh, and available "
            "in bold playful colours, perfect for mixing and matching with your favourite sets."
        ),
        "cat": 2, "ccat": 30,
        "brand": 1,
        "tag": "bikini, brief, colourful, everyday, stretch, new-arrival",
        "mrp": 499, "price": 349, "disc": 30,
        "is_cup": False,
        "sizes":  [1,  2,  3,  4,  5,  6],
        "stocks": [4,  6, 10,  6,  4,  3],
        "variants": [
            {"name": "Teal",   "hex": "#00695C", "folder": "3BF-14", "best": True,
             "imgs": ["mix -2", "mix -8", "mixed -1", "mixed -2", "mixed -3"]},
            {"name": "Coral",  "hex": "#E53935", "folder": "3BF-14", "best": True,
             "imgs": ["mix -3", "mix -4", "mix-5", "mixed -4", "mixed -5"]},
            {"name": "Purple", "hex": "#9C27B0", "folder": "3BF-14", "best": False,
             "imgs": ["mix -1", "mix -6", "mix-4", "mixed -1"]},
        ],
    },

    # ── ESSENTIALS (cat=3) — NO child category ────────────────────────────────

    {
        "id": 18, "code": "SC-2",
        "name": "Shaping Camisole",
        "desc": (
            "Smooth and shape your silhouette effortlessly with our Shaping Camisole by Blossoms. "
            "Crafted from firm yet comfortable stretch fabric, this camisole provides gentle tummy "
            "control and all-over smoothing under any outfit. Adjustable straps and flexible "
            "construction make it easy to wear from morning to night, style meets function in one "
            "sleek versatile design."
        ),
        "cat": 3, "ccat": None,
        "brand": 6,
        "tag": "shapewear, camisole, tummy-control, smooth, essentials, best-seller",
        "mrp": 999, "price": 749, "disc": 25,
        "is_cup": False,
        "sizes":  [1,  2,  3,  4,  5,  6],
        "stocks": [4,  6, 10, 10,  6,  4],
        "variants": [
            {"name": "Beige", "hex": "#C8A882", "folder": "SC-2", "best": True,
             "imgs": ["beige -2", "beige -3", "beige -4", "beige"]},
            {"name": "Black", "hex": "#1A1A1A", "folder": "SC-2", "best": True,
             "imgs": ["black -2", "black -3", "black -4", "black"]},
            {"name": "White", "hex": "#F5F5F5", "folder": "SC-2", "best": False,
             "imgs": ["White -1", "white -2"]},
        ],
    },
]


# -----------------------------------------------------------------------------
# SEED FUNCTION
# -----------------------------------------------------------------------------

def run_seed():
    print("=" * 60)
    print("  TWAM Seed Script v2 (fixed) -- Starting")
    print("=" * 60)

    with engine.begin() as conn:

        # ── STEP 1: Delete old product data (FK-safe order) ──────────────────
        print("\n[1/7] Deleting old product data...")
        tables_to_clear = [
            'twam."ProductImage"',
            'twam."ProductVariantDetail"',
            'twam."ProductVariants"',
            'twam."Products"',
            'twam."ProductColor"',
            'mdm."brands"',
        ]
        for t in tables_to_clear:
            conn.execute(text(f"DELETE FROM {t}"))
            print(f"      Cleared {t}")

        # Reset sequences to 1
        sequences = [
            ('twam', 'ProductImage',         'ProductImageId'),
            ('twam', 'ProductVariantDetail', 'ProductVariantDetailId'),
            ('twam', 'ProductVariants',      'ProductVariantId'),
            ('twam', 'Products',             'ProductId'),
            ('twam', 'ProductColor',         'ColorId'),
        ]
        for schema, tbl, col in sequences:
            try:
                conn.execute(text(
                    f'ALTER SEQUENCE {schema}."{tbl}_{col}_seq" RESTART WITH 1'
                ))
            except Exception:
                pass
        print("      Sequences reset to 1.")

        # ── STEP 2: Brands ────────────────────────────────────────────────────
        print("\n[2/7] Inserting brands...")
        for b in BRANDS:
            conn.execute(text("""
                INSERT INTO mdm."brands"
                    ("brandId","brandName","brandDescription","brandImage",
                     "isActive","deletedInd","createdDate")
                VALUES
                    (:id,:name,:desc,:img,TRUE,FALSE,NOW())
            """), {"id": b["id"], "name": b["name"],
                   "desc": b["desc"], "img": b["img"]})
        print(f"      {len(BRANDS)} brands inserted.")

        # ── STEP 3: Products ──────────────────────────────────────────────────
        print("\n[3/7] Inserting products...")
        for p in PRODUCTS:
            conn.execute(text("""
                INSERT INTO twam."Products"
                    ("ProductId","ProductCode","Name","Description",
                     "CategoryId","ChildCategoryId","BrandId",
                     "Tag","State","DeletedInd","CreatedDate")
                VALUES
                    (:pid,:code,:name,:desc,
                     :cat,:ccat,:brand,
                     :tag,'Approved',FALSE,NOW())
            """), {
                "pid":   p["id"],
                "code":  p["code"],
                "name":  p["name"],
                "desc":  p["desc"],
                "cat":   p["cat"],
                "ccat":  p.get("ccat"),
                "brand": p["brand"],
                "tag":   p["tag"],
            })
        print(f"      {len(PRODUCTS)} products inserted.")

        # ── STEP 4: Variants ──────────────────────────────────────────────────
        # NOTE: Color stores the colour NAME ("Bark"), NOT the hex.
        #       Hex lives in twam.ProductColor (Step 7).
        print("\n[4/7] Inserting variants...")
        variant_id = 1
        for p in PRODUCTS:
            for v in p["variants"]:
                vname = f"{p['name']} - {v['name']}"
                color_name, _ = resolve_color(v.get("name", ""), v.get("hex", ""))
                conn.execute(text("""
                    INSERT INTO twam."ProductVariants"
                        ("ProductVariantId","ProductId","VariantName","ProductCode",
                         "Color","IsBestSeller","IsCupSize","IsReturnAvailable",
                         "State","DeletedInd","CreatedDate")
                    VALUES
                        (:vid,:pid,:vname,:code,
                         :color,:best,:cup,TRUE,
                         'Approved',FALSE,NOW())
                """), {
                    "vid":   variant_id,
                    "pid":   p["id"],
                    "vname": vname,
                    "code":  p["code"],
                    "color": color_name,
                    "best":  v.get("best", False),
                    "cup":   p["is_cup"],
                })
                v["_vid"] = variant_id
                variant_id += 1
        print(f"      {variant_id - 1} variants inserted.")

        # ── STEP 5: Variant Details (stock) ───────────────────────────────────
        print("\n[5/7] Inserting variant details (stock)...")
        detail_id = 1
        for p in PRODUCTS:
            for v in p["variants"]:
                vid = v["_vid"]
                if not p["is_cup"]:
                    # Alpha-sized products
                    for sz, stock in zip(p["sizes"], p["stocks"]):
                        conn.execute(text("""
                            INSERT INTO twam."ProductVariantDetail"
                                ("ProductVariantDetailId","ProductId","ProductVariantId",
                                 "ProductCode","Size","StockQuantity","ProcessedQuantity",
                                 "ReturnedQuantity","AvailableQuantity","DiscountPercent",
                                 "MRPPrice","FinalPrice","CupSize",
                                 "IsLowStock","IsOutOfStock","IsAlphabetSize",
                                 "State","DeletedInd","CreatedDate")
                            VALUES
                                (:did,:pid,:vid,
                                 :code,:sz,:stock,0,
                                 0,:stock,:disc,
                                 :mrp,:price,NULL,
                                 :low,FALSE,TRUE,
                                 'Approved',FALSE,NOW())
                        """), {
                            "did":   detail_id,
                            "pid":   p["id"],
                            "vid":   vid,
                            "code":  p["code"],
                            "sz":    sz,
                            "stock": stock,
                            "disc":  p["disc"],
                            "mrp":   p["mrp"],
                            "price": p["price"],
                            "low":   stock <= 3,
                        })
                        detail_id += 1
                else:
                    # Band × Cup matrix products
                    for band in p["bands"]:
                        for cup in p["cups"]:
                            stock = p["stock_cup"]
                            conn.execute(text("""
                                INSERT INTO twam."ProductVariantDetail"
                                    ("ProductVariantDetailId","ProductId","ProductVariantId",
                                     "ProductCode","Size","StockQuantity","ProcessedQuantity",
                                     "ReturnedQuantity","AvailableQuantity","DiscountPercent",
                                     "MRPPrice","FinalPrice","CupSize",
                                     "IsLowStock","IsOutOfStock","IsAlphabetSize",
                                     "State","DeletedInd","CreatedDate")
                                VALUES
                                    (:did,:pid,:vid,
                                     :code,:band,:stock,0,
                                     0,:stock,:disc,
                                     :mrp,:price,:cup,
                                     FALSE,FALSE,FALSE,
                                     'Approved',FALSE,NOW())
                            """), {
                                "did":   detail_id,
                                "pid":   p["id"],
                                "vid":   vid,
                                "code":  p["code"],
                                "band":  band,
                                "stock": stock,
                                "disc":  p["disc"],
                                "mrp":   p["mrp"],
                                "price": p["price"],
                                "cup":   cup,
                            })
                            detail_id += 1
        print(f"      {detail_id - 1} stock rows inserted.")

        # ── STEP 6: Product Images ────────────────────────────────────────────
        print("\n[6/7] Inserting product images (.png)...")
        img_id = 1
        for p in PRODUCTS:
            for v in p["variants"]:
                vid    = v["_vid"]
                folder = v["folder"]
                for fname in v["imgs"]:
                    full  = f"{fname}.png"
                    fpath = f"/image/{folder}/{full}"
                    conn.execute(text("""
                        INSERT INTO twam."ProductImage"
                            ("ProductImageId","ProductId","ProductVariantId",
                             "FileName","FileType","FilePath",
                             "DeletedInd","CreatedDate")
                        VALUES
                            (:iid,:pid,:vid,
                             :fname,'image/png',:fpath,
                             FALSE,NOW())
                    """), {
                        "iid":   img_id,
                        "pid":   p["id"],
                        "vid":   vid,
                        "fname": full,
                        "fpath": fpath,
                    })
                    img_id += 1
        print(f"      {img_id - 1} images inserted.")

        # ── STEP 7: Product Colours ───────────────────────────────────────────
        # Unique colour name + exact hex stored in twam.ProductColor.
        # resolve_color() fills in whichever field is missing automatically.
        print("\n[7/7] Inserting product colours...")
        seen_names: set = set()
        color_id = 1
        for p in PRODUCTS:
            for v in p["variants"]:
                color_name, color_hex = resolve_color(v.get("name", ""), v.get("hex", ""))
                name_key = color_name.lower().strip()
                if name_key and name_key not in seen_names:
                    seen_names.add(name_key)
                    conn.execute(text("""
                        INSERT INTO twam."ProductColor"
                            ("ColorId","ColorName","HexValue","CreatedDate")
                        VALUES
                            (:cid,:cname,:hex,NOW())
                    """), {"cid": color_id, "cname": color_name, "hex": color_hex})
                    color_id += 1
        print(f"      {color_id - 1} unique colours inserted.")  # ← FIXED: now inside `with` block

        # ── Update sequences to max used IDs ──────────────────────────────────
        seq_vals = [
            ('twam', 'Products',             'ProductId',              max(p["id"] for p in PRODUCTS)),
            ('twam', 'ProductVariants',      'ProductVariantId',       variant_id - 1),
            ('twam', 'ProductVariantDetail', 'ProductVariantDetailId', detail_id  - 1),
            ('twam', 'ProductImage',         'ProductImageId',         img_id      - 1),
            ('twam', 'ProductColor',         'ColorId',                color_id    - 1),
        ]
        for schema, tbl, col, val in seq_vals:
            try:
                conn.execute(text(
                    f"SELECT setval('{schema}.\"{tbl}_{col}_seq\"', {val}, TRUE)"
                ))
            except Exception:
                pass
        print("      Sequences updated to max used IDs.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  SEED COMPLETE")
    print("=" * 60)
    print(f"  Brands           : {len(BRANDS)}")
    print(f"  Products         : {len(PRODUCTS)}")
    print(f"    Bras           : {sum(1 for p in PRODUCTS if p['cat'] == 1)}")
    print(f"    Panties/Shorts : {sum(1 for p in PRODUCTS if p['cat'] == 2)}")
    print(f"    Essentials     : {sum(1 for p in PRODUCTS if p['cat'] == 3)}")
    print(f"  Variants         : {variant_id - 1}")
    print(f"  Stock rows       : {detail_id - 1}")
    print(f"  Images (.png)    : {img_id - 1}")
    print(f"  Colours          : {color_id - 1}")
    print(f"  New Arrivals     : {sum(1 for p in PRODUCTS if 'new-arrival' in p['tag'])}")
    print(f"  Best Sellers     : {sum(1 for p in PRODUCTS if 'best-seller' in p['tag'])}")
    print(f"  mdm.Size         : UNTOUCHED")
    print(f"  mdm.CupSize      : UNTOUCHED")
    print("=" * 60)


if __name__ == "__main__":
    run_seed()