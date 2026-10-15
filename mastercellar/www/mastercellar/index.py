from mastercellar.catalog import get_demo_products


def get_context(context):
    context.title = "The Master Cellar | Fine Wines & Gifts"
    context.full_width = True
    context.no_cache = True
    context.featured = get_demo_products(limit=8)[:4]
