"""
color_init.py
Auto-creates and populates twam."ProductColor" table at startup.
pv."Color" stores hex values (e.g. #1a1a1a), so:
  ColorName = the hex string from pv.Color
  HexValue  = same hex string (used for proximity search)
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


def init_product_color_table(db: Session) -> None:
    # Step 1: Create table
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS twam."ProductColor" (
            "ColorId"     SERIAL PRIMARY KEY,
            "ColorName"   TEXT NOT NULL UNIQUE,
            "HexValue"    TEXT NOT NULL,
            "CreatedDate" TIMESTAMP DEFAULT NOW()
        )
    """))
    db.commit()

    # Step 2: Get all distinct pv.Color values (these are hex strings)
    rows = db.execute(text("""
        SELECT DISTINCT "Color"
        FROM twam."ProductVariants"
        WHERE "Color" IS NOT NULL
          AND "Color" != ''
          AND ("DeletedInd" = false OR "DeletedInd" IS NULL)
    """)).fetchall()

    # Step 3: Upsert — ColorName = hex string, HexValue = same hex string
    for (color_val,) in rows:
        if not color_val:
            continue
        hex_val = color_val.strip().lower()
        # Ensure it is a valid hex (starts with #)
        if not hex_val.startswith('#'):
            # It's a color name — try to map it
            from app.shared.color_utils import resolve_hex
            hex_val = resolve_hex(hex_val) or '#808080'
        db.execute(text("""
            INSERT INTO twam."ProductColor" ("ColorName", "HexValue")
            VALUES (:name, :hex)
            ON CONFLICT ("ColorName")
            DO UPDATE SET "HexValue" = EXCLUDED."HexValue"
        """), {"name": color_val.strip(), "hex": hex_val})

    db.commit()