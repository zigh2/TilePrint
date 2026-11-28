'use strict';
/* TilePrint UI — talks to the Python back-end through window.pywebview.api (desktop) or a
   token-protected local HTTP API (browser mode). All geometry coming from Python is in PDF points. */
(() => {
const TP = window.TP = { ready: false };

// ============================================================ i18n
const I18N = {
en: {
  undo: 'Undo', redo: 'Redo', theme: 'Toggle theme', language: 'Language', open: 'Open', project: 'Project',
  saveProject: 'Save project…', saveProjectD: 'Settings and source path, to continue later',
  openProject: 'Open project…', openProjectD: 'Pick up where you left off',
  exportTiled: 'Export tiled PDF', moreExports: 'More export options', exportFull: 'Export full-size PDF',
  secSource: 'Source', change: 'Change', unit: 'Units',
  sheetFit: 'Fit each sheet on one page', sheetFitD: 'Whole table on one page (skipped if it has charts)',
  secSize: 'Final size', size: 'Size', orientation: 'Orientation', width: 'Width', height: 'Height',
  keepRatio: 'Keep source proportions', scaling: 'Scaling', resetPos: 'Reset position',
  secPaper: 'Printer paper', paper: 'Paper', margin: 'Margin', header: 'Arrow band', overlap: 'Overlap',
  numbering: 'Page numbering', secOpts: 'Sheet details',
  overlapHint0: 'Overlap 0: cut each sheet on its frame line and glue the sheets edge to edge. Nothing is repeated.',
  overlapHintN: 'Each sheet repeats this much of its neighbour, so you can overlap and glue. Use 0 to cut on the frame and glue edge to edge.',
  smartCut: 'Smart cut', smartCutD: 'Moves sheet edges onto empty space so content is not sliced',
  skipBlank: 'Skip blank sheets', skipBlankD: 'Saves paper; the arrows skip them too',
  cropMarks: 'Crop marks', cropMarksD: 'Corner ticks outside the frame',
  ticks: 'Overlap ticks', ticksD: 'Margin ticks where the next sheet starts; nothing inside the frame',
  footerSw: 'Footer', footerD: 'Name, page, date and scale',
  scaleBar: 'Real-size ruler', scaleBarD: 'A 5 cm / 2 in bar to check the print scale',
  blankBacks: 'Duplex printer', blankBacksD: 'Adds a blank back to every sheet',
  footerName: 'Footer name', footerPlaceholder: 'File name',
  emptyTitle: 'Print anything at any size',
  emptyText: 'Drop a PDF, image or spreadsheet. TilePrint splits it into sheets to print and glue, and vectors stay vector.',
  chooseFile: 'Choose a file…', f1t: 'Stays vector', f1d: 'Text and lines never turn into pixels.',
  f2t: 'Neighbour arrows', f2d: 'Page numbers point to the adjacent sheets.', f3t: 'Smart cuts', f3d: 'Edges avoid slicing your content.',
  hint: 'Drag content to move · scroll to zoom · double-click a sheet to preview',
  zoomOut: 'Zoom out', zoomIn: 'Zoom in', fit: 'Fit to window',
  gridIsCuts: 'Grid: one cut line per boundary (click for sheet frames)',
  gridIsSheets: 'Grid: every sheet frame, overlaps visible (click for cut lines)',
  o_unit_mm: 'mm', o_unit_cm: 'cm', o_unit_in: 'in',
  o_poster_orient_auto: 'Auto', o_poster_orient_portrait: 'Portrait', o_poster_orient_landscape: 'Landscape',
  o_paper_orient_auto: 'Auto', o_paper_orient_portrait: 'Portrait', o_paper_orient_landscape: 'Landscape',
  o_scale_mode_fit: 'Fit', o_scale_mode_fill: 'Fill', o_scale_mode_stretch: 'Stretch',
  o_numbering_seq: '1 · 2 · 3', o_numbering_rc: 'A1 · B2',
  custom: 'Custom…', gA: 'ISO A', gB: 'ISO B', gUS: 'US and architectural',
  sheetsWord: 'sheets', chipPrint: '{p} to print', pages: '{n} pages', page1: '1 page',
  dpiOk: 'Image resolution: {d} DPI', dpiLow: 'Low resolution: {d} DPI',
  dpiLowD: 'Prints soft below about 150 DPI. Use a smaller size or a sharper image.',
  notFitted: 'This workbook has charts or images, so it was converted as-is, not fitted to one page.',
  saved: 'PDF saved', showFolder: 'Show in folder', error: 'Something went wrong', opening: 'Opening…',
  writing: 'Writing PDF…', sheetsDone: '{done} of {total} sheets', projSaved: 'Project saved',
  downloadStarted: 'Download started', tooBig: 'Too large for a single PDF page (max 200 in). Use the tiled export.',
  sheetTitle: 'Sheet {label}', sheetSub: 'row {r} · col {c} · {n} of {total}',
  tileInfo: 'Sheet {label} · row {r}, col {c}', preview: 'Preview', skippedTile: 'Skipped (blank)',
  tiledD: '{p} sheets · {paper}', fullD: '{w} × {h} {u} · one page', landscape: 'landscape', portrait: 'portrait',
  noFile: 'Open a file first', dropHere: 'Drop to open', dropFail: 'Use Open to choose the file.',
},
ar: {
  undo: 'تراجع', redo: 'إعادة', theme: 'تبديل المظهر', language: 'اللغة', open: 'فتح', project: 'المشروع',
  saveProject: 'حفظ المشروع…', saveProjectD: 'الإعدادات ومسار المصدر لإكمال العمل لاحقاً',
  openProject: 'فتح مشروع…', openProjectD: 'تابع من حيث توقفت',
  exportTiled: 'تصدير PDF مجزأ', moreExports: 'خيارات تصدير أخرى', exportFull: 'تصدير PDF بالمقاس الكامل',
  secSource: 'المصدر', change: 'تغيير', unit: 'الوحدات',
  sheetFit: 'ملاءمة كل ورقة عمل في صفحة', sheetFitD: 'الجدول كاملاً في صفحة واحدة (يُتجاوز إن وُجدت مخططات)',
  secSize: 'المقاس النهائي', size: 'المقاس', orientation: 'الاتجاه', width: 'العرض', height: 'الارتفاع',
  keepRatio: 'إبقاء نسبة المصدر', scaling: 'التحجيم', resetPos: 'إعادة الموضع',
  secPaper: 'ورق الطباعة', paper: 'الورق', margin: 'الهامش', header: 'شريط الأسهم', overlap: 'التداخل',
  numbering: 'ترقيم الصفحات', secOpts: 'تفاصيل الأوراق',
  overlapHint0: 'التداخل 0: قصّ كل ورقة على خط إطارها وألصق الأوراق جنباً إلى جنب. لا يتكرر أي جزء من الصورة.',
  overlapHintN: 'كل ورقة تكرر هذا المقدار من جارتها لتتداخل وتُلصق. استخدم 0 للقص على الإطار واللصق جنباً إلى جنب.',
  smartCut: 'قص ذكي', smartCutD: 'ينقل حواف الأوراق إلى مساحات فارغة حتى لا يُقطع المحتوى',
  skipBlank: 'تخطي الأوراق الفارغة', skipBlankD: 'يوفر الورق وتتجاوزها الأسهم أيضاً',
  cropMarks: 'علامات القص', cropMarksD: 'علامات في زوايا الإطار من الخارج',
  ticks: 'علامات التداخل', ticksD: 'علامات في الهامش تبين بداية الورقة التالية ولا شيء داخل الإطار',
  footerSw: 'تذييل', footerD: 'الاسم والصفحة والتاريخ والمقياس',
  scaleBar: 'مسطرة بالمقاس الفعلي', scaleBarD: 'شريط 5 سم أو 2 إنش للتحقق من مقياس الطباعة',
  blankBacks: 'طابعة وجهين', blankBacksD: 'تضيف ظهراً فارغاً لكل ورقة',
  footerName: 'اسم التذييل', footerPlaceholder: 'اسم الملف',
  emptyTitle: 'اطبع أي شيء بأي حجم',
  emptyText: 'أسقط ملف PDF أو صورة أو جدولاً. يقسمه TilePrint إلى أوراق للطباعة واللصق، ويبقى المتجهي متجهياً.',
  chooseFile: 'اختر ملفاً…', f1t: 'يبقى متجهياً', f1d: 'النص والخطوط لا تتحول إلى نقاط.',
  f2t: 'أسهم الأوراق المجاورة', f2d: 'أرقام الصفحات المجاورة بالأسهم.', f3t: 'قص ذكي', f3d: 'الحواف لا تقطع المحتوى.',
  hint: 'اسحب المحتوى لتحريكه · العجلة للتكبير · انقر مرتين على ورقة لمعاينتها',
  zoomOut: 'تصغير', zoomIn: 'تكبير', fit: 'ملاءمة النافذة',
  gridIsCuts: 'الشبكة: خط قص واحد لكل حد (انقر لعرض إطار كل ورقة)',
  gridIsSheets: 'الشبكة: إطار كل ورقة مع التداخل (انقر لعرض خطوط القص)',
  o_unit_mm: 'مم', o_unit_cm: 'سم', o_unit_in: 'إنش',
  o_poster_orient_auto: 'تلقائي', o_poster_orient_portrait: 'طولي', o_poster_orient_landscape: 'عرضي',
  o_paper_orient_auto: 'تلقائي', o_paper_orient_portrait: 'طولي', o_paper_orient_landscape: 'عرضي',
  o_scale_mode_fit: 'ملاءمة', o_scale_mode_fill: 'ملء', o_scale_mode_stretch: 'تمديد',
  o_numbering_seq: '1 · 2 · 3', o_numbering_rc: 'A1 · B2',
  custom: 'مخصص…', gA: 'ISO A', gB: 'ISO B', gUS: 'أمريكي ومعماري',
  sheetsWord: 'ورقة', chipPrint: '{p} للطباعة', pages: '{n} صفحات', page1: 'صفحة واحدة',
  dpiOk: 'دقة الصورة: {d} DPI', dpiLow: 'دقة منخفضة: {d} DPI',
  dpiLowD: 'تظهر الطباعة ضبابية تحت نحو 150 DPI. اختر مقاساً أصغر أو صورة أوضح.',
  notFitted: 'يحتوي الملف مخططات أو صوراً، لذا حُوّل كما هو دون ملاءمته لصفحة واحدة.',
  saved: 'تم حفظ الـ PDF', showFolder: 'إظهار في المجلد', error: 'حدث خطأ', opening: 'جارٍ الفتح…',
  writing: 'جارٍ كتابة الملف…', sheetsDone: '{done} من {total} ورقة', projSaved: 'تم حفظ المشروع',
  downloadStarted: 'بدأ التنزيل', tooBig: 'أكبر من أن يكون صفحة PDF واحدة (الحد 200 إنش). استخدم التصدير المجزأ.',
  sheetTitle: 'الورقة {label}', sheetSub: 'صف {r} · عمود {c} · {n} من {total}',
  tileInfo: 'الورقة {label} · صف {r}، عمود {c}', preview: 'معاينة', skippedTile: 'متخطاة (فارغة)',
  tiledD: '{p} ورقة · {paper}', fullD: '{w} × {h} {u} · صفحة واحدة', landscape: 'عرضي', portrait: 'طولي',
  noFile: 'افتح ملفاً أولاً', dropHere: 'أفلت الملف لفتحه', dropFail: 'استخدم زر «فتح» لاختيار الملف.',
},
};
const SEGS = { unit: ['mm', 'cm', 'in'], poster_orient: ['auto', 'portrait', 'landscape'], paper_orient: ['auto', 'portrait', 'landscape'],
               scale_mode: ['fit', 'fill', 'stretch'], numbering: ['seq', 'rc'] };
const PT = { mm: 72 / 25.4, cm: 72 / 2.54, in: 72 };
const DEC = { mm: 1, cm: 2, in: 2 };
const STEP = { mm: 1, cm: 0.1, in: 0.05 };

let lang = 'en';
const t = (k, v) => {
  let s = (I18N[lang] && I18N[lang][k]) ?? I18N.en[k] ?? k;
  if (v) for (const x in v) s = s.split('{' + x + '}').join(v[x]);
  return s;
};
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const store = { get: k => { try { return localStorage.getItem(k); } catch { return null; } },
                set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } } };

