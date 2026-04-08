"""
app/bulkimport/router.py
─────────────────────────
Bulk import endpoint — accepts an Excel (.xlsx) file and creates records
in bulk for: products, categories, brands, sizes, product_variants, coupons.

POST /api/BulkImport/{entity}  → { success, errors, inserted, rows }
GET  /api/BulkImport/template/{entity} → returns an XLSX template to download
"""

import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    import openpyxl
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from database import get_db
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    prefix="/api/BulkImport",
    tags=["Bulk Import"],
    dependencies=[Depends(get_current_user)],
)

# ── Column definitions per entity ──────────────────────────────────────────────

ENTITY_CONFIG = {
    "products": {
        "columns": [
            ("productCode",    "Product Code*",    "str",   True),
            ("name",           "Product Name*",    "str",   True),
            ("description",    "Description*",     "str",   True),
            ("categoryId",     "Category ID*",     "int",   True),
            ("brandId",        "Brand ID*",        "int",   True),
            ("tag",            "Tags",             "str",   False),
            ("childCategoryId","Child Category ID","int",   False),
        ],
        "table":  'twam."products"',
        "schema": "twam",
        "required": ["productCode", "name", "description", "categoryId", "brandId"],
        "notes": "Get Category ID from Categories page · Get Brand ID from Brands page",
    },
    "categories": {
        "columns": [
            ("name",              "Name*",              "str", True),
            ("description",       "Description",        "str", False),
            ("parentCategoryId",  "Parent Category ID", "int", False),
        ],
        "table":  'mdm."categories"',
        "schema": "mdm",
        "required": ["name"],
        "notes": "Leave Parent Category ID blank for top-level categories",
    },
    "brands": {
        "columns": [
            ("brandName",        "Brand Name*",       "str",  True),
            ("brandDescription", "Description",       "str",  False),
        ],
        "table":  'mdm."brands"',
        "schema": "mdm",
        "required": ["brandName"],
        "notes": "Brand images must be uploaded separately via the Brands page",
    },
    "sizes": {
        "columns": [
            ("sizeLabel",  "Size Label*", "str", True),
            ("sizeCode",   "Size Code*",  "str", True),
            ("description","Description", "str", False),
            ("dimensions", "Dimensions",  "str", False),
            ("orderNo",    "Order No",    "int", False),
        ],
        "table":  'mdm."sizes"',
        "schema": "mdm",
        "required": ["sizeLabel", "sizeCode"],
        "notes": "Order No controls the display order (1 = first)",
    },
    "coupons": {
        "columns": [
            ("couponCode",      "Coupon Code*",    "str",   True),
            ("discountType",    "Discount Type*",  "str",   True),  # Flat / Percent
            ("discountValue",   "Discount Value*", "float", True),
            ("minOrderAmount",  "Min Order Amount","float", False),
            ("maxUses",         "Max Uses",        "int",   False),
            ("expiryDate",      "Expiry Date",     "str",   False),  # YYYY-MM-DD
        ],
        "table":  'twam."coupons"',
        "schema": "twam",
        "required": ["couponCode", "discountType", "discountValue"],
        "notes": "Discount Type must be 'Flat' or 'Percent'",
    },
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _check_openpyxl():
    if not OPENPYXL_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="openpyxl is not installed on the server. Run: pip install openpyxl"
        )


def _cast(value, dtype: str):
    """Cast a cell value to the expected Python type."""
    if value is None or str(value).strip() == "":
        return None
    try:
        if dtype == "int":
            return int(float(str(value).strip()))
        elif dtype == "float":
            return float(str(value).strip())
        else:
            return str(value).strip()
    except (ValueError, TypeError):
        raise ValueError(f"Cannot cast '{value}' to {dtype}")


def _parse_excel(file_bytes: bytes, entity: str) -> list[dict]:
    """
    Parse the uploaded Excel file and return a list of row dicts.
    Raises HTTPException for structural errors.
    """
    _check_openpyxl()
    cfg = ENTITY_CONFIG[entity]
    col_defs = cfg["columns"]  # [(field, header, dtype, required)]

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read Excel file: {e}")

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status_code=400, detail="The Excel file is empty.")

    # Map header row → column index (case-insensitive, strip asterisks)
    header_row = [str(h).strip().rstrip("*").strip() if h else "" for h in rows[0]]
    field_map: dict[str, int] = {}
    for col_idx, header in enumerate(header_row):
        for field, col_label, dtype, req in col_defs:
            clean_label = col_label.rstrip("*").strip()
            if header.lower() == clean_label.lower() or header.lower() == field.lower():
                field_map[field] = col_idx

    # Validate that required fields are present
    for field, label, dtype, req in col_defs:
        if req and field not in field_map:
            raise HTTPException(
                status_code=400,
                detail=f"Required column '{label}' not found in the Excel header row. "
                       f"Download the template to see the correct format."
            )

    # Build dtype lookup
    dtype_map = {field: dtype for field, _, dtype, _ in col_defs}

    result = []
    for row_num, row in enumerate(rows[1:], start=2):
        # Skip fully empty rows
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue

        record: dict = {}
        row_errors = []

        for field, label, dtype, required in col_defs:
            if field not in field_map:
                if not required:
                    record[field] = None
                continue
            raw = row[field_map[field]] if field_map[field] < len(row) else None
            try:
                val = _cast(raw, dtype_map[field])
            except ValueError:
                row_errors.append(f"Column '{label}': invalid value '{raw}'")
                val = None

            if required and val is None:
                row_errors.append(f"Column '{label}' is required")

            record[field] = val

        record["_row"] = row_num
        record["_errors"] = row_errors
        result.append(record)

    return result


