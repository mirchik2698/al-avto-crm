const state={view:'tires',user:null,tab:'orders',selected:null,importRows:[],branches:[]};
const money=v=>new Intl.NumberFormat('ru-RU').format(Number(v||0));
const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
async function api(path,options={}){
  const headers=options.body instanceof FormData?{}:{'Content-Type':'application/json'};
  if(state.user?.token)headers.Authorization=`Bearer ${state.user.token}`;
  const r=await fetch(`/api${path}`,{...options,headers:{...headers,...options.headers}});
  if(r.status===204)return null;const data=await r.json().catch(()=>({}));
  if (!r.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(issue => issue.msg.replace(/^Value error, /, '')).join('. ') : data.detail;
    throw Error(detail || 'Не удалось выполнить запрос.');
  }
  return data;
}
function message(text,type='error'){const el=document.getElementById('appMessage');el.textContent=text;el.className=`app-message ${type}`;setTimeout(()=>el.className='app-message',5000)}
const schemas={
 tires:{title:'Шины',kicker:'Каталог шин',primary:[['Ширина','width',['—', ...Array.from({length:20}, (_, index) => String(155 + index * 10))]],['Профиль','profile',['—','25','30','35','40','45','50','55','60','65','70','75','80']],['Диаметр','diameter',['—','14','15','16','17','18','19','20','21','22']],['Сезон','season',['—','Лето','Зима']]],secondary:[]},
 wheels:{title:'Диски',kicker:'Каталог дисков',primary:[['Диаметр','diameter',['—','15','16','17','18','19']],['Разболтовка','bolt_pattern',['—','4×100','5×108','5×112','5×114.3','5×120']]],secondary:['wheel_width','center_bore_min','et']}
};
const showProducts = document.getElementById('showProducts');
const tirePreferences = document.getElementById('tirePreferences');
const tirePriceOrder = document.getElementById('tirePriceOrder');
const tirePairCard = document.getElementById('tirePairCard');
const includeTirePair = document.getElementById('includeTirePair');
const tirePairSize = document.getElementById('tirePairSize');
const tirePairs = new Map([
  ['225/35/20', ['255/30', '265/30']],
  ['235/30/20', ['265/25', '275/25', '285/25']],
  ['235/35/20', ['265/30', '275/30']],
  ['235/45/20', ['255/40', '265/40']],
  ['245/30/20', ['285/25', '295/25']],
  ['245/35/20', ['275/30', '285/30', '295/30']],
  ['245/40/20', ['275/35', '285/35']],
  ['245/45/20', ['275/40']],
  ['255/30/20', ['295/25', '305/25']],
  ['255/35/20', ['285/30', '295/30']],
  ['255/40/20', ['285/35', '295/35']],
  ['255/45/20', ['285/40']],
  ['265/30/20', ['305/25', '325/25']],
  ['265/35/20', ['295/30', '305/30']],
  ['265/40/20', ['295/35', '305/35']],
  ['265/45/20', ['295/40']],
  ['265/50/20', ['295/45']],
  ['275/35/20', ['305/30']],
  ['275/40/20', ['315/35']],
  ['275/45/20', ['305/40']],
  ['275/50/20', ['305/45']],
  ['295/35/20', ['335/30', '345/30']]
]);
let pairKey = '';

function tireSizeKey(params) {
  return ['width', 'profile', 'diameter'].map(name => params.get(name)).join('/');
}

function staggeredRearSizes(params) {
  if (!['18', '19', '20'].includes(params.get('diameter'))) return [];
  const front = params.get('width') + '/' + params.get('profile');
  const shared = tirePairs.get(front + '/20') || [];
  return tireSizeKey(params) === '245/45/18' ? ['265/40', ...shared] : shared;
}
tirePreferences.addEventListener('change', loadCatalog);
includeTirePair.addEventListener('change', loadCatalog);
function control([label, name, items], required = false) {
  const options = items.map((value, index) =>
    `<option value="${index ? esc(value) : ''}">${esc(['bolt_pattern', 'center_bore_min'].includes(name) ? value.replaceAll('.', ',') : value)}</option>`).join('');
  return `<div class="filter-control">
    <label for="filter-${name}">${label}</label>
    <select id="filter-${name}" name="${name}"${required ? ' required' : ''}>${options}</select>
  </div>`;
}

function sizeGridControl([label, name, items], required = true) {
  const choices = (required ? items.slice(1) : items).map((value, index) => `
    <label class="tire-season-choice">
      <input type="radio" name="${esc(name)}" value="${!required && index === 0 ? '' : esc(value)}"${required ? ' required' : ''}>
      <span>${esc(value.replaceAll('.', ','))}</span>
    </label>`).join('');
  return `<div class="filter-control tire-size-control tire-size-${name}">
    <span class="tire-size-label" id="tire-${name}-label">${esc(label)}${name === 'width' ? ', мм' : ''}</span>
    <details class="tire-size-picker" data-empty="${esc(items[0])}">
      <summary aria-labelledby="tire-${name}-label tire-${name}-value"><span id="tire-${name}-value">${esc(items[0])}</span></summary>
      <div class="tire-size-options" role="group" aria-labelledby="tire-${name}-label">${choices}</div>
    </details>
  </div>`;
}

function tireSeasonControl([label, name, items]) {
  const choices = items.slice(1).map(value => `
    <label class="tire-season-choice">
      <input type="radio" name="${esc(name)}" value="${esc(value)}" required>
      <span>${esc(value)}</span>
    </label>`).join('');
  return `<div class="tire-options">
    <fieldset class="tire-season">
      <legend>${esc(label)}</legend>
      <div class="tire-season-options">${choices}</div>
    </fieldset>
    <div class="tire-season-options tire-extra-options">
      <label class="tire-season-choice"><input type="checkbox" name="studded" value="Да"><span>Шип</span></label>
      <label class="tire-season-choice"><input type="checkbox" name="commercial" value="Да"><span>Коммерческие</span></label>
    </div>
  </div>`;
}

function updateFilterButton() {
  const minimumWidth = Number(filterForm.querySelector('[name=width_from]:checked')?.value);
  for (const option of filterForm.querySelectorAll('[name=width_to]')) {
    const belowMinimum = Boolean(option.value) && Number(option.value) < minimumWidth;
    option.closest('label').hidden = belowMinimum;
    option.disabled = belowMinimum;
    if (belowMinimum && option.checked) option.checked = false;
  }
  for (const picker of filterForm.querySelectorAll('.tire-size-picker')) {
    picker.querySelector('summary span').textContent = picker.querySelector('input:checked')?.value.replaceAll('.', ',') || picker.dataset.empty;
  }
  const params = query();
  const nextPairKey = state.view === 'tires' ? tireSizeKey(params) : '';
  const rearSizes = state.view === 'tires' ? staggeredRearSizes(params) : [];
  if (nextPairKey !== pairKey) includeTirePair.checked = false;
  pairKey = nextPairKey;
  tirePairCard.hidden = !rearSizes.length;
  tirePairSize.textContent = rearSizes.map(size => size + ' R' + params.get('diameter')).join(', ');
  showProducts.disabled = [...primaryFilters.querySelectorAll('[required]')].some(input => input.validity.valueMissing);
}

function renderFilters() {
  const schema = schemas[state.view];
  const tires = state.view === 'tires';
  catalogTitle.textContent = schema.title;
  tirePreferences.hidden = !tires;
  tirePreferences.querySelector('[name=min_stock]').disabled = !tires;
  filterForm.classList.toggle('tire-filters', tires);
  primaryFilters.classList.toggle('wheels', !tires);
  primaryFilters.innerHTML = schema.primary.map(field => {
    if (tires && field[1] !== 'season') return sizeGridControl(field);
    if (tires && field[1] === 'season') return tireSeasonControl(field);
    return control(field, tires);
  }).join('');
  if (tires) {
    primaryFilters.prepend(primaryFilters.querySelector('.tire-season'));
    primaryFilters.querySelector('.tire-extra-options').append(tirePairCard);
  }
  else wheelFit.attach(primaryFilters);
  secondaryFilters.closest('details').hidden = !schema.secondary.length;
  secondaryFilters.innerHTML = schema.secondary.map(field => {
    if (field === 'wheel_width') {
      const widths = ['Любая', ...Array.from({ length: 16 }, (_, index) => String(4.5 + index / 2))];
      return `<fieldset class="wheel-width-range">
        <legend class="range-label">Ширина диска, ″</legend>
        <div class="et-range">
          ${sizeGridControl(['От', 'width_from', widths], false)}
          ${sizeGridControl(['До', 'width_to', widths], false)}
        </div>
      </fieldset>`;
    }
    if (field === 'center_bore_min') return sizeGridControl(['ЦО от, мм', 'center_bore_min', ['Любое', ...wheelFit.centerBores()]], false);
    if (field === 'et') return '<div class="filter-control"><span class="range-label">Вылет ET, мм</span><div class="et-range"><input name="et_from" aria-label="Вылет от" placeholder="от" type="number" step="any"><input name="et_to" aria-label="Вылет до" placeholder="до" type="number" step="any"></div></div>';
    return control(field);
  }).join('');
  for (const sizePicker of filterForm.querySelectorAll('.tire-size-picker')) {
    const summary = sizePicker.querySelector('summary');
    function closePicker() {
      if (!sizePicker.open) return;
      summary.focus({ preventScroll: true });
      sizePicker.open = false;
    }
    sizePicker.addEventListener('change', () => setTimeout(closePicker, 0));
    sizePicker.addEventListener('keydown', event => {
      if (event.key === 'Escape' && sizePicker.open) {
        event.preventDefault();
        closePicker();
      }
    });
    sizePicker.addEventListener('focusout', event => {
      if (!sizePicker.contains(event.relatedTarget)) sizePicker.open = false;
    });
  }
  updateFilterButton();
}
function query(){const p=new URLSearchParams();for(const[k,raw]of new FormData(filterForm)){let v=String(raw).trim();if(k==='commercial')v=v==='Да'?'true':'';if(k==='studded')v=v==='Да'?'true':v==='Нет'?'false':'';if(v)p.set(k,v)}return p}
const catalogue = {products: [], page: 0, request: 0};
const pageSize = 9;
const pagination = document.getElementById('catalogPagination');
const previousPage = document.getElementById('previousCatalogPage');
const nextPage = document.getElementById('nextCatalogPage');
const pageStatus = document.getElementById('catalogPageStatus');
let wheelPhotos;