// ============================================================ back-end bridge
const token = (document.querySelector('meta[name="tp-token"]') || {}).content || null;
async function call(method, ...args) {
  try {
    if (window.pywebview && window.pywebview.api) return await window.pywebview.api[method](...args);
    const r = await fetch('/api/' + method, { method: 'POST', headers: { 'X-TP-Token': token || '', 'Content-Type': 'application/json' },
                                              body: JSON.stringify(args) });
    return await r.json();
  } catch (e) { return { ok: false, error: String(e) }; }
}

// ============================================================ state
let S = null, INIT = null;
let base = null, baseKey = '', region = null, rev = 0, lastPoster = '';
let view = { s: 1, tx: 0, ty: 0 }, fitS = 1;
let selected = null, hover = null, drag = null, spaceDown = false, panning = null;
let accent = '#2b62f0', dark = false;
let gridMode = (store.get('tp-grid') === 'sheets') ? 'sheets' : 'cuts';

const ltr = s => `<bdi dir="ltr">${s}</bdi>`;
const unit = () => (S && S.settings.unit) || 'mm';
const toU = pt => pt / PT[unit()];
const fromU = v => v * PT[unit()];
const fmtLen = (pt, u = unit()) => { const v = pt / PT[u]; return (Math.round(v * Math.pow(10, DEC[u])) / Math.pow(10, DEC[u])).toString(); };

