"""Opt-in public WooCommerce catalogue importer for the isolated Master Cellar demo.

Read-only preview first; import only on explicit command. Never requests Woo customer,
order, account or payment information. The import deliberately never modifies a
pre-existing ERPNext Item or Item Price, and never creates a Sales Order.
"""

from decimal import Decimal, InvalidOperation
import csv
import re
from pathlib import Path
from html import unescape
from io import BytesIO
from time import sleep
from urllib.parse import urlparse, urljoin

import frappe
import requests
from frappe.utils import strip_html
from frappe.utils.file_manager import save_file

SOURCE = "https://www.themastercellar.com"
API = SOURCE + "/wp-json/wc/store/v1/products"
DEMO_PREFIX = "TMC-WC-"
PRICE_LIST = "Master Cellar Retail"
MAX_PRODUCTS = 60
REQUEST_TIMEOUT = (5, 18)
IMAGE_LIMIT_BYTES = 4 * 1024 * 1024
UA = "MasterCellarERPNextDemoImporter/0.1 (authorized product preview)"

# The live site's menu includes these labels. Categories may evolve: unknown
# ones are intentionally mapped to Other rather than creating arbitrary groups.
GROUPS = (
    ("Master Cellar Products", "All Item Groups", 1),
    ("Maltese Wines", "Master Cellar Products", 0),
    ("Foreign Wines", "Master Cellar Products", 0),
    ("Spirits", "Master Cellar Products", 0),
    ("Beer & Cider", "Master Cellar Products", 0),
    ("Gift Hampers", "Master Cellar Products", 0),
    ("Gourmet", "Master Cellar Products", 0),
    ("Other", "Master Cellar Products", 0),
)


def _allowed_source_host(url):
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and (
            parsed.hostname == "themastercellar.com"
            or parsed.hostname.endswith(".themastercellar.com")
        )
        and not parsed.username
        and not parsed.password
        and parsed.port in (None, 443)
    )


def _get_products(max_items):
    size = min(max(int(max_items), 1), MAX_PRODUCTS)
    result = []
    with requests.Session() as session:
        session.headers.update({"User-Agent": UA, "Accept": "application/json"})
        page = 1
        while len(result) < size:
            request_url = API
            params = {"per_page": min(size - len(result), 24), "page": page, "type": "simple"}
            for hop in range(3):
                resp = session.get(
                    request_url, params=params, timeout=REQUEST_TIMEOUT, allow_redirects=False,
                )
                if resp.status_code not in (301, 302, 307, 308):
                    break
                redirected = urljoin(request_url, resp.headers.get("Location", ""))
                if not _allowed_source_host(redirected) or hop == 2:
                    raise RuntimeError("Woo Store API redirect left the approved domain or exceeded limit")
                request_url = redirected
                params = None
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Woo Store API HTTP {resp.status_code}; "
                    "the site may disable the public endpoint or require its owner's export."
                )
            if "json" not in resp.headers.get("content-type", "").lower():
                raise RuntimeError("Woo Store API did not return JSON; use an authorised WooCommerce export.")
            body = resp.json()
            if not isinstance(body, list):
                raise RuntimeError("Unexpected WooCommerce Store API response format.")
            if not body:
                break
            for product in body:
                if product.get("type") == "simple" and isinstance(product.get("id"), int):
                    result.append(product)
                    if len(result) == size:
                        break
            page += 1
            if page > 6 or len(body) < min(size - len(result), 24):
                break
            sleep(0.4)
    return result


def _group(categories):
    labels = " ".join(
        str(x.get("name", "")) + " " + str(x.get("slug", ""))
        for x in categories if isinstance(x, dict)
    ).lower()
    if any(x in labels for x in ("hamper", "gift set", "basket")):
        return "Gift Hampers"
    if any(x in labels for x in ("maltese wine", "malta wine", "local wine")):
        return "Maltese Wines"
    if any(x in labels for x in ("foreign wine", "sparkling wine", "dessert wine", "fortified wine", "wine")):
        return "Foreign Wines"
    if any(x in labels for x in ("beer", "cider")):
        return "Beer & Cider"
    if any(x in labels for x in ("liqueur", "spirit", "whisk", "vodka", "gin", "rum", "grappa", "cognac")):
        return "Spirits"
    if any(x in labels for x in ("gourmet", "chocolate", "food")):
        return "Gourmet"
    return "Other"