let catalogSource = '';
const catalogSourceGroups = document.querySelectorAll('.catalog-sources');
for (const group of catalogSourceGroups) {
  group.addEventListener('click', event => {
    const button = event.target.closest('button[data-source]');
    if (!button || catalogSource === button.dataset.source) return;
    catalogSource = button.dataset.source;
    for (const option of document.querySelectorAll('.catalog-sources button')) {
      option.setAttribute('aria-pressed', String(option.dataset.source === catalogSource));
    }
    loadCatalog();
    if (group.nextElementSibling === pagination) catalogSourceGroups[0].scrollIntoView({block:'start'});
  });
}

async function loadCatalog() {
  const request = ++catalogue.request;
  const view = state.view;
  const cheapestFirst = view === 'tires' && tirePriceOrder.checked;
  pagination.hidden = true;
  resultCount.textContent = '';
  productGrid.innerHTML = '<p class="empty-state">Загружаем товары…</p>';
  try {
    const photos = view === 'wheels'
      ? (wheelPhotos ||= fetch('/assets/wheel-photos/index.json').then(r => r.ok ? r.json() : {}).catch(() => ({})))
      : {};
    const params = query();
    if (catalogSource) params.set('source', catalogSource);
    const rearSizes = view === 'tires' && includeTirePair.checked ? staggeredRearSizes(params) : [];
    const requests = [api(`/catalog/${view}?${params}`)];
    for (const size of rearSizes) {
      const other = new URLSearchParams(params);
      const [width, profile] = size.split('/');
      other.set('width', width);
      other.set('profile', profile);
      requests.push(api(`/catalog/tires?${other}`));
    }
    const [lists, manifest] = await Promise.all([Promise.all(requests), photos]);
    let products = lists.flat();
    if (view === 'wheels') {
      const min = Number(params.get('width_from') || -Infinity);
      const max = Number(params.get('width_to') || Infinity);
      const bore = Number(params.get('center_bore_min') || -Infinity);
      products = products.filter(({wheel}) =>
        wheel.width >= min && wheel.width <= max && wheel.center_bore >= bore);
    }
    if (request !== catalogue.request) return;
    catalogue.products = products.map(product => {
      const photo = manifest[product.id];
      return photo?.model === product.model && !product.image_url
        ? {...product, image_url: photo.url}
        : product;
    }).sort((left, right) => cheapestFirst
      ? Number(left.price) - Number(right.price)
      : Number(Boolean(right.image_url)) - Number(Boolean(left.image_url)));
    catalogue.page = 0;
    resultCount.textContent = `Найдено: ${products.length}`;
    renderCatalogPage();
  } catch (error) {
    if (request === catalogue.request) {
      productGrid.innerHTML = `<p class="empty-state">${esc(error.message)} Проверьте доступ к API.</p>`;
    }
  }
}

function renderCatalogPage() {
  const {products, page} = catalogue;
  const pageCount = Math.ceil(products.length / pageSize);
  renderProducts(products.slice(page * pageSize, (page + 1) * pageSize));
  pagination.hidden = pageCount < 2;
  previousPage.disabled = page === 0;
  nextPage.disabled = page + 1 >= pageCount;
  pageStatus.textContent = pageCount ? `Страница ${page + 1} из ${pageCount}` : '';
}

function changeCatalogPage(delta) {
  const target = catalogue.page + delta;
  if (target < 0 || target * pageSize >= catalogue.products.length) return;
  catalogue.page = target;
  renderCatalogPage();
  productGrid.scrollIntoView({block:'start'});
}
previousPage.onclick = () => changeCatalogPage(-1);
nextPage.onclick = () => changeCatalogPage(1);

const photoDialog = document.getElementById('photoDialog');
const photoFull = document.getElementById('photoFull');
const photoTitle = document.getElementById('photoTitle');
const photoStage = photoDialog.querySelector('.photo-stage');
let photoVersion = 0;
let enhancedPhotoUrl;

photoDialog.addEventListener('click', event => {
  if (event.target === photoDialog) photoDialog.close();
});
photoDialog.addEventListener('close', () => {
  if (photoDialog.open) return;
  photoVersion++;
  photoFull.removeAttribute('src');
  photoStage.style.removeProperty('--view-width');
  photoStage.style.removeProperty('--photo-ratio');
  photoStage.classList.remove('cover-supplier-mark');
  if (enhancedPhotoUrl) URL.revokeObjectURL(enhancedPhotoUrl);
  enhancedPhotoUrl = undefined;
});

function sharpenPhoto(context, width, height) {
  const frame = context.getImageData(0, 0, width, height);
  const source = new Uint8ClampedArray(frame.data);
  const stride = width * 4;
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const pixel = y * stride + x * 4;
      if (source[pixel + 3] !== 255) continue;
      for (let channel = 0; channel < 3; channel++) {
        const i = pixel + channel;
        const horizontal = source[i - 4] + source[i + 4];
        const vertical = source[i - stride] + source[i + stride];
        const corners = source[i - stride - 4] + source[i - stride + 4] +
          source[i + stride - 4] + source[i + stride + 4];
        const blurred = (4 * source[i] + 2 * (horizontal + vertical) + corners) / 16;
        frame.data[i] = source[i] + .48 * (source[i] - blurred);
      }
    }
  }
  context.putImageData(frame, 0, 0);
}

async function showProductPhoto(img, name, coverSupplierMark) {
  const version = ++photoVersion;
  photoTitle.textContent = name;
  photoFull.alt = name;
  photoFull.src = img.currentSrc || img.src;
  photoDialog.showModal();
  try {
    await img.decode();
    if (version !== photoVersion || !photoDialog.open) return;
    const scale = Math.min(2, 500 / img.naturalWidth, 1000 / img.naturalHeight);
    const width = Math.max(1, Math.round(img.naturalWidth * scale));
    photoStage.style.setProperty('--view-width', `${width}px`);
    photoStage.style.setProperty('--photo-ratio', img.naturalWidth / img.naturalHeight);
    photoStage.classList.toggle('cover-supplier-mark', coverSupplierMark);
    if (scale <= 1) return;
    const height = Math.max(1, Math.round(img.naturalHeight * scale));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d', {willReadFrequently:true});
    if (!context) return;
    context.imageSmoothingQuality = 'high';
    context.drawImage(img, 0, 0, width, height);
    sharpenPhoto(context, width, height);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
    if (!blob || version !== photoVersion || !photoDialog.open) return;
    if (enhancedPhotoUrl) URL.revokeObjectURL(enhancedPhotoUrl);
    enhancedPhotoUrl = URL.createObjectURL(blob);
    photoFull.src = enhancedPhotoUrl;
  } catch (_) {
    // An external image without canvas access still opens with the visual watermark.
  }
}

