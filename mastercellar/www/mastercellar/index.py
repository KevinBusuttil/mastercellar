from mastercellar.catalog import get_demo_products


def get_context(context):
    context.title = "The Master Cellar | Fine Wines & Gifts"
    context.full_width = True
    context.no_cache = True
    products = get_demo_products(limit=80)
    context.featured = [p for p in products if p["image"]][:6] or products[:6]