// ============================================================ toasts / busy
function toast(kind, title, text, action) {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  const icon = kind === 'ok' ? 'check' : kind === 'bad' ? 'alert' : 'info';
  el.innerHTML = `<svg class="ic"><use href="#i-${icon}"/></svg><div><b></b><span></span></div>`;
  $('b', el).textContent = title; $('span', el).textContent = text || '';
  if (!text) $('span', el).remove();
  if (action) { const b = document.createElement('button'); b.className = 'btn sm'; b.textContent = action.label; b.onclick = () => { action.fn(); el.remove(); }; $('div', el).appendChild(b); }
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), kind === 'bad' ? 9000 : 6500);
}
const busy = (title, text, pct) => {
  $('#busy').hidden = false; $('#busyTitle').textContent = title; $('#busyText').textContent = text || '';
  const bar = $('#busyBar');
  if (pct == null) { bar.style.width = '38%'; bar.style.animation = 'indet 1.1s ease-in-out infinite'; }
  else { bar.style.animation = 'none'; bar.style.marginInlineStart = '0'; bar.style.width = pct + '%'; }
};
const unbusy = () => { $('#busy').hidden = true; };

// ============================================================ theme / language
function applyTheme(mode) {
  if (!mode) mode = store.get('tp-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.dataset.theme = mode; store.set('tp-theme', mode);
  dark = mode === 'dark';
  $('#themeUse').setAttribute('href', dark ? '#i-sun' : '#i-moon');
  accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || accent;
  draw();
}
function applyLang(l, notify) {
  lang = l || store.get('tp-lang') || 'en';
  if (!I18N[lang]) lang = 'en';
  store.set('tp-lang', lang);
  const root = document.documentElement; root.lang = lang; root.dir = lang === 'ar' ? 'rtl' : 'ltr';
  $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  $$('[data-i18n-title]').forEach(el => { el.title = t(el.dataset.i18nTitle); });
  $('#langLabel').textContent = lang === 'ar' ? 'English' : 'العربية';
  $('#footerText').placeholder = t('footerPlaceholder');
  buildSegs(); buildSelects();
  if (S) { syncUI(); }
  if (notify) call('update', { language: lang });
}

// ============================================================ controls
function buildSegs() {
  $$('.seg[data-seg]').forEach(seg => {
    const key = seg.dataset.seg; seg.innerHTML = '';
    SEGS[key].forEach(v => {
      const b = document.createElement('button'); b.type = 'button'; b.dataset.v = v;
      b.textContent = t(`o_${key}_${v}`); b.setAttribute('aria-pressed', 'false'); if (key === 'numbering') b.dir = 'ltr';
      b.onclick = () => patch({ [key]: v });
      seg.appendChild(b);
    });
  });
}
function buildSelects() {
  if (!INIT) return;
  const opts = (withCustom) => {
    const g = (title, items) => `<optgroup label="${title}">${items.map(i =>
      `<option value="${i.name}">${i.name} — ${fmtLen(i.w_mm * PT.mm)} × ${fmtLen(i.h_mm * PT.mm)} ${unit()}</option>`).join('')}</optgroup>`;
    return g(t('gA'), INIT.presets.iso_a) + g(t('gB'), INIT.presets.iso_b) + g(t('gUS'), INIT.presets.us) +
           (withCustom ? `<option value="Custom">${t('custom')}</option>` : '');
  };
  const pv = $('#preset').value, pp = $('#paper').value;
  $('#preset').innerHTML = opts(true); $('#paper').innerHTML = opts(false);
  if (pv) $('#preset').value = pv; if (pp) $('#paper').value = pp;
}
function buildNums() {
  $$('.num[data-num]').forEach(n => {
    const key = n.dataset.num;
    n.innerHTML = `<input inputmode="decimal" autocomplete="off" spellcheck="false"><span class="u"></span>
      <div class="st"><button type="button" tabindex="-1"><svg class="ic sm" style="width:11px;height:11px"><use href="#i-chev-up"/></svg></button>
      <button type="button" tabindex="-1"><svg class="ic sm" style="width:11px;height:11px"><use href="#i-chev"/></svg></button></div>`;
    const inp = $('input', n), [up, dn] = $$('button', n);
    const commit = (valU) => { if (!isFinite(valU)) { syncUI(); return; } patch({ [key]: fromU(Math.max(valU, +n.dataset.min || 0)) }); };
    const parse = s => parseFloat(s.replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d)).replace('٫', '.').replace(',', '.'));
    inp.addEventListener('change', () => commit(parse(inp.value)));
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') { inp.blur(); }
      else if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); bump(e.key === 'ArrowUp' ? 1 : -1, e.shiftKey); }
    });
    const bump = (dir, big) => commit(parse(inp.value) + dir * STEP[unit()] * (big ? 10 : 1));
    up.onclick = e => bump(1, e.shiftKey); dn.onclick = e => bump(-1, e.shiftKey);
  });
}
function wireControls() {
  $$('input[data-sw]').forEach(i => i.addEventListener('change', () => patch({ [i.dataset.sw]: i.checked })));
  $('#preset').onchange = e => patch({ poster_preset: e.target.value });
  $('#paper').onchange = e => patch({ paper: e.target.value });
  $('#lock').onclick = () => patch({ lock_aspect: !S.settings.lock_aspect });
  let ft; $('#footerText').addEventListener('input', e => { clearTimeout(ft); ft = setTimeout(() => patch({ footer_text: e.target.value }), 350); });
  $('#bReset').onclick = async () => apply(await call('reset_position'));
  $('#bUndo').onclick = undo; $('#bRedo').onclick = redo;
  $('#bOpen').onclick = $('#bOpen2').onclick = $('#bChange').onclick = pickFile;
  $('#bTheme').onclick = () => applyTheme(dark ? 'light' : 'dark');
  $('#bLang').onclick = () => applyLang(lang === 'ar' ? 'en' : 'ar', true);
  $('#pPrev').onclick = async () => apply(await call('set_page', S.source.page_index - 1), { fit: true });
  $('#pNext').onclick = async () => apply(await call('set_page', S.source.page_index + 1), { fit: true });
  // menus
  const menus = [['bProject', 'projectMenu'], ['bExportMenu', 'exportMenu']];
  menus.forEach(([b, m]) => { $('#' + b).onclick = e => { e.stopPropagation(); const open = !$('#' + m).hidden; closeMenus(); $('#' + m).hidden = open; }; });
  document.addEventListener('click', closeMenus);
  $('#bExport').onclick = () => doExport('tiled');
  $('#mTiled').onclick = () => doExport('tiled'); $('#mFull').onclick = () => doExport('full');
  $('#mSaveProject').onclick = saveProject; $('#mOpenProject').onclick = openProject;
  // zoom
  $('#zGrid').onclick = () => { gridMode = gridMode === 'cuts' ? 'sheets' : 'cuts'; store.set('tp-grid', gridMode); syncGridBtn(); draw(); };
  $('#zIn').onclick = () => zoomAt(cx(), cy(), 1.3); $('#zOut').onclick = () => zoomAt(cx(), cy(), 1 / 1.3); $('#zFit').onclick = () => { fit(); };
  // modal
  $('#smClose').onclick = closeSheet; $('#sheetModal').onclick = e => { if (e.target.id === 'sheetModal') closeSheet(); };
  $$('#smNav [data-nav]').forEach(b => b.onclick = () => { const tile = tileByNumber(sheetNo); if (tile && tile.nb[b.dataset.nav]) openSheet(tile.nb[b.dataset.nav]); });
}
const closeMenus = () => { $('#projectMenu').hidden = true; $('#exportMenu').hidden = true; };