def _money(product):
    prices = product.get("prices") or {}
    raw = prices.get("price")
    currency = prices.get("currency_code")
    try:
        precision = int(prices.get("currency_minor_unit", 2))
        if raw is None or currency != "EUR" or not (0 <= precision <= 3):
            return None
        result = Decimal(str(raw)) / (Decimal(10) ** precision)
        return result if result >= 0 else None
    except (TypeError, ValueError, InvalidOperation):
        return None


def _clean(value, limit=1200):
    return unescape(strip_html(str(value or ""))).strip()[:limit]


def _image_url(product):
    for image in product.get("images") or []:
        if not isinstance(image, dict):
            continue
        src = image.get("src", "")
        if src and _allowed_source_host(src):
            return src
    return None


def _summary(p):
    return {
        "woo_id": p["id"],
        "item_code": DEMO_PREFIX + str(p["id"]),
        "name": _clean(p.get("name"), 140),
        "group": _group(p.get("categories") or []),
        "price_eur": str(_money(p)) if _money(p) is not None else None,
        "image_available": bool(_image_url(p)),
        "type": p.get("type"),
    }


def preview_store_api(max_items=24):
    """Read-only inspection; does not change ERPNext data."""
    products = _get_products(max_items)
    return {
        "source": SOURCE,
        "fetched": len(products),
        "importable_with_price": sum(_money(p) is not None for p in products),
        "with_source_image": sum(bool(_image_url(p)) for p in products),
        "sample": [_summary(p) for p in products[:12]],
        "mutated": False,
    }


def _ensure_groups_and_price_list():
    if not frappe.db.exists("Item Group", "All Item Groups"):
        frappe.throw("Complete ERPNext setup first.")
    for name, parent, is_group in GROUPS:
        if not frappe.db.exists("Item Group", name):
            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": name,
                "parent_item_group": parent,
                "is_group": is_group,
            }).insert(ignore_permissions=True)
    if not frappe.db.exists("Price List", PRICE_LIST):
        frappe.get_doc({
            "doctype": "Price List",
            "price_list_name": PRICE_LIST,
            "currency": "EUR",
            "enabled": 1,
            "selling": 1,
        }).insert(ignore_permissions=True)


def _get_image_bytes(url):
    """Fetch at most 4MB of published media; never follow URL redirects."""
    if not _allowed_source_host(url):
        raise ValueError("Image is not on the approved Master Cellar host")
    current_url = url
    for hop in range(3):
        response = requests.get(
            current_url, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT,
            stream=True, allow_redirects=False
        )
        if response.status_code not in (301, 302, 307, 308):
            break
        redirected = urljoin(current_url, response.headers.get("Location", ""))
        response.close()
        if not _allowed_source_host(redirected) or hop == 2:
            raise ValueError("Image redirect outside allowed source or too many hops")
        current_url = redirected
    with response:
        response.raise_for_status()
        kind = response.headers.get("content-type", "").split(";")[0].lower()
        if kind not in ("image/jpeg", "image/png", "image/webp"):
            raise ValueError("Unsupported image media type: " + kind)
        payload = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            payload.extend(chunk)
            if len(payload) > IMAGE_LIMIT_BYTES:
                raise ValueError("Image exceeds 4 MB limit")
    # The PIL decoder establishes this is really an image and not HTML.
    from PIL import Image
    im = Image.open(BytesIO(payload))
    im.verify()
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[kind]
    return bytes(payload), ext


def import_store_api(max_items=24, include_images=True):
    """Import new demonstration Items from the public WooCommerce Store API."""
    _ensure_demo_site()
    products = _get_products(max_items)  # network preflight before any writes
    return _import_products(products, include_images=include_images, source="Store API")


def _ensure_demo_site():
    if frappe.local.site != "mastercellar.kodetrek.com":
        frappe.throw("Import is restricted to the designated Master Cellar demo site.")


