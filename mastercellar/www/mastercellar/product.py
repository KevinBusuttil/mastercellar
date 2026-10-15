import frappe

from mastercellar.catalog import get_demo_product


def get_context(context):
    code = frappe.form_dict.get("item", "")
    product = get_demo_product(code)

    if not product:
        frappe.local.flags.redirect_location = "/404"
        raise frappe.Redirect

    context.title = product["item_name"] + " | The Master Cellar"
    context.full_width = True
    context.no_cache = True
    context.product = product