// ============================================================ state application
async function patch(obj) {
  if (!S) return;
  const r = await call('update', obj);
  apply(r);
  if (r.error) toast('bad', t('error'), r.error);
}
async function undo() { apply(await call('undo')); }
async function redo() { apply(await call('redo')); }

function apply(st, opts = {}) {
  if (!st || st.ok === false) { if (st && st.error) toast('bad', t('error'), st.error); return; }
  const prevPlacement = S && S.job ? JSON.stringify(S.job.placement) + S.job.poster.join() : '';
  S = st;
  const src = S.source, j = S.job;
  const key = src ? src.path + '#' + src.page_index : '';
  if (key !== baseKey) { baseKey = key; base = null; region = null; rev++; loadBase(key); }
  const placement = j ? JSON.stringify(j.placement) + j.poster.join() : '';
  if (placement !== prevPlacement) { rev++; region = null; }
  if (j) {
    const sig = j.poster.map(Math.round).join('x');
    if (opts.fit || sig !== lastPoster) { lastPoster = sig; fit(true); }
  }
  syncUI(); draw(); scheduleRegion();
}
async function loadBase(key) {
  if (!S || !S.has_source) return;
  const r = await call('preview_image', 1600);
  if (!r || !r.ok || key !== baseKey) return;
  const img = new Image();
  img.onload = () => { if (key === baseKey) { base = { img, w: r.w, h: r.h }; draw(); scheduleRegion(); } };
  img.src = r.url;
}

function syncGridBtn() {
  const b = $('#zGrid'); if (!b) return;
  b.title = t(gridMode === 'cuts' ? 'gridIsCuts' : 'gridIsSheets'); b.setAttribute('aria-pressed', String(gridMode === 'sheets'));
  $('#gridUse').setAttribute('href', gridMode === 'cuts' ? '#i-grid' : '#i-layers');
}

function syncUI() {
  if (!S) return;
  syncGridBtn();
  const s = S.settings, j = S.job, src = S.source, u = s.unit;
  $('#ver').textContent = 'v' + S.version;
  document.body.classList.toggle('has', S.has_source);
  $('#empty').hidden = S.has_source; $('#side').classList.toggle('off', !S.has_source);
  ['chips', 'zoom', 'scalebar', 'hintbar'].forEach(id => { $('#' + id).hidden = !(S.has_source && j); });
  $('#bUndo').disabled = !S.can_undo; $('#bRedo').disabled = !S.can_redo;
  $('#bExport').disabled = $('#bExportMenu').disabled = !j;
  // source card
  $('#fileChip').hidden = !src;
  if (src) {
    $('#fileChipName').textContent = src.name + (src.page_count > 1 ? `  ·  ${src.page_index + 1}/${src.page_count}` : '');
    $('#srcName').textContent = src.name; $('#srcName').title = src.path;
    $('#srcIcon').setAttribute('href', src.kind === 'image' ? '#i-image' : src.kind === 'sheet' ? '#i-table' : '#i-file');
    $('#srcMeta').innerHTML = ltr(`${fmtLen(src.size_pt[0])} × ${fmtLen(src.size_pt[1])} ${t('o_unit_' + u)}`) +
      (src.pixel_size ? ' · ' + ltr(`${src.pixel_size[0]}×${src.pixel_size[1]} px`) : '') + ' · ' + (src.page_count > 1 ? t('pages', { n: src.page_count }) : t('page1'));
    $('#pager').hidden = src.page_count < 2;
    $('#pCnt').textContent = `${src.page_index + 1} / ${src.page_count}`;
    $('#pPrev').disabled = src.page_index <= 0; $('#pNext').disabled = src.page_index >= src.page_count - 1;
    $('#rowSheetFit').hidden = src.kind !== 'sheet';
  } else { $('#srcName').textContent = '—'; $('#srcMeta').textContent = ''; $('#pager').hidden = true; $('#rowSheetFit').hidden = true; }
  // controls
  $$('.seg[data-seg]').forEach(seg => $$('button', seg).forEach(b => b.setAttribute('aria-pressed', String(s[seg.dataset.seg] === b.dataset.v))));
  $$('input[data-sw]').forEach(i => { i.checked = !!s[i.dataset.sw]; });
  const noOverlap = s.overlap < 0.01;                     // edge to edge: there is nothing to mark
  const tk = $('input[data-sw="overlap_guides"]'); tk.disabled = noOverlap; tk.closest('.switch').style.opacity = noOverlap ? .5 : 1;
  $('#overlapHint').textContent = t(noOverlap ? 'overlapHint0' : 'overlapHintN');
  if ($('#preset').dataset.unit !== u) { $('#preset').dataset.unit = u; buildSelects(); }
  $('#preset').value = s.poster_preset; $('#paper').value = s.paper;
  const custom = s.poster_preset === 'Custom';
  $('#rowCustom').hidden = !custom; $('#rowOrient').hidden = custom;
  $('#lock').setAttribute('aria-pressed', String(s.lock_aspect)); $('#lockUse').setAttribute('href', s.lock_aspect ? '#i-lock' : '#i-unlock');
  $$('.num[data-num]').forEach(n => {
    const k = n.dataset.num, inp = $('input', n);
    if (document.activeElement !== inp) inp.value = fmtLen(s[k]);
    $('.u', n).textContent = u;
  });
  if (document.activeElement !== $('#footerText')) $('#footerText').value = s.footer_text || '';
  // DPI + notes
  const box = $('#dpiBox'); box.innerHTML = '';
  if (j && j.dpi != null) {
    const low = j.dpi < 150, d = Math.round(j.dpi);
    box.hidden = false;
    box.innerHTML = `<div class="note ${low ? 'warn' : 'info'}"><svg class="ic sm" style="margin-top:2px"><use href="#i-${low ? 'alert' : 'info'}"/></svg><div><b>${t(low ? 'dpiLow' : 'dpiOk', { d: ltr(d) })}</b>${low ? '<br>' + t('dpiLowD') : ''}</div></div>`;
  } else if (src && src.notes.includes('sheet_has_charts_not_fitted')) {
    box.hidden = false; box.innerHTML = `<div class="note info"><svg class="ic sm" style="margin-top:2px"><use href="#i-info"/></svg><div>${t('notFitted')}</div></div>`;
  } else box.hidden = true;
  // chips
  const chips = $('#chips');
  if (j) {
    const landscape = j.paper[0] > j.paper[1];
    const dpiBadge = j.dpi != null ? `<span class="chip"><span class="badge ${j.dpi < 150 ? 'warn' : 'ok'}">${ltr(Math.round(j.dpi) + ' DPI')}</span></span>` : '';
    chips.innerHTML =
      `<span class="chip"><svg class="ic sm"><use href="#i-grid"/></svg><b>${ltr(j.rows + ' × ' + j.cols)}</b><span>= ${ltr(j.total)} ${t('sheetsWord')}</span></span>` +
      (j.printed !== j.total ? `<span class="chip"><svg class="ic sm"><use href="#i-fileminus"/></svg><b>${t('chipPrint', { p: ltr(j.printed) })}</b></span>` : '') +
      `<span class="chip"><svg class="ic sm"><use href="#i-maxbox"/></svg><b>${ltr(fmtLen(j.poster[0]) + ' × ' + fmtLen(j.poster[1]))}</b> ${t('o_unit_' + u)}</span>` +
      (j.uniform_scale ? `<span class="chip"><svg class="ic sm"><use href="#i-ruler"/></svg><b>${ltr('×' + j.scale.toFixed(2))}</b></span>` : '') +
      `<span class="chip"><svg class="ic sm"><use href="#i-printer"/></svg><b>${ltr(s.paper)}</b> ${t(landscape ? 'landscape' : 'portrait')}</span>` + dpiBadge;
    $('#mTiledD').textContent = t('tiledD', { p: j.printed, paper: s.paper + ' ' + t(landscape ? 'landscape' : 'portrait') });
    $('#mFullD').textContent = j.too_big_for_single_page ? t('tooBig') : t('fullD', { w: fmtLen(j.poster[0]), h: fmtLen(j.poster[1]), u: t('o_unit_' + u) });
    $('#mFull').disabled = j.too_big_for_single_page; $('#mFull').style.opacity = j.too_big_for_single_page ? .5 : 1;
  }
  updateTileChip();
}