def _import_products(products, include_images=True, source="Store API"):
    _ensure_demo_site()
    _ensure_groups_and_price_list()
    unit = next((u for u in ("Nos", "Unit") if frappe.db.exists("UOM", u)), None)
    if not unit:
        frappe.throw("No suitable Unit/Nos UOM is configured.")

    counts = {"fetched": len(products), "created": 0, "skipped_existing": 0,
              "skipped_no_price": 0, "images_saved": 0, "image_errors": [],
              "record_errors": [], "price_list": PRICE_LIST}

    for product in products:
        code = DEMO_PREFIX + str(product["id"])
        if frappe.db.exists("Item", code):
            counts["skipped_existing"] += 1
            continue
        price = _money(product)
        if price is None:
            counts["skipped_no_price"] += 1
            continue

        savepoint = "woo_product_" + str(product["id"])
        frappe.db.savepoint(savepoint)
        try:
            name = _clean(product.get("name"), 140)
            if not name:
                raise ValueError("Product has no name")
            desc = _clean(product.get("description") or product.get("short_description"))
            frappe.get_doc({
                "doctype": "Item",
                "item_code": code,
                "item_name": name,
                "item_group": _group(product.get("categories") or []),
                "stock_uom": unit,
                "description": desc or name,
                "is_stock_item": 1,
                "is_sales_item": 1,
                "disabled": 0,
            }).insert(ignore_permissions=True)

            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": code,
                "price_list": PRICE_LIST,
                "selling": 1,
                "currency": "EUR",
                "price_list_rate": float(price),
                "note": f"Demo reference from WooCommerce {source}; verify displayed VAT and selling tax template.",
            }).insert(ignore_permissions=True)

            counts["created"] += 1
            if include_images:
                url = _image_url(product)
                if url:
                    try:
                        binary, ext = _get_image_bytes(url)
                        file = save_file(
                            f"mastercellar-woo-{product['id']}.{ext}", binary,
                            "Item", code, is_private=0, df="image"
                        )
                        frappe.db.set_value("Item", code, "image", file.file_url, update_modified=False)
                        counts["images_saved"] += 1
                    except Exception as exc:
                        counts["image_errors"].append({"code": code, "error": str(exc)[:180]})
            sleep(0.15)
        except Exception as exc:
            frappe.db.rollback(save_point=savepoint)
            counts["record_errors"].append({"code": code, "error": str(exc)[:180]})

    frappe.db.commit()
    return counts


def _read_woocommerce_csv(file_name, max_items=MAX_PRODUCTS):
    """Read an admin-exported WooCommerce product CSV from this site's private/files.

    Only a simple basename is accepted. This is useful when the public Store API
    is disabled. No customer or transaction exports are imported.
    """
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.csv", file_name or ""):
        raise ValueError("Supply a CSV basename such as woo-products.csv, not a path")
    path = Path(frappe.get_site_path("private", "files", file_name))
    if not path.is_file():
        raise FileNotFoundError(f"Upload the WooCommerce product export to {path}")
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("WooCommerce product CSV is larger than 10 MB")
    products = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        for row in rows:
            if len(products) >= min(max(int(max_items), 1), MAX_PRODUCTS):
                break
            if str(row.get("Type", "")).strip().lower() != "simple":
                continue
            if str(row.get("Published", "1")).strip() not in ("1", "yes", "true"):
                continue
            if str(row.get("Visibility in catalog", "visible")).strip().lower() == "hidden":
                continue
            try:
                product_id = int(row["ID"])
                raw = (row.get("Sale price") or row.get("Regular price") or "").strip()
                amount = Decimal(raw)
                if amount < 0:
                    continue
                minor = int(amount * 100)
            except (ValueError, TypeError, KeyError, InvalidOperation):
                continue
            categories = [
                {"name": x.strip().split(">")[-1].strip()}
                for x in (row.get("Categories") or "").split(",")
                if x.strip()
            ]
            images = [
                {"src": x.strip()}
                for x in (row.get("Images") or "").split(",")
                if x.strip()
            ]
            products.append({
                "id": product_id,
                "type": "simple",
                "name": row.get("Name", ""),
                "description": row.get("Description", "") or row.get("Short description", ""),
                "categories": categories,
                "prices": {
                    "price": str(minor), "currency_minor_unit": 2, "currency_code": "EUR"
                },
                "images": images,
            })
    return products


def preview_csv(file_name="woo-products.csv", max_items=24):
    """Preview a WooCommerce administrator CSV export with no database writes."""
    products = _read_woocommerce_csv(file_name, max_items=max_items)
    return {
        "source": "private WooCommerce product CSV",
        "file_name": file_name,
        "fetched": len(products),
        "with_source_image": sum(bool(_image_url(p)) for p in products),
        "sample": [_summary(p) for p in products[:12]],
        "mutated": False,
    }


def import_csv(file_name="woo-products.csv", max_items=24, include_images=True):
    """Explicit, opt-in import of a WooCommerce product CSV, with source images."""
    _ensure_demo_site()
    products = _read_woocommerce_csv(file_name, max_items=max_items)
    return _import_products(products, include_images=include_images, source="CSV export")
