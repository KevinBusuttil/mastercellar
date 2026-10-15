/* Reference-matched visual demo. No fetch, order API, email or payment call. */
(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('tmc-reference-data').textContent);
  const main = document.getElementById('tmc-main');
  const root = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  const key = 'mastercellar-reference-basket-v1';
  const products = new Map(data.products.map(p => [p.code, p]));
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const eur = cents => cents == null ? 'Price on request' : '€' + (cents / 100).toLocaleString('en-MT', {minimumFractionDigits:2,maximumFractionDigits:2});
  const link = (view='home', extras={}) => root + '?' + new URLSearchParams({view, ...extras}).toString();
  const photo = p => p.image ? `<img src="${esc(p.image)}" alt="${esc(p.name)}" loading="lazy">` : '<span class="tmc-no-image">Photograph not available</span>';
  const price = p => `<span class="tmc-price">${eur(p.cents)}${p.cents == null ? '' : ' <small>Incl. Vat*</small>'}</span>`;
  const productLink = p => link('product', {item:p.code});
  const note = '<p class="tmc-demo-note">* Reference retail display. VAT, delivery and stock are not calculated by this visual demo. No live orders or payments.</p>';
  let cart = {};
  try { cart = JSON.parse(sessionStorage.getItem(key) || '{}'); } catch (_) { cart = {}; }
  if (!cart || typeof cart !== 'object' || Array.isArray(cart)) cart = {};
  for (const code of Object.keys(cart)) {
    if (!products.has(code) || !Number.isInteger(cart[code]) || cart[code] < 1 || cart[code] > 99) delete cart[code];
  }
  const rows = () => Object.entries(cart).map(([code,qty]) => ({p:products.get(code),qty}));
  const total = () => rows().reduce((sum,{p,qty}) => sum + (p.cents || 0) * qty, 0);
  function toast(message) {
    const el = document.getElementById('tmc-toast');
    el.textContent = message; el.hidden = false;
    clearTimeout(toast.timer); toast.timer = setTimeout(() => { el.hidden = true; }, 6000);
  }
  function save() {
    try { sessionStorage.setItem(key, JSON.stringify(cart)); } catch (_) { toast('Browser storage unavailable. The basket is retained only on this page.'); }
    document.getElementById('tmc-basket-count').textContent = Object.values(cart).reduce((a,b) => a+b,0);
  }
  function card(p) {
    return `<article class="tmc-product-card"><div class="tmc-photo"><a href="${productLink(p)}">${photo(p)}</a><button type="button" class="tmc-add-small" data-add="${esc(p.code)}" aria-label="Add ${esc(p.name)} to demo basket" ${p.cents == null?'disabled':''}>+</button></div><h3><a href="${productLink(p)}">${esc(p.name)}</a></h3>${price(p)}</article>`;
  }
  const breadcrumb = text => `<nav class="tmc-breadcrumb" aria-label="Breadcrumb"><a href="${link()}">Home</a><span>›</span>${esc(text)}</nav>`;
  function newsletter() {
    return `<section class="tmc-newsletter"><div><div><h3>Subscribe to our newsletter</h3><p>For exclusive offers!</p></div><form data-preview><input type="email" aria-label="Email address — preview only" placeholder="Email Address" readonly><button class="tmc-button gold" type="submit">Subscribe</button></form></div></section>`;
  }
  function home() {
    const featured = data.products.filter(p => p.featured).slice(0,6);
    const brand = data.brand;
    main.innerHTML = `<section class="tmc-home-hero"><div class="tmc-hero-text"><h1>Wine Tasting:<br>An Evening<br>With Catena</h1><a class="tmc-text-link" href="${link('catalogue',{category:'Events'})}">Book tickets now ⟶</a><p class="tmc-demo-note">Event page preview · No reservations</p></div><img src="${esc(brand.hero)}" alt="An Evening With Catena — original reference banner artwork"></section>
    <section class="tmc-container tmc-welcome"><div class="tmc-welcome-top"><div><p class="tmc-kicker">Welcome to</p><h2>The Master Cellar</h2><p class="tmc-dropcap">We have been established since 1999, and are strategically positioned in Naxxar and Gzira. We pride ourselves in our understanding of our client’s specific needs and provide a constantly updated range of products to enhance the customers shopping experience.</p><p>The Master Cellar is a shop which offers a vast range of fine local and imported wine, whisky, spirits as well as gourmet items, cigars and non-alcoholic beverages. Each category provides the client with a varied range not only in brands but also price.</p></div><img src="${esc(brand.outside)}" alt="The Master Cellar shopfront"></div><div class="tmc-welcome-bottom"><img src="${esc(brand.inside)}" alt="Inside The Master Cellar"><div><p>The customer’s satisfaction is always taken into consideration and that is why we offer a specialised service, whereby we help you accommodate all their needs.</p><p>Have a look through our e-commerce shop and should you not be able to find what you are after, <a href="${link('info',{section:'contact'})}">get in touch with us</a>.</p></div></div></section>
    <section class="tmc-hamper-banner"><div class="tmc-container tmc-hamper-inner"><div><p class="tmc-kicker">Bespoke hampers</p><h2>Build your own hamper</h2><p>Choose from our wide range of products and build a custom hamper</p><a class="tmc-button gold" href="${link('hamper')}">Create your own hamper</a></div><img src="${esc(brand.hamper)}" alt="Wine and gourmet gift collection"></div></section>
    <section class="tmc-featured" id="tmc-featured"><div class="tmc-container"><p class="tmc-kicker">Our picks</p><h2>Featured</h2><div class="tmc-product-grid">${featured.map(card).join('')}</div><a class="tmc-text-link" href="${link('catalogue')}">See the full collection ⟶</a></div></section>${newsletter()}`;
    if (brand.barrels) document.getElementById('tmc-featured').style.backgroundImage = `linear-gradient(#0004,#0009),url("${brand.barrels}")`;
  }
  function catalogue() {
    const category = data.categories.includes(params.get('category')) ? params.get('category') : '';
    const q = (params.get('q') || '').trim().slice(0,80);
    const order = params.get('sort') || 'default';
    const minRaw = params.get('min'), maxRaw = params.get('max');
    const min = minRaw !== null && minRaw !== '' && Number.isFinite(Number(minRaw)) ? Math.max(0,Number(minRaw))*100 : 0;
    const max = maxRaw !== null && maxRaw !== '' && Number.isFinite(Number(maxRaw)) ? Math.max(0,Number(maxRaw))*100 : Infinity;
    let selection = data.products.filter(p => (!category || p.categories.includes(category)) && (!q || p.name.toLocaleLowerCase().includes(q.toLocaleLowerCase())) && (p.cents == null ? min===0 && max===Infinity : p.cents >= min && p.cents <= max));
    if (order === 'price') selection.sort((a,b) => (a.cents??Infinity)-(b.cents??Infinity));
    if (order === 'price-desc') selection.sort((a,b) => (b.cents??-1)-(a.cents??-1));
    if (order === 'name') selection.sort((a,b) => a.name.localeCompare(b.name));
    const pages = Math.max(1, Math.ceil(selection.length/18));
    const page = Math.min(pages, Math.max(1, parseInt(params.get('page') || '1',10)||1));
    const visible = selection.slice((page-1)*18,page*18);
    const options = {'default':'Default sorting','name':'Sort by name','price':'Sort by price: low to high','price-desc':'Sort by price: high to low'};
    const hidden = `<input type="hidden" name="view" value="catalogue"><input type="hidden" name="category" value="${esc(category)}">`;
    const pageURL = n => {const p=new URLSearchParams(params);p.set('view','catalogue');p.set('page',n);return root+'?'+p;};
    main.innerHTML = `<div class="tmc-container">${breadcrumb(category || 'Our Selection')}<div class="tmc-shop"><aside class="tmc-sidebar"><details open><summary>Items</summary><nav><a class="${category?'':'selected'}" href="${link('catalogue')}">All demo products</a>${data.categories.map(c=>`<a class="${c===category?'selected':''}" href="${link('catalogue',{category:c})}">${esc(c)}</a>`).join('')}</nav></details>
    ${category==='Foreign Wines'?'<details><summary>Wine country</summary><p>The source country attributes have not been imported. Country filtering is not enabled in this preview.</p></details>':''}${category.includes('Wine')?'<details><summary>Grape variety</summary><p>Grape attributes have not been imported. These controls show the reference layout only.</p></details>':''}
    <details ${min || max!==Infinity?'open':''}><summary>Filter by price</summary><form class="tmc-price-filter" method="get">${hidden}<input type="hidden" name="q" value="${esc(q)}"><label>From €<input type="number" name="min" min="0" step="0.01" value="${esc(min?min/100:'')}"></label><label>To €<input type="number" name="max" min="0" step="0.01" value="${esc(max!==Infinity?max/100:'')}"></label><button class="tmc-button" type="submit">Filter</button></form></details>
    <form class="tmc-compact-search" method="get">${hidden}<input type="search" name="q" maxlength="80" value="${esc(q)}" aria-label="Search products" placeholder="Search products…"><button type="submit" aria-label="Run search">⌕</button></form></aside>
    <section><h1>Our Selection</h1><div class="tmc-toolbar"><p>${selection.length?`Showing ${(page-1)*18+1}–${Math.min(page*18,selection.length)} of ${selection.length} demo results`:'No matching demo products'}</p><select id="tmc-sort" aria-label="Sort products">${Object.entries(options).map(([v,t])=>`<option value="${v}" ${v===order?'selected':''}>${t}</option>`).join('')}</select></div><div class="tmc-product-grid">${visible.map(card).join('')}</div>${visible.length?'':`<p class="tmc-empty">This category or selection has not been populated in the reference sample. <a href="${link('catalogue')}">Browse all imported reference products.</a></p>`}<nav class="tmc-pagination" aria-label="Catalogue pages">${Array.from({length:pages},(_,i)=>`<a href="${esc(pageURL(i+1))}" ${page===i+1?'aria-current="page" class="current"':''}>${i+1}</a>`).join('')}</nav>${note}</section></div></div>`;
    document.getElementById('tmc-sort').addEventListener('change',e=>{const p=new URLSearchParams(params);p.set('sort',e.target.value);p.set('view','catalogue');p.delete('page');window.location.href=root+'?'+p;});
  }
  function detail() {
    const p = products.get(params.get('item'));
    if (!p) {main.innerHTML=`<div class="tmc-container tmc-info-page"><h1>Product not found</h1><a href="${link('catalogue')}">Return to the collection</a></div>`;return;}
    const description = p.description && p.description !== p.name ? `<p>${esc(p.description)}</p>` : '';
    const related = data.products.filter(x => x.code!==p.code && x.categories.some(c=>p.categories.includes(c))).slice(-3);
    main.innerHTML=`<div class="tmc-container">${breadcrumb(p.categories[0]+'  ›  '+p.name)}<section class="tmc-detail"><div>${p.image?`<img class="tmc-detail-image" src="${esc(p.image)}" alt="${esc(p.name)}">`:photo(p)}</div><div><h1>${esc(p.name)}</h1>${description}<p class="tmc-demo-note">Loyalty accrual and live stock checks are not enabled in this demonstration.</p><div class="tmc-product-actions"><input id="tmc-product-qty" type="number" value="1" min="1" max="99" step="1" aria-label="Quantity"><button class="tmc-button" type="button" data-add="${esc(p.code)}" ${p.cents==null?'disabled':''}>Add to cart</button>${price(p)}</div>${note}</div></section></div><section class="tmc-related"><div class="tmc-container"><p class="tmc-kicker">It’s about style</p><h2>You Might Also Like</h2><div class="tmc-product-grid">${related.map(card).join('')}</div></div></section>${newsletter()}`;
  }
  function totals() {
    return `<table class="tmc-totals"><tbody><tr><th>Subtotal</th><td>${eur(total())}</td></tr><tr><th>Shipment</th><td>Not calculated in this preview.</td></tr><tr><th>Total</th><td>${eur(total())}</td></tr></tbody></table>`;
  }
  function basket() {
    const items=rows();
    if(!items.length){main.innerHTML=`<div class="tmc-container tmc-basket-page"><p>Your cart is currently empty.</p><a class="tmc-button" href="${link('catalogue')}">Return to shop</a>${note}</div>`;return;}
    main.innerHTML=`<div class="tmc-container tmc-basket-page"><h1>Cart</h1><p class="tmc-demo-note">Preview basket only. Products and reference prices come from ERPNext. No order has been created.</p><table class="tmc-basket-table"><thead><tr><th aria-label="Remove"></th><th aria-label="Image"></th><th>Product</th><th>Price</th><th>Quantity</th><th>Subtotal</th></tr></thead><tbody>${items.map(({p,qty})=>`<tr><td><button type="button" class="tmc-remove" data-remove="${esc(p.code)}" aria-label="Remove ${esc(p.name)}">×</button></td><td>${photo(p)}</td><td><a href="${productLink(p)}">${esc(p.name)}</a></td><td>${eur(p.cents)}</td><td><input type="number" min="1" max="99" step="1" value="${qty}" data-qty="${esc(p.code)}" aria-label="Quantity for ${esc(p.name)}"></td><td>${eur((p.cents||0)*qty)}</td></tr>`).join('')}</tbody></table><form data-preview class="tmc-compact-search"><input placeholder="Coupon code — preview only" aria-label="Coupon preview" readonly><button type="submit">Apply coupon</button></form><div class="tmc-basket-bottom"><section><h2>Personalised Message</h2><textarea placeholder="Gift-message field shown for layout reference only." aria-label="Gift message preview" readonly></textarea><p class="tmc-demo-note">Gift messages and packaging recommendations are not processed by this demo.</p></section><section><h2>Cart totals</h2>${totals()}<a class="tmc-button" href="${link('checkout')}">Proceed to checkout</a>${note}</section></div></div>`;
  }
  function checkout() {
    main.innerHTML=`<div class="tmc-container tmc-basket-page"><h1>Checkout</h1><p class="tmc-demo-note">Visual preview only. Fields are disabled; do not enter customer or card details. No information is sent.</p><div class="tmc-checkout-grid"><section><h3>Billing details</h3><div class="tmc-checkout-fields">${['First name','Last name','Company name (optional)','Country / Region','Street address','Town / City','Postcode','Phone','Email address'].map((label,i)=>`<label class="${i>1?'full':''}">${label}<input disabled placeholder="${label==='Country / Region'?'Malta':'Demonstration only'}"></label>`).join('')}</div><h3 style="margin-top:40px">Additional information</h3><textarea disabled aria-label="Order notes preview" placeholder="Order notes (optional)"></textarea></section><section><h3>Your order</h3><table class="tmc-totals"><thead><tr><th>Product</th><th>Subtotal</th></tr></thead><tbody>${rows().map(({p,qty})=>`<tr><td>${esc(p.name)} × ${qty}</td><td>${eur((p.cents||0)*qty)}</td></tr>`).join('')}</tbody></table>${totals()}<h3>Card payment</h3><p class="tmc-demo-note">Payment integration is not enabled. No card fields, payment gateway, order API or outbound email is connected.</p><button type="button" class="tmc-button" disabled>Place order — demo only</button><p style="margin-top:20px"><a href="${link('cart')}">← Return to cart</a></p></section></div></div>`;
  }
  function info() {
    const section=params.get('section')||'about';
    const content={about:['About The Master Cellar',"Established since 1999, with shops in Naxxar and Gzira. This reference-matched demonstration presents the retail collection through ERPNext instead of WooCommerce."],contact:['Contact Us','The Master Cellar — Oratory Street, Naxxar, and Sliema Road, Gzira. The contact form is not connected in this demonstration. No messages will be sent.'],club:['The Master Cellar Club','Club membership, loyalty points and subscriber features are planned integration work. This page is a visual navigation preview; it does not sign up customers or award points.'],privacy:['Privacy Policy — Demo','This site is a presentation prototype. Do not enter personal, account or payment details. The basket stores only product codes and quantities in this browser tab’s session storage. This is not the production privacy policy.'],delivery:['Delivery Policy — Demo','Live delivery charges, availability, time slots and collection rules have not been integrated. This preview makes no delivery commitment.'],terms:['Terms and Conditions — Demo','No purchases can be completed on this demonstration site. Product prices are reference values captured on 15 October 2026 and maintained in the isolated ERPNext demo. Production commercial terms are not implemented.']}[section]||['Page not included','This information page is outside the implemented demonstration scope.'];
    main.innerHTML=`<section class="tmc-container tmc-info-page"><h1>${esc(content[0])}</h1><p>${esc(content[1])}</p><a class="tmc-button" href="${link('catalogue')}">Explore the collection</a></section>`;
  }
  function hamper() {
    main.innerHTML=`<section class="tmc-container tmc-info-page"><p class="tmc-kicker">Bespoke hampers</p><h1>Create your own hamper</h1><p>Choose your hamper size</p><div class="tmc-size-grid">${['Small','Medium','Large'].map(size=>`<div class="tmc-size-card"><h3>${size}</h3><p>Packaging selection</p><button type="button" class="tmc-button gold" data-preview-action>Select ${size.toLowerCase()}</button></div>`).join('')}</div><p class="tmc-demo-note">Builder layout preview only. Size limits, packaging, component stock and pricing rules are not connected.</p><a href="${link('catalogue',{category:'Wine Hampers'})}">Browse the imported gift collection →</a></section>`;
  }
  function setLinks() {
    document.querySelectorAll('[data-view]').forEach(a=>{const extras={};if(a.dataset.category)extras.category=a.dataset.category;if(a.dataset.section)extras.section=a.dataset.section;a.href=link(a.dataset.view,extras);});
    document.querySelectorAll('[data-brand]').forEach(img=>{const url=data.brand[img.dataset.brand];if(url)img.src=url;else img.hidden=true;});
  }
  document.getElementById('tmc-menu-categories').innerHTML=data.categories.map(c=>`<a href="${link('catalogue',{category:c})}">${esc(c)}</a>`).join('');
  if(data.brand.menu) document.getElementById('tmc-menu').style.backgroundImage=`url("${data.brand.menu}")`;
  for (const [button,dialog] of [['tmc-open-menu','tmc-menu'],['tmc-open-search','tmc-search-dialog']]) document.getElementById(button).addEventListener('click',()=>document.getElementById(dialog).showModal());
  document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
  document.addEventListener('click',e=>{
    const add=e.target.closest('[data-add]');
    if(add){const code=add.dataset.add,p=products.get(code);if(!p || p.cents==null)return;const input=document.getElementById('tmc-product-qty');const value=input?Number(input.value):1;if(!Number.isInteger(value)||value<1||value>99){toast('Choose a whole quantity between 1 and 99.');return;}cart[code]=Math.min(99,(cart[code]||0)+value);save();toast('Added to the demo basket. No order has been placed.');}
    const remove=e.target.closest('[data-remove]');if(remove){delete cart[remove.dataset.remove];save();basket();}
    if(e.target.closest('[data-preview-action]'))toast('Visual preview only. This integration is not enabled and nothing has been submitted.');
  });
  document.addEventListener('submit',e=>{if(e.target.matches('[data-preview]')){e.preventDefault();toast('Preview only. No coupon, email, subscription or message has been submitted.');}});
  document.addEventListener('change',e=>{if(e.target.matches('[data-qty]')){const qty=Number(e.target.value);if(!Number.isInteger(qty)||qty<1||qty>99){toast('Choose a whole quantity between 1 and 99.');setTimeout(basket,0);return;}cart[e.target.dataset.qty]=qty;save();setTimeout(basket,0);}});
  setLinks();save();
  if(!data.ready){main.innerHTML='<section class="tmc-setup"><h1>Reference presentation ready to install</h1><p>Upload the reference asset bundle as a private File, then run the documented preview and install commands. The existing demo remains available at /mastercellar.</p></section>';return;}
  const view=params.get('view')||'home';
  ({home,catalogue,product:detail,cart:basket,checkout,info,hamper}[view]||home)();
})();