function updateTileChip() {
  const el = $('#tilechip'), j = S && S.job;
  const tile = j && selected ? j.tiles.find(x => x.row === selected[0] && x.col === selected[1]) : null;
  if (!tile) { el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = tile.skipped
    ? `<span class="chip"><b>${t('skippedTile')}</b></span>`
    : `<span class="chip"><b>${t('tileInfo', { label: tile.label, r: tile.row + 1, c: tile.col + 1 })}</b></span><button class="btn sm" id="tcPrev"><svg class="ic sm"><use href="#i-grid"/></svg>${t('preview')}</button>`;
  const b = $('#tcPrev'); if (b) b.onclick = () => openSheet(tile.number);
}

// ============================================================ canvas
const cv = $('#cv'), ctx = cv.getContext('2d');
const stage = $('#stage');
const cx = () => stage.clientWidth / 2, cy = () => stage.clientHeight / 2;
let raf = 0, regionTimer = 0;
const queueDraw = () => { if (!raf) raf = requestAnimationFrame(draw); };

function fit(noDraw) {
  if (!S || !S.job) return;
  const [PW, PH] = S.job.poster, W = stage.clientWidth, H = stage.clientHeight, pad = Math.min(80, Math.min(W, H) * .12);
  fitS = Math.max(1e-4, Math.min((W - pad * 2) / PW, (H - pad * 2) / PH));
  view = { s: fitS, tx: (W - PW * fitS) / 2, ty: (H - PH * fitS) / 2 + 10 };
  if (!noDraw) { draw(); scheduleRegion(); }
}
function zoomAt(px, py, f) {
  const ns = Math.min(Math.max(view.s * f, fitS * .25), Math.max(fitS * 120, 12));
  f = ns / view.s;
  view.tx = px - (px - view.tx) * f; view.ty = py - (py - view.ty) * f; view.s = ns;
  draw(); scheduleRegion();
}
const toWorld = (x, y) => [(x - view.tx) / view.s, (y - view.ty) / view.s];
// middle of every overlap band: the single "cut line" between two neighbouring sheets
const cutsOf = (starts, sizes, total) => [0, ...starts.slice(1).map((s, i) => (s + starts[i] + sizes[i]) / 2), total];
// the area a sheet "owns" in the current grid mode: its own frame, or its share of the cut grid
const regionOf = j => {
  if (gridMode !== 'cuts') return t => [t.x, t.y, t.x + t.w, t.y + t.h];
  const cx = cutsOf(j.xs, j.ws, j.poster[0]), cy = cutsOf(j.ys, j.hs, j.poster[1]);
  return t => [cx[t.col], cy[t.row], cx[t.col + 1], cy[t.row + 1]];
};
function tileAt(wx, wy) {
  if (!S || !S.job) return null;
  const [PW, PH] = S.job.poster; if (wx < 0 || wy < 0 || wx > PW || wy > PH) return null;
  const reg = regionOf(S.job);
  let best = null, bd = -1;
  for (const t of S.job.tiles) {
    const r = reg(t);
    if (wx >= r[0] && wx <= r[2] && wy >= r[1] && wy <= r[3]) {
      const d = Math.min(wx - r[0], r[2] - wx, wy - r[1], r[3] - wy);
      if (d > bd) { bd = d; best = t; }
    }
  }
  return best;
}
const tileByNumber = n => S && S.job && S.job.tiles.find(t => t.number === n);
const inContent = (wx, wy) => { const p = S.job.placement; return wx >= p.x && wy >= p.y && wx <= p.x + p.w && wy <= p.y + p.h && wx >= 0 && wy >= 0 && wx <= S.job.poster[0] && wy <= S.job.poster[1]; };

function rr(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }

function draw() {
  raf = 0;
  const dpr = window.devicePixelRatio || 1, W = stage.clientWidth, H = stage.clientHeight;
  if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
  if (!S || !S.job) return;
  const j = S.job, [PW, PH] = j.poster, pl = j.placement, sc = view.s;
  ctx.save(); ctx.translate(view.tx, view.ty); ctx.scale(sc, sc);
  // paper with soft shadow
  ctx.save(); ctx.shadowColor = dark ? 'rgba(0,0,0,.7)' : 'rgba(16,24,40,.30)'; ctx.shadowBlur = 38; ctx.shadowOffsetY = 12; ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, PW, PH); ctx.restore();
  // content
  ctx.save(); ctx.beginPath(); ctx.rect(0, 0, PW, PH); ctx.clip(); ctx.imageSmoothingQuality = 'high';
  const ox = drag ? drag.dx : 0, oy = drag ? drag.dy : 0;
  if (base) ctx.drawImage(base.img, pl.x + ox, pl.y + oy, pl.w, pl.h);
  if (region && region.rev === rev && !drag) ctx.drawImage(region.img, region.x, region.y, region.w, region.h);
  ctx.restore();
  // grid: "cuts" = ONE line per boundary (middle of each overlap band); "sheets" = every sheet's own frame
  const [fw, fh] = j.frame, cuts = gridMode === 'cuts', reg = regionOf(j);
  ctx.fillStyle = cuts ? 'rgba(255,150,0,.13)' : 'rgba(255,150,0,.20)';
  for (let i = 1; i < j.xs.length; i++) { const x = j.xs[i], w = Math.min(j.xs[i - 1] + j.ws[i - 1], PW) - x; if (w > 0.01) ctx.fillRect(x, 0, w, PH); }
  for (let i = 1; i < j.ys.length; i++) { const y = j.ys[i], h = Math.min(j.ys[i - 1] + j.hs[i - 1], PH) - y; if (h > 0.01) ctx.fillRect(0, y, PW, h); }
  const clipTo = ([x0, y0, x1, y1]) => { ctx.beginPath(); ctx.rect(x0, y0, Math.min(x1, PW) - x0, Math.min(y1, PH) - y0); ctx.clip(); };
  // skipped sheets: dim + hatch
  for (const t of j.tiles) if (t.skipped) {
    const r = reg(t), w = r[2] - r[0], h = r[3] - r[1];
    ctx.save(); clipTo(r);
    ctx.fillStyle = dark ? 'rgba(0,0,0,.45)' : 'rgba(30,38,56,.16)'; ctx.fillRect(r[0], r[1], w, h);
    ctx.strokeStyle = dark ? 'rgba(255,255,255,.10)' : 'rgba(30,38,56,.16)'; ctx.lineWidth = 1 / sc; const g = 16 / sc;
    ctx.beginPath(); for (let k = -h; k < w; k += g) { ctx.moveTo(r[0] + k, r[3]); ctx.lineTo(r[0] + k + h, r[1]); } ctx.stroke(); ctx.restore();
  }
  // selection / hover
  const hl = (k, a) => { if (!k) return; const t = j.tiles.find(x => x.row === k[0] && x.col === k[1]); if (!t) return;
    const r = reg(t); ctx.save(); clipTo(r); ctx.globalAlpha = a; ctx.fillStyle = accent; ctx.fillRect(r[0], r[1], r[2] - r[0], r[3] - r[1]); ctx.restore(); };
  hl(hover, .08); hl(selected, .16);
  // lines
  ctx.save(); ctx.beginPath(); ctx.rect(-2 / sc, -2 / sc, PW + 4 / sc, PH + 4 / sc); ctx.clip();   // never leave the poster
  ctx.lineWidth = 1.5 / sc; ctx.strokeStyle = accent;
  if (cuts) {
    const cx = cutsOf(j.xs, j.ws, PW), cy = cutsOf(j.ys, j.hs, PH);
    ctx.globalAlpha = .95; ctx.beginPath();
    for (let i = 1; i < cx.length - 1; i++) { ctx.moveTo(cx[i], 0); ctx.lineTo(cx[i], PH); }
    for (let i = 1; i < cy.length - 1; i++) { ctx.moveTo(0, cy[i]); ctx.lineTo(PW, cy[i]); }
    ctx.stroke();
  } else {
    for (const t of j.tiles) { ctx.setLineDash(t.skipped ? [8 / sc, 6 / sc] : []); ctx.globalAlpha = t.skipped ? .55 : .95; ctx.strokeRect(t.x, t.y, t.w, t.h); }
  }
  ctx.restore(); ctx.setLineDash([]); ctx.globalAlpha = 1;
  // sheet numbers
  for (const t of j.tiles) {
    const r = reg(t), rw = Math.min(r[2], PW) - r[0], rh = Math.min(r[3], PH) - r[1];
    if (Math.min(rw, rh) * sc < 64) continue;
    const fs = Math.min(24, Math.max(11, Math.min(rw, rh) * 0.075 * sc)) / sc;
    const label = t.skipped ? '–' : t.label;
    ctx.font = `700 ${fs}px "TP Sans","TP Arabic",system-ui,sans-serif`;
    const tw = ctx.measureText(label).width, padx = fs * .55, ph = fs * 1.55, pw = Math.max(ph, tw + padx * 2);
    const px = r[0] + fs * .5, py = r[1] + fs * .5;
    ctx.fillStyle = t.skipped ? (dark ? '#4b5568' : '#8a93a6') : accent; rr(ctx, px, py, pw, ph, ph / 2); ctx.fill();
    ctx.fillStyle = dark && !t.skipped ? '#0b1226' : '#fff'; ctx.textBaseline = 'middle'; ctx.textAlign = 'center';
    ctx.fillText(label, px + pw / 2, py + ph / 2 + fs * .04);
  }
  // poster outline
  ctx.strokeStyle = dark ? 'rgba(255,255,255,.22)' : 'rgba(16,24,40,.35)'; ctx.lineWidth = 1 / sc; ctx.strokeRect(0, 0, PW, PH);
  ctx.restore();
  // chrome that depends on zoom
  $('#zPct').textContent = Math.round(view.s / fitS * 100) + '%';
  updateScaleBar();
}

