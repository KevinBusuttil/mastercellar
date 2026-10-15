import frappe

from mastercellar.catalog import CATEGORIES, get_demo_products


def get_context(context):
    category = frappe.form_dict.get("category")
    if category not in CATEGORIES:
        category = None

    context.title = f"{category or 'The Collection'} | The Master Cellar"
    context.full_width = True
    context.no_cache = True
    context.category = category
    context.categories = list(CATEGORIES)
    search = (frappe.form_dict.get("q") or "").strip()[:65]
    context.search = search
    context.products = get_demo_products(category=category, limit=80, search=search)
