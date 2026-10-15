# Master Cellar — ERPNext v16 demo portal

Frappe custom app for the Master Cellar Malta demonstration at **mastercellar.kodetrek.com**.

## Scope

- A bespoke, responsive storefront homepage, category browsing, and product-detail pages.
- Product data comes from ERPNext **Item**; displayed indicative prices come from **Item Price** in selling price list `Master Cellar Retail`.
- Only demonstration SKUs beginning with `TMC-` are exposed. Other ERPNext items are not displayed.
- A repeatable, non-destructive demo fixture seeds seven sample items, groups, and prices.
- **No checkout, online payments, delivery promises, real inventory, tax calculation, age verification or order creation is implemented here.** Those must be integrated, legally reviewed, and tested separately. This is an honest interactive storefront prototype.
- Does not depend on the separate Webshop or Payments app. Does not alter other sites.

## Requirements

- Frappe v16, ERPNext v16, Python 3.14 (matching Frappe v16).
- Existing bench and a **separate** site: `mastercellar.kodetrek.com`.
- Existing production sites must not be updated or migrated as part of this work.

## Deployment checklist — perform only after reviewing/merging the feature PR

1. Back up the new site and confirm the server's other sites are healthy:

   ```bash
   cd ~/frappe-bench
   bench --site mastercellar.kodetrek.com backup --with-files
   bench --site mastercellar.kodetrek.com list-apps
   ```

2. Review dependencies in the PR and plan any bench-level app installation for a safe window. Application code, asset linking, and dependency resolution are shared by all sites in the bench. When approved:

   ```bash
   cd ~/frappe-bench
   bench get-app --branch main https://github.com/KevinBusuttil/mastercellar.git
   bench --site mastercellar.kodetrek.com install-app mastercellar
   bench --site mastercellar.kodetrek.com list-apps
   ```

   Do **not** run `bench update` or `bench --site all migrate` for this demo.

3. In the new site's ERPNext Desk, complete the company setup wizard. The demo item seeder does not create a legal company or accounting settings.

4. Seed the optional catalogue in **this site only** (idempotent; will not rewrite existing prices):

   ```bash
   bench --site mastercellar.kodetrek.com execute mastercellar.setup_demo.seed
   ```

5. In **Website Settings** on the new site, set **Home Page** to `mastercellar`. For initial testing, browse `/mastercellar` directly to avoid altering site navigation prematurely.
6. Clear only this site's website caches:

   ```bash
   bench --site mastercellar.kodetrek.com clear-website-cache
   bench --site mastercellar.kodetrek.com clear-cache
   ```

7. Test:
   - `https://mastercellar.kodetrek.com/mastercellar`
   - `https://mastercellar.kodetrek.com/mastercellar/catalogue`
   - `https://mastercellar.kodetrek.com/mastercellar/product?item=TMC-W001`
   - Edit one **demo** Item Price and refresh the product page to verify ERPNext read-through.
   - Confirm no other ERPNext site has the app installed.

### Reversibility

Before changing Website Settings, record its previous home page value. To revert visible navigation, restore that value in the new site's Website Settings. Avoid uninstalling the app on the night before a client demo. No data or schema from other sites should be changed.

## Product-data model

This initial implementation reads:

- `Item`: code, name, group, image, disabled status, sales-item flag.
- `Item Price`: selling price list, rate, currency, validity dates.

It is deliberately **not** an authoritative commercial pricing engine. Before go-live, use ERPNext's full pricing/tax/stock APIs or the client's actual commercial-terms system, including customer-specific agreements, promotions and stock reservation.

### Future milestones

1. Agree product master source (AX/ERPNext), legal company, branch warehouses, tax rules and media licensing.
2. Establish age verification and delivery handoff controls for alcohol.
3. Integrate a tested commercial cart and checkout engine (Frappe Webshop only after v16 verification, or carefully designed custom APIs).
4. Sales Order, payment confirmation, picking/fulfilment, pickup, refunds, and reconciliation.
5. Corporate orders, curated hamper builder, events, membership and SEO migration.