# ── GET /api/BulkImport/entities ──────────────────────────────────────────────
@router.get("/entities")
def list_entities():
    """Return the list of supported entities for bulk import."""
    return {
        "entities": [
            {
                "key": k,
                "label": k.replace("_", " ").title(),
                "columns": [c[1] for c in v["columns"]],
                "required": v["required"],
                "notes": v["notes"],
            }
            for k, v in ENTITY_CONFIG.items()
        ]
    }


# ── GET /api/BulkImport/template/{entity} ────────────────────────────────────
@router.get("/template/{entity}")
def download_template(entity: str):
    """Download a pre-formatted Excel template for the given entity."""
    _check_openpyxl()
    if entity not in ENTITY_CONFIG:
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not supported.")

    cfg = ENTITY_CONFIG[entity]
    col_defs = cfg["columns"]

    wb = Workbook()
    ws = wb.active
    ws.title = entity.title()

    # ── Style helpers ──
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    header_font  = Font(bold=True, color="FFFFFF", size=11)
    header_fill  = PatternFill("solid", fgColor="6B0F2A")   # TWAM brand dark
    req_fill     = PatternFill("solid", fgColor="F5E6EA")   # light pink for required
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border  = Border(
        left=Side(style="thin", color="DDDDDD"),
        right=Side(style="thin", color="DDDDDD"),
        top=Side(style="thin", color="DDDDDD"),
        bottom=Side(style="thin", color="DDDDDD"),
    )

    # Header row
    for col_idx, (field, label, dtype, required) in enumerate(col_defs, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = center_align
        cell.border    = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = max(20, len(label) + 4)

    # Sample row
    SAMPLE_ROW = {
        "productCode":    "PRD-001",
        "name":           "Sample Product",
        "description":    "A brief description of the product",
        "categoryId":     1,
        "brandId":        1,
        "tag":            "summer,casual",
        "childCategoryId":"",
        "brandName":      "Sample Brand",
        "brandDescription":"Brand description here",
        "name_brand":     "Sample Brand",
        "name_cat":       "Category Name",
        "description_cat":"Category description",
        "parentCategoryId":"",
        "sizeLabel":      "S",
        "sizeCode":       "S",
        "dimensions":     "Chest: 34-36in",
        "orderNo":        1,
        "couponCode":     "SAVE10",
        "discountType":   "Percent",
        "discountValue":  10,
        "minOrderAmount": 500,
        "maxUses":        100,
        "expiryDate":     "2025-12-31",
    }

    for col_idx, (field, label, dtype, required) in enumerate(col_defs, start=1):
        sample_val = SAMPLE_ROW.get(field, "")
        cell = ws.cell(row=2, column=col_idx, value=sample_val)
        if required:
            cell.fill = req_fill
        cell.border = thin_border

    # Notes row
    notes_row = len(col_defs) + 4
    ws.cell(row=4, column=1, value="📌 Notes:").font = Font(bold=True, size=10)
    ws.cell(row=5, column=1, value=cfg["notes"]).font = Font(italic=True, color="666666", size=9)
    ws.cell(row=6, column=1, value="• Required fields are marked with * in the header").font = Font(italic=True, color="666666", size=9)
    ws.cell(row=7, column=1, value="• Row 2 is a sample — replace with your data and delete this row").font = Font(italic=True, color="666666", size=9)
    ws.cell(row=8, column=1, value=f"• Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}").font = Font(italic=True, color="999999", size=8)

    # Freeze header
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30

    # Stream response
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"twam_{entity}_template.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── POST /api/BulkImport/preview/{entity} ─────────────────────────────────────
@router.post("/preview/{entity}")
async def preview_import(
    entity: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Parse the Excel file and return a preview of rows WITHOUT inserting.
    Frontend shows this preview table so the admin can confirm before importing.
    """
    if entity not in ENTITY_CONFIG:
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not supported.")

    content = await file.read()
    rows = _parse_excel(content, entity)

    valid_rows   = [r for r in rows if not r["_errors"]]
    invalid_rows = [r for r in rows if r["_errors"]]

    return {
        "entity":       entity,
        "totalRows":    len(rows),
        "validRows":    len(valid_rows),
        "invalidRows":  len(invalid_rows),
        "columns":      [c[1] for c in ENTITY_CONFIG[entity]["columns"]],
        "rows":         rows[:200],   # cap preview at 200 rows
        "canImport":    len(valid_rows) > 0,
    }


# ── POST /api/BulkImport/import/{entity} ──────────────────────────────────────
@router.post("/import/{entity}")
async def execute_import(
    entity: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Parse and INSERT valid rows into the database.
    Returns a summary: { inserted, skipped, errors }.
    """
    if entity not in ENTITY_CONFIG:
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not supported.")

    # Only admins / product managers can import
    if current_user.role_id not in {Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER, Roles.INVENTORY_MANAGER}:
        raise HTTPException(status_code=403, detail="Insufficient permissions for bulk import.")

    content = await file.read()
    rows = _parse_excel(content, entity)

    inserted = 0
    skipped  = 0
    row_errors = []
    now = datetime.now(timezone.utc)

    for row in rows:
        if row["_errors"]:
            skipped += 1
            row_errors.append({
                "row": row["_row"],
                "errors": row["_errors"],
            })
            continue

        try:
            _insert_row(db, entity, row, current_user.user_id, now)
            inserted += 1
        except Exception as e:
            skipped += 1
            row_errors.append({"row": row["_row"], "errors": [str(e)]})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")

    return {
        "entity":   entity,
        "inserted": inserted,
        "skipped":  skipped,
        "errors":   row_errors[:50],   # cap error list
        "message":  f"Successfully imported {inserted} {entity}. {skipped} rows skipped.",
    }


# ── Entity-specific insert logic ───────────────────────────────────────────────

def _insert_row(db: Session, entity: str, row: dict, user_id: str, now: datetime):
    """Insert a single validated row into the appropriate table."""

    if entity == "products":
        db.execute(text("""
            INSERT INTO twam."products"
              ("productCode","name","description","categoryId","childCategoryId","brandId","tag",
               "state","userProfileId","createdBy","modifiedBy","createdDate","modifiedDate","deletedInd")
            VALUES
              (:productCode,:name,:description,:categoryId,:childCategoryId,:brandId,:tag,
               'Created',:userId,:userId,:userId,:now,:now,false)
        """), {**row, "userId": user_id, "now": now})

    elif entity == "categories":
        db.execute(text("""
            INSERT INTO mdm."categories"
              ("name","description","parentCategoryId","userProfileId","state",
               "isActive","createdBy","modifiedBy","createdDate","modifiedDate","deletedInd")
            VALUES
              (:name,:description,:parentCategoryId,:userId,'Active',
               true,:userId,:userId,:now,:now,false)
        """), {**row, "userId": user_id, "now": now})

    elif entity == "brands":
        db.execute(text("""
            INSERT INTO mdm."brands"
              ("brandName","brandDescription","userProfileId","state",
               "isActive","createdDate","modifiedDate","deletedInd")
            VALUES
              (:brandName,:brandDescription,:userId,'Active',
               true,:now,:now,false)
        """), {**row, "userId": user_id, "now": now})

    elif entity == "sizes":
        db.execute(text("""
            INSERT INTO mdm."sizes"
              ("sizeLabel","sizeCode","description","dimensions","orderNo",
               "state","isActive","userProfileId","createdDate","modifiedDate","deletedInd")
            VALUES
              (:sizeLabel,:sizeCode,:description,:dimensions,:orderNo,
               'Active',true,:userId,:now,:now,false)
        """), {**row, "userId": user_id, "now": now})

    elif entity == "coupons":
        expiry = None
        if row.get("expiryDate"):
            try:
                expiry = datetime.strptime(row["expiryDate"], "%Y-%m-%d").date()
            except ValueError:
                pass

        db.execute(text("""
            INSERT INTO twam."coupons"
              ("couponCode","discountType","discountValue","minOrderAmount","maxUses",
               "expiryDate","isActive","usedCount","userProfileId",
               "createdDate","modifiedDate","deletedInd")
            VALUES
              (:couponCode,:discountType,:discountValue,:minOrderAmount,:maxUses,
               :expiryDate,true,0,:userId,
               :now,:now,false)
        """), {**row, "expiryDate": expiry, "userId": user_id, "now": now})

    else:
        raise ValueError(f"No insert handler for entity '{entity}'")