function renderProducts(products) {
  const tires = state.view === 'tires';
  const template = document.getElementById(tires ? 'tireCardTemplate' : 'wheelCardTemplate');
  productGrid.replaceChildren();
  if (!products.length) {
    productGrid.innerHTML = '<p class="empty-state">По этому подбору товаров пока нет.</p>';
    return;
  }
  for (const product of products) {
    const card = template.content.cloneNode(true);
    const spec = tires ? product.tire : product.wheel;
    const name = product.brand === 'Литье' ? product.model : `${product.brand} ${product.model}`;
    const visual = card.querySelector('.product-visual');
    const photoButton = card.querySelector('.product-photo-button');
    const photoFrame = card.querySelector('.product-photo-frame');
    const img = card.querySelector('.product-image');
    if (product.image_url) {
      const coverSupplierMark = /(?:^|\/)assets\/wheel-photos\//.test(product.image_url);
      img.alt = name;
      img.loading = 'lazy';
      img.onload = () => {
        photoFrame.style.setProperty('--photo-ratio', img.naturalWidth / img.naturalHeight);
        photoFrame.classList.toggle('cover-supplier-mark', coverSupplierMark);
      };
      img.onerror = () => {
        visual.classList.remove('has-image');
        photoButton.hidden = true;
      };
      visual.classList.add('has-image');
      photoButton.hidden = false;
      photoButton.setAttribute('aria-label', `Увеличить фото: ${name}`);
      photoButton.onclick = () => showProductPhoto(img, name, coverSupplierMark);
      img.src = product.image_url;
    }
    if (tires) {
      card.querySelector('h3').textContent = `${spec.width}/${spec.profile} R${spec.diameter}`;
      card.querySelector('.product-name').textContent = name;
      card.querySelector('.season').textContent = spec.season;
      card.querySelector('.load-index').textContent = spec.load_index;
    } else {
      card.querySelector('h3').textContent = name;
      card.querySelector('.product-name').textContent = spec.color;
      card.querySelector('.diameter').textContent = `R${spec.diameter}`;
      card.querySelector('.bolt').textContent = `Разболтовка: ${spec.bolt_pattern}`;
    }
    card.querySelector('.stock').textContent = `${product.stock} шт`;
    card.querySelector('.price').textContent = money(product.price);
    card.querySelector('.order-button').onclick = () => openDrawer('orders', product);
    productGrid.append(card);
  }
}
function switchView(view) {
  state.view = view;
  document.querySelectorAll('.nav-link[data-view]').forEach(button => {
    const active = button.dataset.view === view;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  renderFilters();
  loadCatalog();
}
const employeeArea = document.getElementById('employeeDrawer');
const publicSite = document.getElementById('publicSite');
const employeeContent = document.getElementById('employeeContent');
let workspaceRevision = 0;
let catalogScroll = 0;

function toggleDrawer(open) {
  if (open) catalogScroll = window.scrollY;
  else workspaceRevision++;
  publicSite.hidden = open;
  employeeArea.hidden = !open;
  window.scrollTo(0, open ? 0 : catalogScroll);
  if (!open) employeeEntry.focus({preventScroll:true});
}

const workspaceSections = {
  orders: {label:'Заказы', render:ordersView},
  suppliers: {label:'Поставщики', render:suppliersView},
  clients: {label:'Клиенты', render:clientsView},
  inventory: {label:'Номенклатура', render:inventoryView},
  mailing: {label:'Рассылки', render:mailingsView},
  employees: {label:'Сотрудники', render:employeesView}
};

function branchLabel(id) {
  const branch = state.branches.find(item => item.id === id);
  return branch ? branch.name : '';
}
function isAdmin() { return state.user?.role === 'admin'; }
function canEditBranch(branchId) { return isAdmin() || state.user?.branch_id === branchId; }

async function ensureBranches() {
  if (!state.branches.length) {
    try { state.branches = await api('/branches'); } catch (_) { state.branches = []; }
  }
  return state.branches;
}

function workspace() {
  const admin = state.user.role === 'admin';
  const access = document.querySelector('.role-switch');
  access.innerHTML = `<span class="login-hint">${esc(state.user.name)} · ${admin ? 'Администратор' : 'Сотрудник'}</span>
    <button type="button" class="logout-button" id="logout">Выйти</button>`;
  const tabs = document.querySelector('.employee-tabs');
  tabs.innerHTML = Object.entries(workspaceSections)
    .filter(([key]) => key !== 'mailing' || admin)
    .filter(([key]) => key !== 'employees' || admin)
    .map(([key, section]) => {
      const active = state.tab === key;
      return `<button type="button" class="nav-link${active ? ' active' : ''}" data-tab="${key}" aria-pressed="${active}">${section.label}</button>`;
    }).join('');
  access.querySelector('#logout').onclick = () => {
    workspaceRevision++;
    state.user = null;
    localStorage.removeItem('alauto_session');
    loginView();
  };
  tabs.querySelectorAll('button').forEach(button => {
    button.onclick = () => {
      state.tab = button.dataset.tab;
      state.selected = null;
      workspace();
    };
  });
  employeeContent.innerHTML = '<p class="empty-state">Загрузка…</p>';
  ensureBranches().finally(() => {
    workspaceSections[state.tab].render(++workspaceRevision);
  });
}

const orderStatus = {in_transit:'В пути', completed:'Завершён'};
const suppliers = ['ШинСервис', '4точки', 'Вершина', 'Шинные Решения', 'ПинАвто', 'Asia tyres'];
let orderStatusFilter = 'in_transit';
const dateLabel = value => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString('ru-RU');
};
const shortDate = value => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : `${String(date.getDate()).padStart(2, '0')}.${String(date.getMonth() + 1).padStart(2, '0')}`;
};
const plural = (count, forms) => {
  const mod10 = count % 10, mod100 = count % 100;
  return forms[(mod10 === 1 && mod100 !== 11) ? 0 : (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) ? 1 : 2];
};
function workspaceHeading(label, action, id) {
  return `<div class="section-heading workspace-heading"><h1>${label}</h1>
    <button type="button" class="primary-action" id="${id}">${action}</button></div><div id="formHost"></div>`;
}
function workspaceError(error, revision) {
  if (revision === workspaceRevision) employeeContent.innerHTML = `<p class="empty-state">${esc(error.message)}</p>`;
}
function statusTabs(counts) {
  return `<div class="catalog-sources order-status-tabs" role="group" aria-label="Статус заказов">${Object.entries(orderStatus)
    .map(([value, label]) => `<button type="button" data-status-filter="${value}" aria-pressed="${orderStatusFilter === value}">${label} <span class="tab-count">${counts[value] || 0}</span></button>`).join('')}</div>`;
}
function statusCounts(orders) {
  return orders.reduce((counts, order) => {
    counts[order.status] = (counts[order.status] || 0) + 1;
    return counts;
  }, {in_transit: 0, completed: 0});
}

function orderCard(order, client) {
  const lines = order.items.map(item => `<div class="order-column">
      <small>${esc(item.supplier || 'Поставщик не указан')}</small>
      <span class="order-item-name">${esc(item.name)}</span>
      <strong>${esc(item.quantity)} шт. × ${money(item.unit_price)} ₽</strong>
    </div>`);
  const contents = lines.length ? lines.join('')
    : `<div class="order-column"><span class="order-item-name">${esc(order.comment || 'Содержимое не указано')}</span></div>`;
  return `<article class="order-ticket${lines.length > 1 ? ' order-wide' : ''}" data-order-ticket="${order.id}">
    <header>
      <div class="ticket-title">
        <button type="button" data-order-id="${order.id}" aria-label="Открыть заказ №${order.id}">Заказ №${order.id} ↗</button>
        <span class="ticket-date">${esc(shortDate(order.created_at))}</span>
        ${branchLabel(order.branch_id) ? `<span class="branch-tag">${esc(branchLabel(order.branch_id))}</span>` : ''}
      </div>
      ${canEditBranch(order.branch_id) ? `<div class="status-switch" role="group" aria-label="Статус заказа №${order.id}">${Object.entries(orderStatus)
        .map(([value, label]) => `<button type="button" data-set-status="${value}" aria-pressed="${order.status === value}">${label}</button>`).join('')}</div>` : ''}
    </header>
    <div class="order-columns" tabindex="0" aria-label="Содержимое заказа">${contents}</div>
    <footer>
      <strong>${esc(client?.phone || 'Телефон не указан')}</strong>
      <div class="ticket-client">
        <span>${esc(client?.name || 'Клиент не указан')}</span>
        ${client?.code ? `<button type="button" class="client-link" data-client-card="${order.client_id}" aria-label="Открыть клиента ${esc(client.code)}">${esc(client.code)}</button>` : ''}
      </div>
      <small>Остаток ${money(order.remainder)} ₽</small>
    </footer>
  </article>`;
}

async function ordersView(revision) {
  try {
    const [orders, clients] = await Promise.all([api('/orders'), api('/clients')]);
    if (revision !== workspaceRevision) return;
    const people = new Map(clients.map(client => [client.id, client]));
    employeeContent.innerHTML = `<div class="section-heading workspace-heading"><h1>Заказы</h1></div>
      <div id="orderTabs"></div><div id="formHost"></div>
      <div class="order-board" id="orderBoard"><button type="button" id="newOrder" class="order-new"><b aria-hidden="true">＋</b>Новый заказ</button></div>
      <p class="empty-state" id="orderEmpty" hidden>В этом статусе заказов пока нет.</p>`;
    const board = employeeContent.querySelector('#orderBoard');
    const tabs = employeeContent.querySelector('#orderTabs');
    const empty = employeeContent.querySelector('#orderEmpty');
    const newOrder = board.querySelector('#newOrder');
    function render() {
      tabs.innerHTML = statusTabs(statusCounts(orders));
      board.querySelectorAll('.order-ticket').forEach(node => node.remove());
      const visible = orders.filter(order => order.status === orderStatusFilter);
      newOrder.insertAdjacentHTML('afterend', visible.map(order => orderCard(order, people.get(order.client_id))).join(''));
      empty.hidden = visible.length > 0;
    }
    newOrder.onclick = () => orderForm(null, clients, revision);
    window.onClientsUpdated = render;
    tabs.onclick = event => {
      const button = event.target.closest('[data-status-filter]');
      if (!button || button.dataset.statusFilter === orderStatusFilter) return;
      orderStatusFilter = button.dataset.statusFilter;
      render();
    };
    board.onclick = event => {
      const toggle = event.target.closest('[data-set-status]');
      const ticket = event.target.closest('[data-order-ticket]');
      if (toggle && ticket) {
        const orderId = Number(ticket.dataset.orderTicket);
        const next = toggle.dataset.setStatus;
        toggle.closest('.status-switch').classList.add('is-busy');
        api(`/orders/${orderId}/status`, {method:'PATCH', body: JSON.stringify({status: next})})
          .then(updated => {
            const index = orders.findIndex(order => order.id === orderId);
            if (index >= 0) orders[index] = updated;
            render();
            message(`Заказ №${orderId}: ${orderStatus[next].toLowerCase()}.`, 'success');
          })
          .catch(error => { message(error.message); render(); });
        return;
      }
      const open = event.target.closest('[data-order-id]');
      if (open) {
        const order = orders.find(order => order.id === Number(open.dataset.orderId));
        if (order && !canEditBranch(order.branch_id)) {
          message('Этот заказ создан в другом филиале — доступен только для просмотра.');
        }
        orderForm(null, clients, revision, order);
        return;
      }
      const clientButton = event.target.closest('[data-client-card]');
      if (clientButton) showClientCard(people.get(Number(clientButton.dataset.clientCard)), revision, clients);
    };
    render();
    if (state.selected) {
      orderForm(state.selected, clients, revision);
      state.selected = null;
    }
  } catch (error) {
    workspaceError(error, revision);
  }
}