function updateScaleBar() {
  const u = unit(), pxTarget = 110, len = pxTarget / view.s / PT[u];
  const pow = Math.pow(10, Math.floor(Math.log10(len))), m = len / pow;
  const nice = (m >= 5 ? 5 : m >= 2 ? 2 : 1) * pow;
  $('#sbLabel').textContent = `${+nice.toPrecision(3)} ${t('o_unit_' + u)}`; $('#sbBar').style.width = (nice * PT[u] * view.s) + 'px';
}

// -- crisp region re-render when zoomed past the base image's resolution
function scheduleRegion() { clearTimeout(regionTimer); regionTimer = setTimeout(fetchRegion, 200); }
async function fetchRegion() {
  if (!S || !S.job || !base) return;
  const j = S.job, pl = j.placement, dpr = window.devicePixelRatio || 1, W = stage.clientWidth, H = stage.clientHeight;
  const x0 = Math.max(-view.tx / view.s, pl.x, 0), y0 = Math.max(-view.ty / view.s, pl.y, 0);
  const x1 = Math.min((W - view.tx) / view.s, pl.x + pl.w, j.poster[0]), y1 = Math.min((H - view.ty) / view.s, pl.y + pl.h, j.poster[1]);
  if (x1 - x0 < 1 || y1 - y0 < 1) { region = null; return; }
  const need = view.s * dpr, have = base.w / pl.w;
  if (need <= have * 1.15) { if (region) { region = null; draw(); } return; }
  const myRev = rev, outPx = Math.min(2800, Math.ceil((x1 - x0) * need));
  const r = await call('render_region', x0, y0, x1 - x0, y1 - y0, outPx);
  if (!r || !r.ok || myRev !== rev) return;
  const img = new Image();
  img.onload = () => { if (myRev === rev) { region = { img, x: r.x, y: r.y, w: r.w, h: r.h, rev: myRev }; draw(); } };
  img.src = r.url;
}

