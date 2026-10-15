"""Opt-in, idempotent sample catalogue seeder. Never called during app installation."""

import frappe

PRICE_LIST = "Master Cellar Retail"
PRODUCTS = [
    ("TMC-W001", "Marsovin Cassar De Malte 0.75L", "Maltese Wines", 29.90),
    ("TMC-W002", "Villa Sparina Gavi di Gavi 0.75L", "Foreign Wines", 20.85),
    ("TMC-W003", "Speri Amarone Della Valpolicella 0.75L", "Foreign Wines", 56.95),
    ("TMC-W004", "1919 White 0.75L", "Maltese Wines", 17.90),
    ("TMC-S001", "Absolut Vodka 70cl", "Spirits", 15.95),
    ("TMC-B001", "TOBCo. Helles Can 330ml", "Beer & Cider", 3.40),
    ("TMC-H001", "100th Anniversary Gift Box", "Gift Hampers", 106.25),
]
GROUPS = (
    ("Master Cellar Products", "All Item Groups", 1),
    ("Maltese Wines", "Master Cellar Products", 0),
    ("Foreign Wines", "Master Cellar Products", 0),
    ("Spirits", "Master Cellar Products", 0),
    ("Beer & Cider", "Master Cellar Products", 0),
    ("Gift Hampers", "Master Cellar Products", 0),
    ("Gourmet", "Master Cellar Products", 0),
)


def seed():
    """Execute with: bench --site SITE execute mastercellar.setup_demo.seed.

    No company, stock levels, tax rows, permissions or website settings are changed.
    Existing Items/Prices are not overwritten.
    """
    if not frappe.db.exists("Item Group", "All Item Groups"):
        frappe.throw("Complete ERPNext setup before seeding Master Cellar demo products.")

    for name, parent, is_group in GROUPS:
        if not frappe.db.exists("Item Group", name):
            frappe.get_doc(
                {
                    "doctype": "Item Group",
                    "item_group_name": name,
                    "parent_item_group": parent,
                    "is_group": is_group,
                }
            ).insert(ignore_permissions=True)

    if not frappe.db.exists("Price List", PRICE_LIST):
        frappe.get_doc(
            {
                "doctype": "Price List",
                "price_list_name": PRICE_LIST,
                "currency": "EUR",
                "enabled": 1,
                "selling": 1,
            }
        ).insert(ignore_permissions=True)

    stock_uom = next((u for u in ("Nos", "Unit") if frappe.db.exists("UOM", u)), None)
    if not stock_uom:
        frappe.throw("Create a Nos or Unit UOM before seeding demo products.")

    created_items = created_prices = 0
    for code, label, group, rate in PRODUCTS:
        if not frappe.db.exists("Item", code):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": code,
                    "item_name": label,
                    "item_group": group,
                    "stock_uom": stock_uom,
                    "is_stock_item": 1,
                    "is_sales_item": 1,
                    "disabled": 0,
                }
            ).insert(ignore_permissions=True)
            created_items += 1

        if not frappe.db.exists(
            "Item Price", {"item_code": code, "price_list": PRICE_LIST, "selling": 1}
        ):
            frappe.get_doc(
                {
                    "doctype": "Item Price",
                    "item_code": code,
                    "price_list": PRICE_LIST,
                    "selling": 1,
                    "currency": "EUR",
                    "price_list_rate": rate,
                }
            ).insert(ignore_permissions=True)
            created_prices += 1

    frappe.db.commit()
    return {"created_items": created_items, "created_prices": created_prices, "site": frappe.local.site}