async function employeesView(revision) {
  try {
    const [users, branches] = await Promise.all([api('/users'), ensureBranches()]);
    if (revision !== workspaceRevision) return;
    employeeContent.innerHTML = `<div class="section-heading workspace-heading"><h1>Сотрудники</h1>
      <button type="button" class="primary-action" id="newEmployee">+ Сотрудник</button></div>
      <div id="formHost"></div>
      <div class="employee-board">${users.map(user => employeeCard(user)).join('')}</div>`;
    employeeContent.querySelector('#newEmployee').onclick = () => employeeForm(revision, null, users);
    const board = employeeContent.querySelector('.employee-board');
    board.onclick = event => {
      const edit = event.target.closest('[data-edit-user]');
      if (edit) {
        employeeForm(revision, users.find(user => user.id === Number(edit.dataset.editUser)), users);
        return;
      }
      const remove = event.target.closest('[data-delete-user]');
      if (remove && confirm('Удалить сотрудника?')) {
        api('/users/' + remove.dataset.deleteUser, {method:'DELETE'})
          .then(() => { message('Сотрудник удалён.', 'success'); workspace(); })
          .catch(error => message(error.message));
      }
    };
  } catch (error) {
    workspaceError(error, revision);
  }
}

function employeeCard(user) {
  const role = user.role === 'admin' ? 'Администратор' : 'Сотрудник';
  const branch = user.role === 'admin' ? 'Все филиалы' : (branchLabel(user.branch_id) || '—');
  return `<article class="order-ticket employee-ticket" data-user-id="${user.id}">
    <div class="card-line"><h3>${esc(user.name)}</h3><span class="diameter">${role}</span></div>
    <p class="employee-login">Логин: <b>${esc(user.login)}</b></p>
    <p class="employee-branch">Филиал: <b>${esc(branch)}</b></p>
    <div class="form-actions employee-actions">
      <button type="button" class="ghost-action" data-edit-user="${user.id}">Изменить</button>
      <button type="button" class="ghost-action danger-action" data-delete-user="${user.id}">Удалить</button>
    </div>
  </article>`;
}

function employeeForm(revision, user = null, users = []) {
  const host = document.getElementById('formHost');
  const branchOptions = state.branches.map(branch =>
    `<option value="${branch.id}" ${user?.branch_id === branch.id ? 'selected' : ''}>${esc(branch.name)}</option>`).join('');
  host.innerHTML = `<form class="modal" id="employeeForm"><h2>${user ? 'Карточка сотрудника' : 'Новый сотрудник'}</h2>
    <div class="form-fields">
      <label class="field">Имя *<input name="name" maxlength="120" required value="${esc(user?.name ?? '')}"></label>
      <label class="field">Логин *<input name="login" maxlength="64" required value="${esc(user?.login ?? '')}"></label>
      <label class="field">Пароль ${user ? '<small>оставьте пустым, чтобы не менять</small>' : '*'}<input name="password" type="password" autocomplete="new-password" ${user ? '' : 'required'} minlength="4"></label>
      <label class="field">Роль<select name="role">
        <option value="employee" ${user?.role !== 'admin' ? 'selected' : ''}>Сотрудник</option>
        <option value="admin" ${user?.role === 'admin' ? 'selected' : ''}>Администратор</option>
      </select></label>
      <label class="field">Филиал<select name="branch_id">
        <option value="">—</option>${branchOptions}
      </select></label>
    </div>
    <p class="form-error" role="alert" hidden></p>
    <div class="form-actions"><button type="button" class="ghost-action" data-close-employee>Отмена</button>
      <button type="submit" class="primary-action">${user ? 'Сохранить' : 'Создать сотрудника'}</button></div></form>`;
  const form = host.querySelector('form');
  form.querySelector('[data-close-employee]').onclick = () => host.replaceChildren();
  form.onsubmit = event => {
    event.preventDefault();
    const values = new FormData(form);
    const payload = {name: values.get('name').trim(), login: values.get('login').trim(),
      password: values.get('password') || null, role: values.get('role'),
      branch_id: values.get('branch_id') ? Number(values.get('branch_id')) : null};
    submitWorkspaceForm(form, revision, user ? '/users/' + user.id : '/users', payload,
      user ? 'Сотрудник обновлён.' : 'Сотрудник создан.', user ? 'PUT' : 'POST');
  };
  form.elements.name.focus();
}

async function suppliersView(revision) {
  try {
    const suppliers = await api('/suppliers');
    if (revision !== workspaceRevision) return;
    const admin = state.user.role === 'admin';
    employeeContent.innerHTML = `<div class="section-heading workspace-heading"><h1>Поставщики</h1>
        <button type="button" class="primary-action" id="newSupplier">+ Поставщик</button></div>
      <div id="formHost"></div>
      <div class="order-board supplier-board" id="supplierBoard">${suppliers.map(supplier => supplierCard(supplier, admin)).join('')}</div>
      <p class="notice supplier-hint">Excel: .xls, .xlsx, .xlsm — колонки находятся по заголовкам, размер берётся из наименования. Остатки по API: <b>POST /api/ingest/{код}</b> с заголовком <b>X-API-Key</b>.</p>`;
    const board = employeeContent.querySelector('#supplierBoard');
    employeeContent.querySelector('#newSupplier').onclick = () => supplierForm(revision);
    board.onchange = event => {
      const input = event.target.closest('[data-stock-file]');
      const card = input?.closest('[data-supplier-id]');
      if (!input?.files[0] || !card) return;
      const supplier = suppliers.find(item => item.id === Number(card.dataset.supplierId));
      previewSupplierStock(supplier, input.files[0], revision);
      input.value = '';
    };
    board.onclick = event => {
      const button = event.target.closest('[data-issue-key]');
      if (!button) return;
      const card = button.closest('[data-supplier-id]');
      const supplier = suppliers.find(item => item.id === Number(card.dataset.supplierId));
      issueSupplierKey(supplier, revision);
    };
  } catch (error) {
    workspaceError(error, revision);
  }
}

function supplierCard(supplier, admin) {
  return `<article class="order-ticket supplier-card" data-supplier-id="${supplier.id}">
    <div class="card-line"><h3>${esc(supplier.name)}</h3>${supplier.variant ? `<span class="diameter">${esc(supplier.variant)}</span>` : ''}</div>
    <label class="supplier-upload">
      <span class="eyebrow">Загрузить остатки из Excel</span>
      <input type="file" accept=".xls,.xlsx,.xlsm" data-stock-file>
    </label>
    <div class="supplier-key">
      <span class="supplier-key-status">${supplier.has_key ? 'Ключ API выдан' : 'Ключ API не выдан'}</span>
      ${admin ? '<button type="button" class="ghost-action" data-issue-key>Ключ API</button>' : ''}
    </div>
    <p class="supplier-sync">${supplier.last_sync_at ? `Список от ${esc(dateLabel(supplier.last_sync_at))} · ${esc(supplier.last_rows_ok)} ${plural(supplier.last_rows_ok || 0, ['строка', 'строки', 'строк'])}` : 'Списков пока нет'}</p>
  </article>`;
}