// -- pointer interaction
function localPos(e) { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
cv.addEventListener('pointerdown', e => {
  if (!S || !S.job) return;
  cv.setPointerCapture(e.pointerId);
  const [x, y] = localPos(e), [wx, wy] = toWorld(x, y);
  const onContent = inContent(wx, wy);
  if (e.button === 1 || spaceDown || !onContent) { panning = { x, y, tx: view.tx, ty: view.ty }; cv.className = 'grabbing'; return; }
  if (e.button === 0) drag = { sx: x, sy: y, dx: 0, dy: 0, moved: false, tile: tileAt(wx, wy) };
});
cv.addEventListener('pointermove', e => {
  if (!S || !S.job) return;
  const [x, y] = localPos(e);
  if (panning) { view.tx = panning.tx + x - panning.x; view.ty = panning.ty + y - panning.y; queueDraw(); return; }
  if (drag) {
    const dx = (x - drag.sx) / view.s, dy = (y - drag.sy) / view.s;
    if (!drag.moved && Math.hypot(x - drag.sx, y - drag.sy) < 4) return;
    drag.moved = true; drag.dx = dx; drag.dy = dy; cv.className = 'grabbing'; queueDraw(); return;
  }
  const [wx, wy] = toWorld(x, y), t = tileAt(wx, wy), k = t ? [t.row, t.col] : null;
  if ((k && k.join()) !== (hover && hover.join())) { hover = k; queueDraw(); }
  cv.className = spaceDown ? 'hand' : inContent(wx, wy) ? 'move' : 'hand';
});
cv.addEventListener('pointerup', async e => {
  if (panning) { panning = null; cv.className = ''; scheduleRegion(); return; }
  if (!drag) return;
  const d = drag; drag = null; cv.className = 'move';
  if (d.moved) { const r = await call('move_content', d.dx, d.dy); apply(r); }
  else { selected = d.tile ? [d.tile.row, d.tile.col] : null; updateTileChip(); draw(); }
});
cv.addEventListener('dblclick', e => {
  if (!S || !S.job) return; const [x, y] = localPos(e), [wx, wy] = toWorld(x, y), t = tileAt(wx, wy);
  if (t && !t.skipped) openSheet(t.number);
});
cv.addEventListener('wheel', e => { e.preventDefault(); const [x, y] = localPos(e); zoomAt(x, y, Math.exp(-e.deltaY * (e.ctrlKey ? 0.012 : 0.0017))); }, { passive: false });
cv.addEventListener('pointerleave', () => { if (hover) { hover = null; queueDraw(); } });
new ResizeObserver(() => { if (S && S.job && !panning) { const pct = view.s / fitS; const oldW = cv._w || stage.clientWidth; fit(true); view.s = fitS * pct; cv._w = stage.clientWidth; draw(); scheduleRegion(); } else draw(); }).observe(stage);

// ============================================================ sheet preview modal
let sheetNo = 0;
async function openSheet(n) {
  const tile = tileByNumber(n); if (!tile) return;
  sheetNo = n; selected = [tile.row, tile.col]; updateTileChip(); draw();
  const m = $('#sheetModal'); m.hidden = false;
  $('#smTitle').textContent = t('sheetTitle', { label: tile.label });
  $('#smSub').textContent = t('sheetSub', { r: tile.row + 1, c: tile.col + 1, n: tile.number, total: S.job.printed });
  $$('#smNav [data-nav]').forEach(b => { b.disabled = !tile.nb[b.dataset.nav]; b.style.opacity = tile.nb[b.dataset.nav] ? 1 : .3; });
  $('#smSpin').hidden = false; $('#smImg').hidden = true;
  const r = await call('sheet_preview', n);
  if (n !== sheetNo) return;
  if (!r.ok) { closeSheet(); toast('bad', t('error'), r.error || ''); return; }
  $('#smImg').src = r.url; $('#smImg').hidden = false; $('#smSpin').hidden = true;
}
const closeSheet = () => { $('#sheetModal').hidden = true; sheetNo = 0; };

// ============================================================ files, projects, export
const isProject = n => n.toLowerCase().endsWith('.tileprint');
async function openPath(path) {
  busy(t('opening'), '', null);
  const r = await call('open_path', path);
  unbusy();
  if (!r.ok) { toast('bad', t('error'), r.error); return; }
  selected = null; apply(r.state, { fit: true });
  if (r.state.settings.footer_text === '' ) { /* footer falls back to the file name on the Python side */ }
}
async function uploadAndOpen(file, project) {
  busy(t('opening'), file.name, null);
  try {
    const up = await (await fetch('/upload?name=' + encodeURIComponent(file.name), { method: 'POST', headers: { 'X-TP-Token': token || '' }, body: file })).json();
    unbusy();
    if (!up.ok) return toast('bad', t('error'), up.error || '');
    if (project) { const r = await call('open_project_path', up.path); if (r.ok) { apply(r.state, { fit: true }); } else toast('bad', t('error'), r.error); }
    else await openPath(up.path);
  } catch (e) { unbusy(); toast('bad', t('error'), String(e)); }
}
async function handleFile(file) {
  if (file.pywebviewFullPath) {
    if (isProject(file.name)) { const r = await call('open_project_path', file.pywebviewFullPath); r.ok ? apply(r.state, { fit: true }) : toast('bad', t('error'), r.error); }
    else await openPath(file.pywebviewFullPath);
  } else if (token) await uploadAndOpen(file, isProject(file.name));
  else toast('info', t('dropFail'));
}
async function pickFile() {
  if (!token && window.pywebview) {
    busy(t('opening'), '', null); const r = await call('open_dialog'); unbusy();
    if (r.ok && !r.cancelled) { selected = null; apply(r.state, { fit: true }); } else if (!r.ok) toast('bad', t('error'), r.error);
  } else { const i = document.createElement('input'); i.type = 'file'; i.onchange = () => i.files[0] && handleFile(i.files[0]); i.click(); }
}
async function saveProject() {
  closeMenus();
  if (!S || !S.has_source) return toast('info', t('noFile'));
  if (!token && window.pywebview) { const r = await call('save_project_dialog'); if (r.ok && !r.cancelled) toast('ok', t('projSaved'), r.path); else if (!r.ok) toast('bad', t('error'), r.error); }
  else { const r = await call('project_text'); if (!r.ok) return; const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([r.text], { type: 'application/json' })); a.download = S.source.name.replace(/\.[^.]+$/, '') + '.tileprint'; a.click(); toast('ok', t('projSaved')); }
}
async function openProject() {
  closeMenus();
  if (!token && window.pywebview) { const r = await call('open_project_dialog'); if (r.ok && !r.cancelled) { apply(r.state, { fit: true }); } else if (!r.ok) toast('bad', t('error'), r.error); }
  else { const i = document.createElement('input'); i.type = 'file'; i.accept = '.tileprint'; i.onchange = () => i.files[0] && uploadAndOpen(i.files[0], true); i.click(); }
}
async function doExport(kind) {
  closeMenus();
  if (!S || !S.job) return toast('info', t('noFile'));
  if (kind === 'full' && S.job.too_big_for_single_page) return toast('bad', t('error'), t('tooBig'));
  const r = await call('export', kind);
  if (!r.ok) return toast('bad', t('error'), r.error);
  if (r.cancelled) return;
  busy(t('writing'), '', kind === 'tiled' ? 0 : null);
  const poll = async () => {
    const st = await call('export_status');
    if (st.state === 'running') {
      if (kind === 'tiled') busy(t('writing'), t('sheetsDone', { done: st.done, total: st.total }), st.total ? st.done / st.total * 100 : 0);
      setTimeout(poll, 140);
    } else if (st.state === 'done') {
      unbusy();
      const name = st.path.split(/[\\/]/).pop(), mb = (st.size / 1048576).toFixed(st.size > 1e7 ? 0 : 1);
      if (S.mode === 'browser') { window.location = `/download?id=${encodeURIComponent(st.token)}&t=${encodeURIComponent(token)}`; toast('ok', t('downloadStarted'), `${name} · ${mb} MB`); }
      else toast('ok', t('saved'), `${name} · ${mb} MB`, { label: t('showFolder'), fn: () => call('reveal', st.path) });
    } else { unbusy(); toast('bad', t('error'), st.error || ''); }
  };
  poll();
}