All data and pricing in the seeder are **illustrative demonstration data**; they must be verified before any production use.


## Import real WooCommerce products and images for the client demonstration

**Do not import into production.** This process only targets the isolated
`mastercellar.kodetrek.com` site. The public product feed (if enabled) is
not a substitute for an authenticated migration covering customer accounts,
orders, stock, tax rules, coupon rules, variants and transaction history.

**Before downloading source photos, obtain permission from the client to reuse
their existing product photographs and branding on the demo.** Keep the demo
behind an access restriction or disable search indexing, and remove stale
data after the meeting.

### Option A — Public WooCommerce Store API (preferred for fast demo)

Before changing the database, SSH into the server and test:

```bash
cd ~/frappe-bench
curl -sSI --max-time 15 'https://www.themastercellar.com/wp-json/wc/store/v1/products?per_page=1'
bench --site mastercellar.kodetrek.com execute \
  mastercellar.woo_import.preview_store_api \
  --kwargs '{"max_items":12}'
```

The preview returns how many products and images the remote endpoint exposes
and a short sample, **without updating ERPNext**. If HTTP 403, 404 or HTML
appears, use Option B. Do not bypass access restrictions.

After reviewing the preview and taking an ERPNext site backup:

```bash
bench --site mastercellar.kodetrek.com backup --with-files
bench --site mastercellar.kodetrek.com execute \
  mastercellar.woo_import.import_store_api \
  --kwargs '{"max_items":36,"include_images":True}'
```

The `--kwargs` option in this Frappe v16 installation evaluates a Python
dictionary, not JSON. Use `True`, `False` and `None`, not JSON's lowercase
`true`, `false` and `null`. Do not quote a boolean as a string. A
`NameError: name 'true' is not defined` occurs while parsing arguments,
before the importer runs; retry with `True`, without reinstalling the app
or restoring the database. Only use trusted Python expressions in this option.
See the official reference:
https://docs.frappe.io/framework/user/en/bench/reference/execute

The import is opt-in, uses a fixed source hostname, limits redirects and
image sizes, and only creates new `TMC-WC-*` items. It never overwrites
existing ERPNext items or selling prices.

### Option B — WooCommerce product CSV export (when API blocked)

In **WordPress Admin → Products → All Products → Export**, export the published
simple products. This is the official WooCommerce product export route.
Transfer it to your *new Frappe site*, e.g.:

```bash
sites/mastercellar.kodetrek.com/private/files/woo-products.csv
```

Only the basename `woo-products.csv` is accepted by the importer; do not pass
absolute paths. This export may include links to product images; they are
downloaded only from the approved `themastercellar.com` host.

Preview first:

```bash
bench --site mastercellar.kodetrek.com execute \
  mastercellar.woo_import.preview_csv \
  --kwargs '{"file_name":"woo-products.csv","max_items":12}'
```

Then, only after reviewing the result:

```bash
bench --site mastercellar.kodetrek.com execute \
  mastercellar.woo_import.import_csv \
  --kwargs '{"file_name":"woo-products.csv","max_items":36,"include_images":True}'
```

Do not export/import actual customer or transaction data for the demo.

### Post-import checks

```bash
bench --site mastercellar.kodetrek.com clear-website-cache
bench --site mastercellar.kodetrek.com execute \
  mastercellar.catalog.get_demo_products
```

Browse `/mastercellar/catalogue` and verify product images resolve at local
`/files/...` URLs, product pages open and selected prices agree with the
original storefront.

Imported `Item Price` values are **reference/display values only**.
They are not evidence of correct ERPNext VAT treatment; Woo CSV and Store API
may have different tax display semantics. Do not enable real orders/payments
based on this import without tax and commercial-pricing reconciliation.

**Limitations:** Currently supports WooCommerce **simple products** only.
Variable products, subscriptions, gift-card balances, event registrations,
real inventory/warehouses and customer-specific prices require dedicated
integration. Existing `TMC-*` seeded demo products remain unchanged.