async function previewSupplierStock(supplier, file, revision) {
  const host = document.getElementById('formHost');
  if (!host || !supplier) return;
  host.innerHTML = '<p class="notice">Разбираем файл…</p>';
  try {
    const upload = new FormData();
    upload.append('file', file);
    const preview = await api(`/suppliers/${supplier.id}/stock/preview`, {method:'POST', body: upload});
    if (revision !== workspaceRevision) return;
    host.innerHTML = `<form class="modal stock-preview" data-stock-preview>
      <h2>Проверка файла</h2>
      <p class="notice">${esc(supplier.name)} · ${esc(preview.filename || file.name)} · наценка ${money(supplier.markup_percent)}% · найдено колонок: ${esc(Object.keys(preview.columns || {}).length)}</p>
      ${preview.valid_rows.length ? `<div class="workspace-table stock-table"><table class="data-table"><thead><tr><th>Стр.</th><th>Бренд</th><th>Наименование</th><th>Размер</th><th>Сезон</th><th>Цена поставщика</th><th>С наценкой</th><th>Ост.</th></tr></thead><tbody>${preview.valid_rows.map(row => `<tr>
        <td>${esc(row.row)}</td><td>${esc(row.brand)}</td><td>${esc(row.model)}</td>
        <td>${esc(row.width)}/${esc(row.profile)} R${esc(row.diameter)}</td><td>${esc(row.season)}</td>
        <td>${money(row.price)} ₽</td><td>${money(Number(row.price) * (1 + Number(supplier.markup_percent) / 100))} ₽</td><td>${esc(row.stock)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="empty-state">Подходящих строк нет.</p>'}
      ${preview.errors.length ? `<div class="import-errors"><b>Ошибки (${preview.errors.length}):</b><ul>${preview.errors.map(error => `<li>строка ${esc(error.row)} — ${esc(error.message)}</li>`).join('')}</ul></div>` : ''}
      <p class="form-error" role="alert" hidden></p>
      <div class="form-actions"><button type="button" class="ghost-action" data-cancel-stock>Отмена</button>
        <button type="submit" class="primary-action" ${preview.valid_rows.length ? '' : 'disabled'}>Загрузить ${preview.valid_rows.length} ${plural(preview.valid_rows.length, ['строку', 'строки', 'строк'])}</button></div>
    </form>`;
    const form = host.querySelector('[data-stock-preview]');
    form.querySelector('[data-cancel-stock]').onclick = () => host.replaceChildren();
    form.onsubmit = event => {
      event.preventDefault();
      submitWorkspaceForm(form, revision, `/suppliers/${supplier.id}/stock/confirm`,
        {filename: preview.filename, rows: preview.valid_rows}, `Остатки «${supplier.name}» обновлены.`, 'POST');
    };
  } catch (error) {
    host.innerHTML = `<p class="empty-state">${esc(error.message)}</p>`;
  }
}

async function issueSupplierKey(supplier, revision) {
  const host = document.getElementById('formHost');
  if (!host || !supplier) return;
  try {
    const result = await api(`/suppliers/${supplier.id}/key`, {method:'POST', body: JSON.stringify({})});
    if (revision !== workspaceRevision) return;
    host.innerHTML = `<div class="modal"><h2>API-ключ · ${esc(supplier.name)}</h2>
      <p class="notice">Ключ показывается один раз — передайте его поставщику. Прежний ключ сразу перестаёт работать.</p>
      <p class="notice">Адрес приёма: <b>POST ${esc(result.ingest_url)}</b></p>
      <code class="api-key">${esc(result.api_key)}</code>
      <div class="form-actions"><button type="button" class="ghost-action" data-copy-key>Копировать</button>
        <button type="button" class="primary-action" data-close-key>Готово</button></div></div>`;
    host.querySelector('[data-close-key]').onclick = () => { host.replaceChildren(); workspace(); };
    host.querySelector('[data-copy-key]').onclick = async () => {
      try {
        await navigator.clipboard.writeText(result.api_key);
        message('Ключ скопирован.', 'success');
      } catch (_) { message('Скопируйте ключ вручную.'); }
    };
  } catch (error) {
    message(error.message);
  }
}

function supplierForm(revision) {
  const host = document.getElementById('formHost');
  host.innerHTML = `<form class="modal" id="supplierForm"><h2>Новый поставщик</h2>
    <div class="form-fields">
      <label class="field">Название *<input name="name" maxlength="120" required placeholder="Например: ШинСервис"></label>
      <label class="field">Наценка, %<input name="markup_percent" type="number" min="0" max="100" step="0.01" value="25" required></label>
    </div>
    <p class="form-error" role="alert" hidden></p>
    <div class="form-actions"><button type="button" class="ghost-action" data-close-supplier>Отмена</button>
      <button type="submit" class="primary-action">Создать</button></div></form>`;
  const form = host.querySelector('form');
  form.querySelector('[data-close-supplier]').onclick = () => host.replaceChildren();
  form.onsubmit = event => {
    event.preventDefault();
    const values = new FormData(form);
    submitWorkspaceForm(form, revision, '/suppliers', {name: values.get('name').trim(), markup_percent: values.get('markup_percent')}, 'Поставщик добавлен.', 'POST');
  };
  form.elements.name.focus();
}

function clientFactsMarkup(orders) {
  const list = orders || [];
  const total = list.reduce((sum, order) => sum + Number(order.total_amount || 0), 0);
  return `<dl class="client-facts">
    <div><dt>Заказов</dt><dd>${orders ? orders.length : '—'}</dd></div>
    <div><dt>На сумму</dt><dd>${orders ? money(total) + ' ₽' : '—'}</dd></div>
  </dl>`;
}
function clientHistoryMarkup(orders) {
  const rows = (orders || []).map(order => {
    const contents = (order.items || []).map(item => item.name).filter(Boolean).join(', ') || order.comment || '—';
    const suppliersList = (order.items || []).map(item => item.supplier).filter(Boolean).join(', ') || order.supplier || '—';
    return `<tr data-order-row="${order.id}">
      <td>№${esc(order.id)}</td><td>${esc(dateLabel(order.created_at))}</td>
      <td>${esc(suppliersList)}</td>
      <td class="client-order-contents">${esc(contents)}</td>
      <td>${money(order.total_amount)} ₽</td>
      <td><span class="status">${esc(orderStatus[order.status] || order.status)}</span></td>
    </tr>`;
  }).join('');
  return `<section class="client-history"><h3>История заказов</h3>${orders === null
    ? '<p class="notice">Загружаем историю заказов…</p>'
    : rows ? `<div class="workspace-table"><table class="data-table"><thead><tr><th>Заказ</th><th>Дата</th><th>Поставщик</th><th>Содержимое</th><th>Сумма</th><th>Статус</th></tr></thead><tbody>${rows}</tbody></table></div>`
    : '<p class="notice">Заказов пока нет.</p>'}</section>`;
}
function clientCardMarkup(client, orders) {
  const branchSwitch = isAdmin() && state.branches.length ? `<div class="client-branch-switch">
      <span class="eyebrow">Филиал клиента</span>
      <div class="segmented" role="group" aria-label="Филиал клиента">${state.branches.map(branch =>
        `<button type="button" data-set-branch="${branch.id}" aria-pressed="${client.branch_id === branch.id}">${esc(branch.name)}</button>`).join('')}</div>
    </div>` : '';
  return `<div class="client-card">
    <div class="client-card-heading">
      <div class="client-identity"><span class="eyebrow">ID · ${esc(client.code || '—')}</span><h2>${esc(client.name)}</h2></div>
      <button type="button" class="ghost-action" data-close-client>Закрыть ×</button>
    </div>
    ${branchSwitch}
    <form class="client-edit" data-client-form>
      <div class="form-fields">
        <label class="field">Имя *<input name="name" maxlength="120" required value="${esc(client.name)}"></label>
        <label class="field">Телефон *<input name="phone" type="tel" minlength="5" maxlength="32" required value="${esc(client.phone)}"></label>
        <label class="field full">Примечание<textarea name="note" maxlength="2000" placeholder="Например: предпочитает дешёвые китайские шины, Ford Focus 2 205/55/16">${esc(client.note || '')}</textarea></label>
      </div>
      <p class="notice">ID клиента пересчитывается автоматически при изменении имени или телефона.</p>
      <p class="form-error" role="alert" hidden></p>
      <div class="form-actions"><button type="submit" class="primary-action">Сохранить</button></div>
    </form>
    ${clientFactsMarkup(orders)}
    ${clientHistoryMarkup(orders)}
    <div class="form-actions"><button type="button" class="primary-action" data-new-order>+ Новый заказ</button></div>
  </div>`;
}

function renderClientCard(dialog, client, orders, revision, request, clients) {
  dialog.innerHTML = clientCardMarkup(client, orders);
  const form = dialog.querySelector('[data-client-form]');
  const identityName = dialog.querySelector('.client-identity h2');
  form.oninput = () => { identityName.textContent = form.elements.name.value.trim() || client.name; };
  form.onsubmit = async event => {
    event.preventDefault();
    const box = form.querySelector('.form-error');
    box.hidden = true;
    try {
      const updated = await api('/clients/' + client.id, {method:'PUT', body: JSON.stringify(readClient(new FormData(form)))});
      const shared = (clients || []).find(item => item.id === client.id);
      if (shared) Object.assign(shared, updated);
      if (typeof window.onClientsUpdated === 'function') window.onClientsUpdated();
      message('Клиент обновлён.', 'success');
      renderClientCard(dialog, updated, orders, revision, request, clients);
    } catch (error) {
      box.textContent = error.message;
      box.hidden = false;
      message(error.message);
    }
  };
  dialog.querySelector('[data-close-client]').onclick = () => dialog.close();
  for (const branchButton of dialog.querySelectorAll('[data-set-branch]')) {
    branchButton.onclick = async () => {
      const branchId = Number(branchButton.dataset.setBranch);
      if (branchId === client.branch_id) return;
      try {
        const updated = await api('/clients/' + client.id + '?branch_id=' + branchId,
          {method:'PUT', body: JSON.stringify({name: client.name, phone: client.phone, note: client.note})});
        const shared = (clients || []).find(item => item.id === client.id);
        if (shared) Object.assign(shared, updated);
        if (typeof window.onClientsUpdated === 'function') window.onClientsUpdated();
        message(`Филиал клиента изменён на «${branchLabel(updated.branch_id)}».`, 'success');
        renderClientCard(dialog, updated, orders, revision, request, clients);
      } catch (error) {
        message(error.message);
      }
    };
  }
  dialog.querySelector('[data-new-order]').onclick = () => {
    dialog.close();
    orderForm(null, clients, revision, null, client.id);
  };
  bindClientHistory(dialog, orders, revision, request, clients);
}

function bindClientHistory(dialog, orders, revision, request, clients) {
  for (const row of dialog.querySelectorAll('[data-order-row]')) {
    row.onclick = () => {
      const order = (orders || []).find(item => item.id === Number(row.dataset.orderRow));
      if (!order) return;
      dialog.close();
      orderForm(null, clients, revision, order);
    };
  }
}

let clientCardRequest = 0;
async function showClientCard(client, revision, clients = null) {
  if (!client) return;
  const request = ++clientCardRequest;
  for (const dialog of document.querySelectorAll('dialog.client-dialog')) dialog.remove();
  const dialog = document.createElement('dialog');
  dialog.className = 'client-dialog';
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => { if (request === clientCardRequest) ++clientCardRequest; dialog.remove(); });
  document.body.append(dialog);
  renderClientCard(dialog, client, null, revision, request, clients);
  dialog.showModal();
  let orders = null;
  try {
    orders = (await api('/orders?client_id=' + client.id)).filter(order => String(order.client_id) === String(client.id));
  } catch (_) {
    orders = null;
  }
  if (request !== clientCardRequest || !dialog.isConnected) return;
  if (orders === null) {
    const history = dialog.querySelector('.client-history');
    if (history) history.innerHTML = '<h3>История заказов</h3><p class="notice">Не удалось загрузить историю заказов.</p>';
    return;
  }
  dialog.querySelector('.client-facts').outerHTML = clientFactsMarkup(orders);
  dialog.querySelector('.client-history').outerHTML = clientHistoryMarkup(orders);
  bindClientHistory(dialog, orders, revision, request, clients);
}

async function clientsView(revision) {
  try {
    const [clients, orders, branches] = await Promise.all([api('/clients'), api('/orders'), ensureBranches()]);
    if (revision !== workspaceRevision) return;
    const counts = orders.reduce((map, order) => { map[order.client_id] = (map[order.client_id] || 0) + 1; return map; }, {});
    const admin = isAdmin();
    let branchFilter = state.clientBranchFilter ?? '';
    employeeContent.innerHTML = `<div class="section-heading workspace-heading"><h1>Клиенты</h1>
        <button type="button" class="primary-action" id="newClient">+ Клиент</button></div>
      ${admin ? `<div class="catalog-sources client-branch-tabs" role="group" aria-label="База клиентов">
        <button type="button" data-branch-filter="" aria-pressed="${branchFilter === ''}">Все базы</button>
        ${branches.map(branch => `<button type="button" data-branch-filter="${branch.id}" aria-pressed="${String(branch.id) === String(branchFilter)}">${esc(branch.name)}</button>`).join('')}
      </div>` : ''}
      <label class="field client-search">Поиск<input id="clientSearch" type="search" placeholder="Имя, телефон или ID" autocomplete="off"></label>
      <div id="formHost"></div><div class="client-card-grid" id="clientGrid"><p class="empty-state">Клиенты не найдены.</p></div>`;
    const grid = employeeContent.querySelector('#clientGrid');
    const search = employeeContent.querySelector('#clientSearch');
    function render() {
      const term = search.value.trim().toLowerCase();
      const visible = clients.filter(client => (branchFilter === '' || String(client.branch_id) === String(branchFilter))
        && (!term || [client.name, client.phone, client.code, client.note]
        .some(value => String(value || '').toLowerCase().includes(term))));
      grid.innerHTML = visible.length
        ? visible.map(client => clientTile(client, counts[client.id] || 0)).join('')
        : '<p class="empty-state">Клиенты не найдены.</p>';
    }
    search.oninput = render;
    window.onClientsUpdated = render;
    render();
    if (admin) employeeContent.querySelector('.client-branch-tabs').onclick = event => {
      const button = event.target.closest('[data-branch-filter]');
      if (!button) return;
      branchFilter = button.dataset.branchFilter;
      state.clientBranchFilter = branchFilter;
      for (const option of employeeContent.querySelectorAll('[data-branch-filter]')) {
        option.setAttribute('aria-pressed', String(option.dataset.branchFilter === branchFilter));
      }
      render();
    };
    employeeContent.querySelector('#newClient').onclick = () => clientForm(revision);
    grid.onclick = event => {
      const remove = event.target.closest('[data-delete-client]');
      if (remove) {
        const client = clients.find(item => item.id === Number(remove.dataset.deleteClient));
        if (client && confirm(`Удалить клиента «${client.name}» из базы?`)) {
          api('/clients/' + client.id, {method:'DELETE'})
            .then(() => {
              const index = clients.findIndex(item => item.id === client.id);
              if (index >= 0) clients.splice(index, 1);
              message('Клиент удалён из базы.', 'success');
              render();
            })
            .catch(error => message(error.message));
        }
        return;
      }
      const ordersButton = event.target.closest('[data-client-orders]');
      if (ordersButton) {
        showClientOrders(clients.find(client => client.id === Number(ordersButton.dataset.clientOrders)), revision, clients);
        return;
      }
      const editButton = event.target.closest('[data-edit-client]');
      if (editButton) {
        showClientCard(clients.find(client => client.id === Number(editButton.dataset.editClient)), revision, clients);
        return;
      }
      const button = event.target.closest('[data-client-card]');
      if (button) showClientCard(clients.find(client => client.id === Number(button.dataset.clientCard)), revision, clients);
    };
  } catch (error) {
    workspaceError(error, revision);
  }
}

function clientTile(client, orderCount) {
  return `<article class="client-tile" data-client-tile="${client.id}">
    <header class="client-tile-top">
      <span class="client-tile-id">ID клиента: <b>${esc(client.code || '—')}</b></span>
      <button type="button" class="client-tile-count" data-client-orders="${client.id}" aria-label="Заказы клиента ${esc(client.code || client.name)}">Заказов: <b>${orderCount}</b></button>
    </header>
    <h3 class="client-tile-name">${esc(client.name)}</h3>
    <a class="client-tile-phone" href="tel:${esc(String(client.phone).replace(/[^\d+]/g, ''))}">${esc(client.phone)}</a>
    <p class="client-tile-note">${esc(client.note || 'Примечания пока нет')}${isAdmin() && branchLabel(client.branch_id) ? `<span class="branch-tag">${esc(branchLabel(client.branch_id))}</span>` : ''}</p>
    <div class="client-tile-actions">
      <button type="button" class="ghost-action client-tile-edit" data-edit-client="${client.id}" aria-label="Изменить клиента ${esc(client.code || client.name)}">Изменить</button>
      <button type="button" class="ghost-action danger-action client-tile-delete" data-delete-client="${client.id}" aria-label="Удалить клиента ${esc(client.code || client.name)}">Удалить</button>
    </div>
  </article>`;
}

async function showClientOrders(client, revision, clients = null) {
  if (!client) return;
  const request = ++clientCardRequest;
  for (const dialog of document.querySelectorAll('dialog.client-dialog')) dialog.remove();
  const dialog = document.createElement('dialog');
  dialog.className = 'client-dialog';
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => { if (request === clientCardRequest) ++clientCardRequest; dialog.remove(); });
  document.body.append(dialog);
  dialog.innerHTML = `<div class="client-card client-orders-card">
    <div class="client-card-heading">
      <div class="client-identity"><span class="eyebrow">ID · ${esc(client.code || '—')}</span><h2>Заказы · ${esc(client.name)}</h2></div>
      <button type="button" class="ghost-action" data-close-client>Закрыть ×</button>
    </div>
    ${clientHistoryMarkup(null)}
  </div>`;
  dialog.querySelector('[data-close-client]').onclick = () => dialog.close();
  dialog.showModal();
  let orders = null;
  try {
    orders = (await api('/orders?client_id=' + client.id)).filter(order => String(order.client_id) === String(client.id));
  } catch (_) {
    orders = null;
  }
  if (request !== clientCardRequest || !dialog.isConnected) return;
  if (orders === null) {
    dialog.querySelector('.client-history').innerHTML = '<h3>История заказов</h3><p class="notice">Не удалось загрузить заказы.</p>';
    return;
  }
  dialog.querySelector('.client-history').outerHTML = clientHistoryMarkup(orders);
  bindClientHistory(dialog, orders, revision, request, clients);
}