// ============================================================ global events
document.addEventListener('keydown', e => {
  if (e.target.matches('input, select, textarea')) { if (e.key === 'Escape') e.target.blur(); return; }
  const mod = e.ctrlKey || e.metaKey;
  if (e.code === 'Space') { spaceDown = true; cv.className = 'hand'; e.preventDefault(); }
  else if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); }
  else if (mod && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); }
  else if (mod && e.key.toLowerCase() === 'o') { e.preventDefault(); pickFile(); }
  else if (mod && e.key.toLowerCase() === 's') { e.preventDefault(); saveProject(); }
  else if (mod && e.key.toLowerCase() === 'e') { e.preventDefault(); doExport('tiled'); }
  else if (e.key === '+' || e.key === '=') zoomAt(cx(), cy(), 1.25);
  else if (e.key === '-') zoomAt(cx(), cy(), 1 / 1.25);
  else if (e.key === '0') fit();
  else if (e.key === 'Escape') { closeSheet(); closeMenus(); }
  else if (!$('#sheetModal').hidden) {
    const map = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' }, tile = tileByNumber(sheetNo);
    if (map[e.key] && tile && tile.nb[map[e.key]]) { e.preventDefault(); openSheet(tile.nb[map[e.key]]); }
  }
});
document.addEventListener('keyup', e => { if (e.code === 'Space') { spaceDown = false; cv.className = ''; } });
let dragDepth = 0;
window.addEventListener('dragenter', e => { e.preventDefault(); dragDepth++; $('#dropveil').hidden = false; $('#dropveil').textContent = t('dropHere'); $('#drop').classList.add('over'); });
window.addEventListener('dragleave', e => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) { $('#dropveil').hidden = true; $('#drop').classList.remove('over'); } });
window.addEventListener('dragover', e => e.preventDefault());
// Desktop: pywebview delivers dropped files (with real paths) to Python, which opens them and calls
// TP.afterExternalOpen. Here we only clean up the overlay and show progress. Browser mode: upload the file.
window.addEventListener('drop', e => { e.preventDefault(); dragDepth = 0; $('#dropveil').hidden = true; $('#drop').classList.remove('over');
  if (!token && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) { busy(t('opening'), '', null); setTimeout(unbusy, 60000); } }, true);
window.addEventListener('drop', e => {
  if (!token) return;                         // desktop: handled by Python
  const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]; if (f) handleFile(f); });
window.addEventListener('contextmenu', e => { if (!e.target.matches('input')) e.preventDefault(); });
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (!store.get('tp-theme')) applyTheme(); });

// ============================================================ boot
async function boot() {
  buildNums(); wireControls(); applyTheme();
  const saved = store.get('tp-lang');
  applyLang(saved || ((navigator.language || '').toLowerCase().startsWith('ar') ? 'ar' : 'en'));
  INIT = await call('init'); buildSelects();
  if (INIT && INIT.state) { if (!saved && INIT.state.settings.language) applyLang(INIT.state.settings.language); apply(INIT.state, { fit: true }); }
  call('update', { language: lang });
  const sf = await call('startup_file'); if (sf && sf.path) await openPath(sf.path);
  TP.ready = true;
}
TP.afterExternalOpen = r => {            // a file dropped on the desktop window (opened by Python)
  unbusy();
  if (!r || r.ok === false) { toast('bad', t('error'), (r && r.error) || ''); return; }
  selected = null; apply(r.state, { fit: true });
};
TP.apply = apply; TP.openPath = openPath; TP.call = call; TP.state = () => S; TP.openSheet = openSheet;
TP.setView = (s, tx, ty) => { view = { s, tx, ty }; draw(); scheduleRegion(); };
TP.fit = fit;
const start = () => boot();
if (token) start();
else if (window.pywebview && window.pywebview.api) start();
else window.addEventListener('pywebviewready', start);
})();
