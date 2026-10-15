# Screenshot-matched Master Cellar demo — 15 October 2026

## Isolation and scope

New optional route: `/mastercellar/replica`. Existing `/mastercellar`, catalogue,
product pages, Woo importer, company, production integrations and other sites
are unchanged. No Webshop, Payments, Builder or additional pip/npm packages.

Reference: user-supplied `MasterCellar_Rebuild_Reference(1).zip`: 32 desktop
screenshots, asset manifest, visible page text, images, and typography samples.
This implements the main retail presentation, not every captured page/state.

Working: reference header/footer, homepage, catalogue, category/search/price
filters, actual sample counts, sorting/pagination, product details, full-screen
menu/search, and tab-local preview basket with quantities/totals. Products and
current reference Item Prices are read from ERPNext. The price source remains
`Master Cellar Retail`, not a customer-specific commercial pricing engine.

Preview only: checkout (disabled fields/button), newsletter, coupons, loyalty,
hamper-size selectors and supplementary information pages. No customer/payment
information is requested or transmitted. No Sales Orders, payment requests,
emails, subscriptions, reservations or stock entries are created.
Country/grape attributes are not in this dataset; those controls explicitly
say they are unavailable. Reference counts, not the source shop's full counts,
are displayed. No claims of production tax/stock/payment correctness.

## Assets and reference sample

The separately supplied `mastercellar-reference-assets.zip` contains 59 product
records and 69 image/logo files; it contains no executable code or font files.
13 Maltese product photos and 2 decorative assets are screenshot crops where
source originals were unavailable. Other product images and logos are supplied
originals. The background strip is a visual approximation, not the full original
barrel photograph. Fonts are requested from Google Fonts (Lora, Nunito Sans,
Playfair Display), with system fallbacks when unavailable. Mobile adaptation
is implemented, but mobile fidelity to the original cannot be verified because
there are no original mobile screenshots.

The bundle creates separate `TMC-REF-*` non-stock demo Items under Item Group
`Master Cellar Reference`. These are reference records, not a second live product
migration. Existing `TMC-*` and `TMC-WC-*` items are not overwritten or deleted.
The new route shows only its reference set, avoiding the old placeholder items.
Re-running the installer preserves existing reference Item/Item Price edits.
Media is public for rendering; the source ZIP and presentation manifest remain
private. The installer is CLI-only and restricted to `mastercellar.kodetrek.com`.

## Deployment

1. From the existing app, pull the feature branch. Stop on a conflict.

   ```bash
   cd ~/frappe-bench/apps/mastercellar
   git status --short
   git pull --ff-only upstream feat/erpnext-v16-demo-storefront
   python3 -m unittest discover -s tests -p 'test_reference.py' -v
   cd ~/frappe-bench
   ./env/bin/python -m py_compile apps/mastercellar/mastercellar/reference.py
   node --check apps/mastercellar/mastercellar/public/js/reference.js
   bench --site mastercellar.kodetrek.com backup --with-files
   ```

2. Download the supplied asset ZIP, then log in to this site's ERPNext Desk.
   Search for **File**, select **New / Upload**, and upload the ZIP with
   **Is Private** enabled. Keep the name `mastercellar-reference-assets.zip`.
   It should be stored in `sites/mastercellar.kodetrek.com/private/files/`.
   An SSH/SFTP upload to that location works as well. No ZIP extraction by hand.

3. Validate first. No changes are made by the default dry run.

   ```bash
   bench --site mastercellar.kodetrek.com execute mastercellar.reference.install_bundle
   ```

   Expected: `dry_run: true`, `reference_products: 59`, `media_files: 69`.
   If Frappe renamed the uploaded ZIP, use its actual basename with
   `--kwargs '{"file_name":"actual-name.zip"}'`. Do not pass a full path.

4. After reviewing the preview, opt in to the isolated reference import:

   ```bash
   bench --site mastercellar.kodetrek.com execute \
     mastercellar.reference.install_bundle --kwargs '{"dry_run":False}'
   bench --site mastercellar.kodetrek.com execute mastercellar.reference.health_check
   bench --site mastercellar.kodetrek.com clear-cache
   bench --site mastercellar.kodetrek.com clear-website-cache
   ```

   Bench kwargs use Python `True` / `False`, not JSON booleans. With a renamed
   ZIP include both `file_name` and `dry_run` in the same dictionary.

5. At a safe moment restart only the already identified web service:

   ```bash
   sudo supervisorctl restart frappe-bench-web:frappe-bench-frappe-web
   ```

   This briefly affects the other sites sharing that web process. Do not restart
   nginx, MariaDB, Redis, unrelated benches or active background workers.
   Existing static asset links serve the new CSS/JS; no asset compilation,
   migration, app reinstall or bench update is needed for these additions.

6. Open `https://mastercellar.kodetrek.com/mastercellar/replica`.
   Catalogue: append `?view=catalogue&category=Maltese+Wines`.
   Product links lead to `?view=product&item=TMC-REF-...`.
   Basket and checkout are `?view=cart` and `?view=checkout`.

Only after accepting it, change **Website Settings → Home Page** to
`mastercellar/replica`. Record the old value first. This is optional.
Returning to the existing `/mastercellar` page provides the previous demo.
Do not uninstall the app or restore the whole database to revert presentation.

## Verification performed before delivery

23 offline Python tests passed, covering bundle validation, scope restrictions,
price/JSON handling, SVG/path protections, preview mode and mocked idempotent
installation. The actual 59-product media ZIP also passed the installer dry run.
Python compilation and JavaScript syntax checks passed.

Offline Chromium rendering checked desktop (1363px) and mobile (390px), using
the supplied images and reference font faces. Catalogue, product, basket quantity
updates, checkout-disabled state, search, price filtering and dialog controls
were exercised. No page-script errors, missing visible images or horizontal
overflow in the checked catalogue view. These use a local data/ERPNext-base-template
stand-in and do **not** constitute a live ERPNext installation or browser test
against DigitalOcean. Verify the actual site after deployment.

Before production: media/licensing review, SEO/migration redirects, accessibility,
real age/ID policy, guest/customer identity, VAT/shipping, stock reservation,
commercial pricing, payment/webhooks, idempotency, refunds, orders, emails and
privacy/security review. `noindex` is included but is not access control; restrict
access separately for a confidential client demonstration.