function clientFields() {
  return `<label class="field">Имя *<input name="name" maxlength="120" required></label>
    <label class="field">Телефон *<input name="phone" type="tel" inputmode="tel" pattern="(\\+7|8)\\d{10}" title="11 цифр, начинается с +7 или 8" placeholder="+79876543210" required></label>
    <label class="field full">Примечание<textarea name="note" maxlength="2000" placeholder="Например: предпочитает дешёвые китайские шины, Ford Focus 2 205/55/16"></textarea></label>`;
}

function readClient(values) {
  const phone = String(values.get('phone') || '').trim();
  const digits = phone.replace(/\D/g, '');
  if (digits.length !== 11 || !((phone.startsWith('+') && digits.startsWith('7')) || (!phone.startsWith('+') && digits.startsWith('8')))) {
    throw Error('Телефон должен содержать 11 цифр и начинаться с «+7» или «8».');
  }
  return {name:values.get('name').trim(), phone, note:values.get('note').trim() || null};
}

function clientCodePreview(name, phone) {
  const digits = String(phone || '').replace(/\D/g, '');
  const code = `${String(name || '').trim().slice(0, 36)}${digits.slice(-4)}`;
  return code || '—';
}

async function submitWorkspaceForm(form, revision, path, payload, confirmation, method = 'POST', verify = null) {
  if (form.dataset.saving) return;
  form.dataset.saving = 'true';
  const submit = form.querySelector('[type="submit"]');
  const errorBox = form.querySelector('.form-error');
  submit.disabled = true;
  errorBox.hidden = true;
  try {
    await api(path,{method,body:JSON.stringify(payload)});
    if (verify) await verify();
    if (revision === workspaceRevision) workspace();
    message(confirmation,'success');
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    delete form.dataset.saving;
    submit.disabled = false;
  }
}

function clientForm(revision, client = null) {
  const host = document.getElementById('formHost');
  const branchSelect = isAdmin() && !client ? `<label class="field">База клиента<select name="branch_id">
    ${state.branches.map(branch => `<option value="${branch.id}">${esc(branch.name)}</option>`).join('')}
  </select></label>` : '';
  host.innerHTML = `<form class="modal" id="clientForm"><h2>${client ? 'Карточка клиента' : 'Новый клиент'}</h2>
    <p class="client-id-preview">ID клиента (создаётся автоматически): <b data-client-id>—</b></p>
    <div class="form-fields">${branchSelect}${clientFields()}</div>
    <p class="form-error" role="alert" hidden></p>
    <div class="form-actions"><button type="button" class="ghost-action" data-close-client-form>Отмена</button>
      <button type="submit" class="primary-action">${client ? 'Сохранить' : 'Создать клиента'}</button></div></form>`;
  const form = host.querySelector('form');
  const preview = form.querySelector('[data-client-id]');
  const updatePreview = () => { preview.textContent = clientCodePreview(form.elements.name.value, form.elements.phone.value); };
  form.oninput = updatePreview;
  form.onsubmit = event => {
    event.preventDefault();
    const values = new FormData(form);
    let clientData;
    try { clientData = readClient(values); } catch (error) {
      message(error.message);
      const box = form.querySelector('.form-error');
      box.textContent = error.message; box.hidden = false;
      return;
    }
    const branchQuery = (!client && isAdmin() && values.get('branch_id')) ? `?branch_id=${values.get('branch_id')}` : '';
    submitWorkspaceForm(form, revision, client ? '/clients/' + client.id : '/clients' + branchQuery,
      clientData, client ? 'Клиент обновлён.' : 'Клиент создан.', client ? 'PUT' : 'POST');
  };
  form.querySelector('[data-close-client-form]').onclick = () => host.replaceChildren();
  if (client) for (const key of ['name','phone','note']) form.elements[key].value = client[key] ?? '';
  updatePreview();
  form.elements.name.focus();
}

