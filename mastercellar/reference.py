"""Opt-in reference-matched demo. No order/payment/customer write endpoints.

The supplied media bundle creates isolated TMC-REF-* Items. The replica reads
these Items and their current ERPNext retail Item Prices on every page request.
The earlier demo/imports and their routes remain untouched.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import zipfile
from io import BytesIO

import frappe
from frappe.utils import getdate, nowdate

SITE = "mastercellar.kodetrek.com"
STATE = "mastercellar-reference.json"
PRICE_LIST = "Master Cellar Retail"
MAX_PRODUCTS = 200
MAX_BYTES = 32 * 1024 * 1024
PREFIX = "TMC-REF-"
CATEGORIES = ["Events", "Wine Hampers", "Gift Sets", "Maltese Wines", "Foreign Wines",
              "Sparkling Wines", "Fortified Wines", "Dessert Wines", "Spirits", "Liqueurs",
              "Beer & Ciders", "Non-Alcoholics", "Accessories", "Scented Candles", "Gourmet Items"]


def money_cents(value):
    """Convert valid non-negative prices to integer cents, never binary floats."""
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > 100000:
            return None
        return int((number * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return None


def safe_json(value):
    """JSON safe to embed in a non-executable script element."""
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def validate_bundle(manifest, names):
    if not isinstance(manifest, dict) or manifest.get("version") != "20261015-reference-v1":
        raise ValueError("Unsupported reference bundle version")
    products = manifest.get("products")
    files = manifest.get("files")
    if not isinstance(products, list) or not 1 <= len(products) <= MAX_PRODUCTS:
        raise ValueError("Reference catalogue must contain 1–200 products")
    if not isinstance(files, dict) or not 1 <= len(files) <= 300:
        raise ValueError("Invalid media manifest")
    for name, digest in files.items():
        if not re.fullmatch(r"[A-Za-z0-9._-]+\.(png|jpg|jpeg|webp|svg)", name):
            raise ValueError("Unsafe or unsupported asset filename")
        if not re.fullmatch(r"[a-f0-9]{64}", str(digest)) or "images/" + name not in names:
            raise ValueError("Missing or invalid asset: " + name)
    codes = set()
    for p in products:
        if not isinstance(p, dict) or not re.fullmatch(r"TMC-REF-[A-F0-9]{12}", p.get("item_code", "")):
            raise ValueError("Only isolated TMC-REF-* product codes are permitted")
        if p["item_code"] in codes:
            raise ValueError("Duplicate reference product code")
        codes.add(p["item_code"])
        if not isinstance(p.get("name"), str) or not 1 <= len(p["name"]) <= 140:
            raise ValueError("Invalid product name")
        if money_cents(p.get("price")) is None or p.get("image") not in files:
            raise ValueError("Missing price or photograph for " + p["item_code"])
        if not p.get("categories") or any(c not in CATEGORIES for c in p["categories"]):
            raise ValueError("Invalid reference category")
        if len(str(p.get("description", ""))) > 10000:
            raise ValueError("Description too long")
    if not isinstance(manifest.get("brand"), dict) or any(n not in files for n in manifest["brand"].values()):
        raise ValueError("Missing brand asset")
    return manifest


def _state_path():
    return Path(frappe.get_site_path("private", STATE))


def _load_state():
    path = _state_path()
    if not path.is_file():
        return None
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Reference state exceeds expected size")
    return json.loads(path.read_text(encoding="utf-8"))


def install_bundle(file_name="mastercellar-reference-assets.zip", dry_run=True):
    """CLI only. Preview by default; opt in with --kwargs '{"dry_run":False}'.

    Upload the supplied ZIP as a PRIVATE File in the demo site first. This never
    downloads from WordPress, changes existing product values, or changes the
    site's homepage. File assets are public so the demo can display them.
    """
    if frappe.local.site != SITE:
        frappe.throw("This installer is restricted to the Master Cellar demo site")
    if type(dry_run) is not bool:
        raise ValueError("dry_run must be a Python boolean, True or False")
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.zip", str(file_name)):
        raise ValueError("Use the uploaded ZIP basename, not a path")
    root = Path(frappe.get_site_path("private", "files")).resolve()
    path = (root / file_name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Upload the ZIP as a private File on this site first")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Reference ZIP is too large")
    payloads = {}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 400 or sum(x.file_size for x in entries) > MAX_BYTES:
            raise ValueError("Reference archive exceeds extraction limits")
        if len({x.filename for x in entries}) != len(entries):
            raise ValueError("Duplicate ZIP paths")
        manifest = validate_bundle(json.loads(archive.read("manifest.json")), archive.namelist())
        for name, digest in manifest["files"].items():
            payload = archive.read("images/" + name)
            if len(payload) > 5 * 1024 * 1024 or hashlib.sha256(payload).hexdigest() != digest:
                raise ValueError("Asset hash/size validation failed: " + name)
            if name.endswith(".svg"):
                # The bundle contains only original logo SVGs, not executable SVG.
                from xml.etree import ElementTree as ET
                if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
                    raise ValueError("SVG entities/DOCTYPE are not permitted")
                tree = ET.fromstring(payload)
                for element in tree.iter():
                    tag = element.tag.rsplit("}", 1)[-1].lower()
                    if tag not in {"svg", "g", "path", "defs", "clippath", "rect", "circle", "polygon", "polyline", "line", "ellipse", "style", "title", "desc"}:
                        raise ValueError("Unsupported SVG element")
                    if tag == "style" and any(token in (element.text or "").lower() for token in ("url(", "@import", "javascript:", "data:")):
                        raise ValueError("Unsupported SVG stylesheet")
                    for key, value in element.attrib.items():
                        if key.lower().startswith("on") or key.rsplit("}", 1)[-1].lower() == "href":
                            raise ValueError("Unsupported SVG attribute")
                        if "url(" in str(value).lower() and not re.fullmatch(r"url\(#[A-Za-z_][A-Za-z0-9_.-]*\)", value):
                            raise ValueError("Unsupported SVG resource reference")
            else:
                from PIL import Image
                with Image.open(BytesIO(payload)) as image:
                    if image.width * image.height > 25000000:
                        raise ValueError("Reference image dimensions too large")
                    image.verify()
            payloads[name] = payload
    result = {"site": frappe.local.site, "dry_run": dry_run,
              "reference_products": len(manifest["products"]), "media_files": len(payloads),
              "created_items": 0, "created_prices": 0, "existing_items": 0}
    if dry_run:
        return result
    if not frappe.db.exists("Item Group", "All Item Groups"):
        frappe.throw("Complete ERPNext setup first")
    unit = next((u for u in ("Nos", "Unit") if frappe.db.exists("UOM", u)), None)
    if not unit:
        frappe.throw("A Nos or Unit UOM is required")
    group = "Master Cellar Reference"
    if not frappe.db.exists("Item Group", group):
        frappe.get_doc({"doctype": "Item Group", "item_group_name": group,
                        "parent_item_group": "All Item Groups", "is_group": 0}).insert(ignore_permissions=True)
    if not frappe.db.exists("Price List", PRICE_LIST):
        frappe.get_doc({"doctype": "Price List", "price_list_name": PRICE_LIST,
                        "currency": "EUR", "selling": 1, "enabled": 1}).insert(ignore_permissions=True)
    elif frappe.db.get_value("Price List", PRICE_LIST, "currency") != "EUR":
        frappe.throw("Reference price list must be in EUR")
    from frappe.utils.file_manager import save_file
    previous = _load_state() or {}
    urls = {}
    for name, payload in payloads.items():
        old_url = previous.get("asset_urls", {}).get(name)
        # Reuse only this exact bundle's existing File records.
        if (previous.get("files", {}).get(name) == manifest["files"][name]
                and old_url and frappe.db.exists("File", {"file_url": old_url, "is_private": 0})):
            urls[name] = old_url
        else:
            saved = save_file("tmc-ref-" + name, payload, None, None, is_private=0)
            urls[name] = saved.file_url
    for p in manifest["products"]:
        code = p["item_code"]
        if frappe.db.exists("Item", code):
            result["existing_items"] += 1
        else:
            frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": p["name"],
                            "description": p.get("description") or p["name"], "stock_uom": unit,
                            "item_group": group, "image": urls[p["image"]],
                            "is_stock_item": 0, "is_sales_item": 1, "disabled": 0}).insert(ignore_permissions=True)
            result["created_items"] += 1
        if not frappe.db.exists("Item Price", {"item_code": code, "price_list": PRICE_LIST}):
            frappe.get_doc({"doctype": "Item Price", "item_code": code, "price_list": PRICE_LIST,
                            "currency": "EUR", "selling": 1, "uom": unit,
                            "price_list_rate": float(Decimal(p["price"])),
                            "note": "15-Oct-2026 screenshot reference; VAT-inclusive display only. Demo, not transactional pricing."}).insert(ignore_permissions=True)
            result["created_prices"] += 1
    manifest["asset_urls"] = urls
    target = _state_path()
    staged = target.with_suffix(".pending")
    staged.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    # Publish the presentation manifest only after database records are durable.
    frappe.db.commit()
    staged.replace(target)
    return result


def get_payload():
    state = _load_state()
    empty = {"ready": False, "products": [], "brand": {}, "categories": CATEGORIES,
             "captured_on": "2026-10-15", "source": "ERPNext reference catalogue"}
    if not state:
        return empty
    metadata = {p["item_code"]: p for p in state["products"] if p["item_code"].startswith(PREFIX)}
    codes = list(metadata)[:MAX_PRODUCTS]
    items = frappe.get_all("Item", filters={"item_code": ["in", codes], "disabled": 0, "is_sales_item": 1},
                           fields=["item_code", "item_name", "description", "image", "stock_uom"],
                           limit_page_length=MAX_PRODUCTS) if codes else []
    prices = frappe.get_all("Item Price", filters={"item_code": ["in", codes], "price_list": PRICE_LIST,
                                                    "currency": "EUR", "selling": 1},
                            fields=["item_code", "price_list_rate", "valid_from", "valid_upto", "customer", "supplier", "batch_no", "uom"],
                            order_by="valid_from desc, modified desc", limit_page_length=2000) if codes else []
    units = {p.item_code: p.stock_uom for p in items}
    rates = {}
    today = getdate(nowdate())
    for p in prices:
        if p.item_code in rates or p.customer or p.supplier or p.batch_no:
            continue
        if p.uom and p.uom != units.get(p.item_code):
            continue
        if p.valid_from and getdate(p.valid_from) > today or p.valid_upto and getdate(p.valid_upto) < today:
            continue
        cents = money_cents(p.price_list_rate)
        if cents is not None:
            rates[p.item_code] = cents
    rows = []
    from frappe.utils import strip_html
    for item in items:
        meta = metadata[item.item_code]
        image = item.image or state["asset_urls"].get(meta["image"], "")
        if not image.startswith("/files/"):
            image = ""  # This demo serves only local public product media.
        rows.append({"code": item.item_code, "name": item.item_name,
                     "description": strip_html(item.description or ""), "image": image,
                     "cents": rates.get(item.item_code), "categories": meta["categories"],
                     "featured": bool(meta.get("featured")), "position": meta.get("position", 999)})
    rows.sort(key=lambda p: p["position"])
    return {**empty, "ready": True, "products": rows,
            "brand": {key: state["asset_urls"].get(value, "") for key, value in state["brand"].items()}}


def health_check():
    data = get_payload()
    return {"ready": data["ready"], "visible_products": len(data["products"]),
            "priced_products": sum(p["cents"] is not None for p in data["products"]),
            "products_with_images": sum(bool(p["image"]) for p in data["products"]),
            "transactional": False}


def get_context(context):
    context.title = "The Master Cellar"
    context.no_cache = True
    context.full_width = True
    context.body_class = "tmc-reference-page"
    context.reference_json = safe_json(get_payload())
