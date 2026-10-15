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