function orderForm(selected, clients, revision, order = null, presetClientId = null) {
  clients = clients || [];
  const host = document.getElementById('formHost');
  const supplierOptions = suppliers.map(supplier => `<option>${esc(supplier)}</option>`).join('');
  const clientOptions = clients.map(client => `<option value="${client.id}" ${client.id === order?.client_id || client.id === presetClientId ? 'selected' : ''}>${esc(client.code || client.name)}</option>`).join('');
  const creating = !order && clients.length === 0;
  const lines = order?.items.length ? order.items
    : [selected ? {name: [selected.brand, selected.model].filter(Boolean).join(' '), unit_price: selected.price} : {}];
  const line = ({name = '', supplier = '', quantity = 1, unit_price = ''} = {}) => `<div class="form-fields order-line" data-order-item data-supplier="${esc(supplier)}">
    <div class="field line-supplier">
      <span class="field-label">Поставщик *</span>
      <select name="item_supplier" required>
        <option value="">Выберите поставщика</option>${supplierOptions}<option value="__other">Другой…</option>
      </select>
      <input name="item_supplier_other" maxlength="120" placeholder="Название поставщика" value="${esc(!suppliers.includes(supplier) && supplier ? supplier : '')}">
    </div>
    <label class="field">Наименование *<input name="item_name" maxlength="300" value="${esc(name)}" required placeholder="Например: Bridgestone Blizzak 255/45 R20"></label>
    <label class="field">Количество<input type="number" name="quantity" min="1" max="999" value="${esc(quantity)}" required></label>
    <label class="field">Цена за штуку, ₽<input type="number" name="unit_price" inputmode="decimal" min="0" step="0.01" value="${esc(unit_price)}"></label>
    <button type="button" class="line-remove" data-remove-item aria-label="Удалить позицию">×</button>
    <p class="order-line-sum" data-line-sum></p>
  </div>`;
  host.innerHTML = `<form class="modal order-form" id="orderForm">
    <div class="form-heading">
      <h2>${order ? `Заказ №${order.id}` : 'Новый заказ'}</h2>
      ${order?.created_at ? `<span class="eyebrow">от ${esc(shortDate(order.created_at))}</span>` : ''}
    </div>
    <div class="form-fields">
      <div class="field full client-picker">
        <span class="field-label">Клиент *</span>
        <div class="segmented" role="group" aria-label="Клиент заказа">
          <button type="button" data-client-mode="existing" aria-pressed="${!creating}">Из списка</button>
          <button type="button" data-client-mode="new" aria-pressed="${creating}">Новый клиент</button>
        </div>
        <div class="client-existing" data-client-existing>
          <select name="client_id" aria-label="Клиент"><option value="">Выберите клиента</option>${clientOptions}</select>
          <button type="button" class="ghost-action" data-open-client>Профиль ↗</button>
        </div>
        <fieldset class="form-fields client-fields" data-client-new ${creating ? '' : 'hidden disabled'}><legend>Новый клиент</legend>${clientFields()}</fieldset>
      </div>
      <fieldset class="field full status-field">
        <legend>Статус</legend>
        <div class="segmented">${Object.entries(orderStatus).map(([value, label]) =>
          `<label class="tire-season-choice"><input type="radio" name="status" value="${value}" ${(order?.status || 'in_transit') === value ? 'checked' : ''}><span>${label}</span></label>`).join('')}</div>
      </fieldset>
      <div class="full order-items" data-order-items>${lines.map(line).join('')}</div>
      <div class="full"><button type="button" class="ghost-action" data-add-item>+ Позиция</button></div>
      <label class="field full">Комментарий<textarea name="comment" rows="2" maxlength="2000" placeholder="Например: предоплата 5 000 ₽, звонить перед приездом">${esc(order?.comment ?? '')}</textarea></label>
      <label class="field">Сумма заказа, ₽ *<input name="total_amount" type="number" inputmode="decimal" min="0" step="0.01" value="${esc(order?.total_amount ?? '')}" required></label>
      <label class="field">Задаток, ₽<input name="deposit" type="number" inputmode="decimal" min="0" step="0.01" value="${esc(order?.deposit ?? '5000')}" required></label>
      <div class="calc-line full"><span>Остаток</span><strong id="remainder">0 ₽</strong></div>
    </div>
    <p class="form-error" role="alert" hidden></p>
    <div class="form-actions"><button type="button" class="ghost-action" data-close-order>Отмена</button>
      <button type="submit" class="primary-action" ${order && !canEditBranch(order.branch_id) ? 'disabled title="Только просмотр"' : ''}>${order ? 'Сохранить изменения' : 'Создать заказ'}</button></div>
  </form>`;
  const form = host.querySelector('form');
  const controls = form.elements;
  const itemsHost = form.querySelector('[data-order-items]');
  const applySupplier = row => {
    const supplier = row.dataset.supplier || '';
    const select = row.querySelector('[name=item_supplier]');
    const other = row.querySelector('[name=item_supplier_other]');
    if (supplier && !suppliers.includes(supplier)) {
      select.value = '__other';
      other.hidden = other.disabled = false;
      other.required = true;
    } else {
      select.value = supplier;
      other.hidden = other.disabled = true;
      other.required = false;
      other.value = '';
    }
  };
  for (const row of form.querySelectorAll('[data-order-item]')) applySupplier(row);
  const recalc = () => {
    let total = 0;
    for (const row of form.querySelectorAll('[data-order-item]')) {
      const quantity = Number(row.querySelector('[name=quantity]').value) || 0;
      const price = Number(row.querySelector('[name=unit_price]').value) || 0;
      const sum = quantity * price;
      total += sum;
      row.querySelector('[data-line-sum]').textContent = sum ? `${money(sum)} ₽` : '';
    }
    if (!controls.total_amount.dataset.manual) controls.total_amount.value = total ? total.toFixed(2) : '';
    const deposit = Number(controls.deposit.value) || 0;
    form.querySelector('#remainder').textContent = `${money(Math.max(0, (Number(controls.total_amount.value) || 0) - deposit))} ₽`;
  };
  controls.total_amount.oninput = () => { controls.total_amount.dataset.manual = controls.total_amount.value === '' ? '' : 'true'; };
  controls.deposit.oninput = recalc;
  itemsHost.addEventListener('input', event => {
    if (event.target.name === 'quantity' || event.target.name === 'unit_price') recalc();
  });
  itemsHost.addEventListener('change', event => {
    if (event.target.name === 'item_supplier') {
      const row = event.target.closest('[data-order-item]');
      const other = row.querySelector('[name=item_supplier_other]');
      const custom = event.target.value === '__other';
      other.hidden = other.disabled = !custom;
      other.required = custom;
      if (!custom) other.value = '';
      else other.focus();
    }
  });
  itemsHost.addEventListener('click', event => {
    const remove = event.target.closest('[data-remove-item]');
    if (!remove) return;
    const row = remove.closest('[data-order-item]');
    if (form.querySelectorAll('[data-order-item]').length === 1) {
      row.insertAdjacentHTML('afterend', line());
      row.remove();
      applySupplier(itemsHost.lastElementChild);
      itemsHost.lastElementChild.querySelector('[name=item_name]')?.focus();
    } else row.remove();
    recalc();
  });
  form.querySelector('[data-add-item]').onclick = () => {
    itemsHost.insertAdjacentHTML('beforeend', line());
    applySupplier(itemsHost.lastElementChild);
    itemsHost.lastElementChild.querySelector('[name=item_name]').focus();
  };
  form.querySelector('[data-open-client]').onclick = () => {
    const client = clients.find(item => item.id === Number(controls.client_id.value));
    if (client) showClientCard(client, revision, clients);
    else message('Сначала выберите клиента из списка.');
  };
  form.querySelector('[data-close-order]').onclick = () => host.replaceChildren();

  const modeButtons = form.querySelectorAll('[data-client-mode]');
  const existing = form.querySelector('[data-client-existing]');
  const newClient = form.querySelector('[data-client-new]');
  const switchClient = mode => {
    for (const button of modeButtons) button.setAttribute('aria-pressed', String(button.dataset.clientMode === mode));
    existing.hidden = controls.client_id.disabled = mode === 'new';
    newClient.hidden = newClient.disabled = mode !== 'new';
    controls.client_id.required = mode !== 'new';
  };
  modeButtons.forEach(button => { button.onclick = () => switchClient(button.dataset.clientMode); });
  switchClient(creating ? 'new' : 'existing');
  recalc();
  form.onsubmit = event => {
    event.preventDefault();
    const values = new FormData(form);
    const creatingNow = newClient.hidden === false;
    const items = [...form.querySelectorAll('[data-order-item]')].map(row => {
      const select = row.querySelector('[name=item_supplier]');
      const supplier = select.value === '__other' ? row.querySelector('[name=item_supplier_other]').value.trim() : select.value;
      const price = row.querySelector('[name=unit_price]').value;
      return {name: row.querySelector('[name=item_name]').value.trim(), supplier,
        quantity: Number(row.querySelector('[name=quantity]').value), unit_price: price || '0'};
    });
    const payload = {
      ...(creatingNow ? {new_client: readClient(values)} : {client_id: Number(values.get('client_id'))}),
      comment: values.get('comment').trim(),
      total_amount: values.get('total_amount'),
      deposit: values.get('deposit'),
      status: values.get('status'),
      items
    };
    submitWorkspaceForm(form, revision, order ? `/orders/${order.id}` : '/orders', payload,
      order ? 'Изменения сохранены.' : (creatingNow ? 'Заказ и клиент созданы.' : 'Заказ создан.'), order ? 'PUT' : 'POST');
  };
  if (!order) controls.client_id.focus();
}

function loginView(){
  document.querySelector('.role-switch').innerHTML = '<span class="login-hint">Войдите с рабочим логином сотрудника</span>';
  document.querySelector('.employee-tabs').innerHTML = '';
  employeeContent.innerHTML = `<form id="loginForm" class="modal visible">
    <h4>Вход для сотрудников</h4>
    <div class="form-fields">
      <div class="field full"><label>Логин</label><input name="login" autocomplete="username" required></div>
      <div class="field full"><label>Пароль</label><input name="password" type="password" autocomplete="current-password" required></div>
    </div>
    <p class="form-error" role="alert" hidden></p>
    <div class="form-actions"><button class="primary-action">Войти</button></div>
  </form>`;
  loginForm.onsubmit = login;
  loginForm.elements.login.focus();
}
async function login(e){
  e.preventDefault();
  const form = e.currentTarget;
  const f = new FormData(form);
  const errorBox = form.querySelector('.form-error');
  try{
    const r = await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({username:f.get('login'),password:f.get('password')})});
    const d = await r.json();
    if(!r.ok) throw Error(d.detail||'Не удалось войти');
    state.user = {...d.user, token: d.access_token};
    localStorage.setItem('alauto_session', JSON.stringify(state.user));
    workspace();
  } catch(err){
    message(err.message);
    if (errorBox && form.isConnected) { errorBox.textContent = err.message; errorBox.hidden = false; }
  }
}
async function inventoryView(){employeeContent.innerHTML='<div class="workspace-header"><div><h3>Номенклатура</h3><p>Excel сначала проходит предварительную проверку.</p></div><button class="primary-action" id="addProduct">+ Товар</button></div><div id="formHost"></div><div class="upload-zone"><strong>Импорт из Excel</strong>Выберите .xlsx: данные не будут записаны до подтверждения.<br><input type="file" accept=".xlsx,.xlsm" id="excelImport"></div><div id="importResult"></div>';addProduct.onclick=productForm;excelImport.onchange=previewImport}
function productForm(){formHost.innerHTML='<form class="modal visible" id="productForm"><h4>Новый товар</h4><div class="form-fields"><div class="field"><label>Тип</label><select name="type" id="productType"><option value="tire">Шина</option><option value="wheel">Диск</option></select></div><div class="field"><label>Бренд *</label><input name="brand" required></div><div class="field"><label>Модель *</label><input name="model" required></div><div class="field"><label>Цена, ₽ *</label><input name="price" type="number" min="0" required></div><div class="field"><label>Остаток *</label><input name="stock" type="number" min="0" required></div><div class="field"><label id="specALabel">Ширина *</label><input name="a" required></div><div class="field"><label id="specBLabel">Профиль *</label><input name="b" required></div><div class="field"><label id="specCLabel">Диаметр *</label><input name="c" required></div></div><p class="notice" id="productHint">Шина будет добавлена как летняя с индексом нагрузки «—». Для полного набора характеристик используйте Excel.</p><div class="form-actions"><button class="primary-action">Сохранить</button></div></form>';const f=document.getElementById('productForm'),update=()=>{const tire=f.type.value==='tire';specALabel.textContent=tire?'Ширина *':'Диаметр *';specBLabel.textContent=tire?'Профиль *':'Разболтовка *';specCLabel.textContent=tire?'Диаметр *':'Цвет *';productHint.textContent=tire?'Шина будет добавлена как летняя с индексом нагрузки «—». Для полного набора характеристик используйте Excel.':'Для диска ширина 7J, ЦО 66.1 и ET 35 указываются по умолчанию; полный набор характеристик можно загрузить Excel.'};f.type.onchange=update;f.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(f)),tire=d.type==='tire',payload={type:d.type,brand:d.brand,model:d.model,price:+d.price,stock:+d.stock,[tire?'tire':'wheel']:tire?{width:+d.a,profile:+d.b,diameter:+d.c,season:'Лето',load_index:'—'}:{diameter:+d.a,bolt_pattern:d.b,width:7,center_bore:66.1,et:35,color:d.c}};try{await api('/products',{method:'POST',body:JSON.stringify(payload)});message('Товар добавлен.','success');inventoryView();loadCatalog()}catch(x){message(x.message)}}}
async function previewImport(e) {
  const file = e.target.files[0];
  state.importRows = [];
  if (!file) return;
  importResult.innerHTML = '<p class="notice">Проверяем файл…</p>';
  try {
    const form = new FormData();
    form.append('file', file);
    const preview = await api('/import/products/preview', {method:'POST', body:form});
    state.importRows = preview.valid_rows;
    const rows = preview.valid_rows.map(({row, data:p, source_price}) => {
      const s = p.wheel || p.tire;
      return `<tr><td>${row}</td><td>${esc(p.model)}</td><td>${s.diameter}</td><td>${esc(s.bolt_pattern || '—')}</td><td>${esc(s.width)}</td><td>${esc(s.center_bore ?? '—')}</td><td>${esc(s.et ?? '—')}</td><td>${esc(s.color ?? '—')}</td><td>${money(source_price)}</td><td>${money(p.price)}</td></tr>`;
    }).join('');
    importResult.innerHTML = `<p class="notice">Готово к импорту: ${preview.valid_rows.length}. Ошибки: ${preview.errors.length}. Наценка: 25% к цене Excel, округление до копеек. В каталог попадёт продажная цена.</p>
      ${preview.errors.length ? `<ul class="import-errors">${preview.errors.map(x=>`<li>Строка ${x.row}: ${esc(x.message)}</li>`).join('')}</ul>` : ''}
      ${rows ? `<div style="overflow:auto;max-height:420px"><table class="data-table"><thead><tr><th>Строка</th><th>Модель</th><th>Диаметр</th><th>PCD</th><th>Ширина</th><th>ЦО</th><th>ET</th><th>Цвет</th><th>Excel, ₽</th><th>Продажа, ₽</th></tr></thead><tbody>${rows}</tbody></table></div><button class="primary-action" id="confirmImport">Подтвердить импорт с наценкой 25%</button>` : ''}`;
    document.getElementById('confirmImport')?.addEventListener('click', confirmImport);
  } catch (error) {
    importResult.innerHTML = `<p class="notice">${esc(error.message)}</p>`;
  }
}
async function confirmImport(){try{await api('/import/products/confirm',{method:'POST',body:JSON.stringify({rows:state.importRows})});state.importRows=[];message('Импорт подтверждён.','success');inventoryView();loadCatalog()}catch(e){message(e.message)}}
async function mailingsView(){try{const rows=await api('/mailings');employeeContent.innerHTML=`<div class="workspace-header"><div><h3>Рассылки</h3><p>Сохраняются только черновики.</p></div></div><form id="mailingForm" class="mailing-card"><div class="field"><label>Тема</label><input name="subject" required></div><div class="field" style="margin-top:12px"><label>Текст</label><textarea name="text" required></textarea></div><div class="form-actions"><button class="primary-action">Сохранить черновик</button></div></form>${rows.length?`<table class="data-table"><tbody>${rows.map(m=>`<tr><td>${esc(m.subject)}</td><td>${esc(m.status)}</td></tr>`).join('')}</tbody></table>`:'<p class="empty-state">Черновиков пока нет.</p>'}`;mailingForm.onsubmit=async e=>{e.preventDefault();try{await api('/mailings',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(e.currentTarget)))});message('Черновик сохранён.','success');mailingsView()}catch(x){message(x.message)}}}catch(e){employeeContent.innerHTML=`<p class="empty-state">${esc(e.message)}</p>`}}
function openDrawer(tab = 'orders', product = null) {
  state.tab = tab;
  state.selected = product;
  toggleDrawer(true);
  state.user ? workspace() : loginView();
}
try { state.user = JSON.parse(localStorage.getItem('alauto_session')); } catch (_) { state.user = null; }
document.querySelectorAll('.nav-link[data-view]').forEach(button => {
  button.onclick = () => switchView(button.dataset.view);
});
filterForm.addEventListener('input', updateFilterButton);
filterForm.onsubmit = event => {
  event.preventDefault();
  if (showProducts.disabled) return;
  loadCatalog();
  productGrid.scrollIntoView({behavior:'smooth', block:'start'});
};
filterForm.onreset = () => setTimeout(() => {
  for (const picker of filterForm.querySelectorAll('.tire-size-picker[open]')) picker.open = false;
  wheelFit.refresh();
  updateFilterButton();
  loadCatalog();
});
employeeEntry.onclick = () => openDrawer();
closeDrawer.onclick = () => toggleDrawer(false);
document.getElementById('workspaceBrand').onclick = () => toggleDrawer(false);
renderFilters();
loadCatalog();





















