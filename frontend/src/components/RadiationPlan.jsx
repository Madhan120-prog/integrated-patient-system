import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { CalendarDays, CircleCheck, Radiation, RotateCcw, ScanLine, TriangleAlert, Zap, ZoomIn, ZoomOut } from 'lucide-react';
import { formatDate } from './ChartVisuals';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const WINDOWS = [['lung', 'Lung'], ['soft', 'Soft tissue'], ['bone', 'Bone']];
const rgb = (c) => `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
const isoDate = (d) => (d && d.length === 8 ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}` : d);

// Met, met but within 10% of the limit, or not met.
const status = (c) => {
  if (!c.ok) return 'review';
  const close = c.op === '<=' ? c.value >= 0.9 * c.limit_value : c.value <= 1.02 * c.limit_value;
  return close ? 'close' : 'met';
};
const STATUS = {
  met: { label: 'Met', cls: 'bg-emerald-50 text-emerald-800 border-emerald-200', Icon: CircleCheck },
  close: { label: 'Met, close to limit', cls: 'bg-amber-50 text-amber-900 border-amber-200', Icon: CircleCheck },
  review: { label: 'Review', cls: 'bg-rose-50 text-rose-800 border-rose-200', Icon: TriangleAlert },
};

const Tile = ({ Icon, label, value, sub, tone = 'slate', children }) => (
  <div className={`card-raised rounded-2xl border p-4 bg-gradient-to-br ${tone === 'emerald' ? 'from-emerald-50 to-white border-emerald-100' : tone === 'amber' ? 'from-amber-50 to-white border-amber-100' : 'from-slate-50 to-white border-slate-200/70'}`}>
    <div className="flex items-start gap-3">
      <span className="w-10 h-10 rounded-xl flex items-center justify-center text-white shrink-0" style={{ background: tone === 'emerald' ? '#059669' : tone === 'amber' ? '#d97706' : '#0f766e' }}>
        <Icon className="w-5 h-5" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className="text-lg font-semibold text-slate-900 leading-snug">{value}</p>
        {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
    {children}
  </div>
);

// One planning CT slice, rendered by the server from the DICOM files.
// Scroll (mouse wheel or two fingers) steps through slices; pinch or Ctrl/Cmd + scroll
// zooms at the cursor; drag moves the image when zoomed; double-click resets.
const MAX_ZOOM = 6;
const SliceViewer = ({ patientId, ct, structures, site }) => {
  const [index, setIndex] = useState(ct.focus ?? Math.floor(ct.slices / 2));
  const [win, setWin] = useState(site === 'lung' ? 'lung' : 'soft');
  const [contours, setContours] = useState(true);
  const [dose, setDose] = useState(true);
  const [url, setUrl] = useState(null);
  const [view, setView] = useState({ zoom: 1, x: 0, y: 0 });
  const cache = useRef(new Map());
  const box = useRef(null);
  const wheelAcc = useRef(0);
  const drag = useRef(null);
  const size = view.zoom > 1.4 ? 1024 : 512;

  useEffect(() => () => cache.current.forEach((u) => URL.revokeObjectURL(u)), []);
  useEffect(() => {
    let live = true;
    const get = (i) => {
      const key = `${i}|${win}|${contours}|${dose}|${size}`;
      if (cache.current.has(key)) return Promise.resolve(cache.current.get(key));
      return axios.get(`${API}/radiation/${patientId}/slice/${i}`, { params: { window: win, contours, dose, size }, responseType: 'blob' })
        .then((res) => { const u = URL.createObjectURL(res.data); cache.current.set(key, u); return u; });
    };
    get(index).then((u) => live && setUrl(u)).catch(() => {});
    [index - 1, index + 1, index - 2, index + 2].filter((i) => i >= 0 && i < ct.slices).forEach((i) => get(i).catch(() => {}));   // smooth scrolling
    return () => { live = false; };
  }, [patientId, index, win, contours, dose, size, ct.slices]);

  // Keep the picture covering the frame: no panning past its edges.
  const clamp = (v, width) => {
    const max = 0;
    const min = width - width * v.zoom;
    return { zoom: v.zoom, x: Math.min(max, Math.max(min, v.x)), y: Math.min(max, Math.max(min, v.y)) };
  };
  const zoomAt = (factor, cx, cy) => setView((v) => {
    const width = box.current?.clientWidth || 1;
    const zoom = Math.min(MAX_ZOOM, Math.max(1, v.zoom * factor));
    const k = zoom / v.zoom;
    return clamp({ zoom, x: cx - (cx - v.x) * k, y: cy - (cy - v.y) * k }, width);
  });

  // Wheel needs a non-passive listener so the page does not scroll underneath.
  useEffect(() => {
    const el = box.current;
    if (!el) return undefined;
    const onWheel = (e) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      if (e.ctrlKey || e.metaKey) {                     // trackpad pinch arrives as ctrl + wheel
        zoomAt(Math.exp(-e.deltaY * 0.01), e.clientX - r.left, e.clientY - r.top);
        return;
      }
      wheelAcc.current += e.deltaY;
      const steps = Math.trunc(wheelAcc.current / 40);
      if (steps) {
        wheelAcc.current -= steps * 40;
        setIndex((i) => Math.min(ct.slices - 1, Math.max(0, i + steps)));
      }
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [ct.slices]);   // zoomAt only reads refs and setters

  const onPointerDown = (e) => {
    if (view.zoom <= 1) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { px: e.clientX, py: e.clientY, x: view.x, y: view.y };
  };
  const onPointerMove = (e) => {
    if (!drag.current) return;
    const d = drag.current;
    setView((v) => clamp({ zoom: v.zoom, x: d.x + e.clientX - d.px, y: d.y + e.clientY - d.py }, box.current.clientWidth));
  };
  const onPointerUp = () => { drag.current = null; };
  const onKeyDown = (e) => {
    if (e.key === 'ArrowUp' || e.key === 'ArrowRight') { e.preventDefault(); setIndex((i) => Math.min(ct.slices - 1, i + 1)); }
    if (e.key === 'ArrowDown' || e.key === 'ArrowLeft') { e.preventDefault(); setIndex((i) => Math.max(0, i - 1)); }
    if (e.key === '+' || e.key === '=') zoomAt(1.25, box.current.clientWidth / 2, box.current.clientWidth / 2);
    if (e.key === '-') zoomAt(0.8, box.current.clientWidth / 2, box.current.clientWidth / 2);
    if (e.key === '0') setView({ zoom: 1, x: 0, y: 0 });
  };

  const z = ct.zs?.[index];
  return (
    <div className="card-raised rounded-2xl border border-slate-200/70 bg-white p-4" data-testid="rt-viewer">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-900">Planning CT</h4>
          <p className="text-xs text-slate-500">Slice {index + 1} of {ct.slices}{z != null ? ` · z ${z > 0 ? '+' : ''}${z} mm` : ''} · {ct.description}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {WINDOWS.map(([id, label]) => (
            <button key={id} onClick={() => setWin(id)} aria-pressed={win === id}
              className={`text-xs font-medium rounded-full px-3 py-1 border ${win === id ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'}`}>{label}</button>
          ))}
          <button onClick={() => setContours(!contours)} aria-pressed={contours}
            className={`text-xs font-medium rounded-full px-3 py-1 border ${contours ? 'bg-teal-700 text-white border-teal-700' : 'bg-white text-slate-700 border-slate-200'}`}>Outlines</button>
          <button onClick={() => setDose(!dose)} aria-pressed={dose}
            className={`text-xs font-medium rounded-full px-3 py-1 border ${dose ? 'bg-teal-700 text-white border-teal-700' : 'bg-white text-slate-700 border-slate-200'}`}>Dose</button>
        </div>
      </div>
      <div ref={box} tabIndex={0} role="img" data-testid="rt-image"
        aria-label={`Planning CT slice ${index + 1} of ${ct.slices}. Scroll to change slice, pinch or Ctrl and scroll to zoom, drag to move, double-click to reset.`}
        onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}
        onDoubleClick={() => setView({ zoom: 1, x: 0, y: 0 })} onKeyDown={onKeyDown}
        className={`relative rounded-xl overflow-hidden bg-black aspect-square select-none touch-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-600 ${view.zoom > 1 ? (drag.current ? 'cursor-grabbing' : 'cursor-grab') : 'cursor-ns-resize'}`}>
        {url ? (
          <img src={url} alt="" draggable={false} className="absolute inset-0 w-full h-full object-contain origin-top-left"
            style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.zoom})` }} />
        ) : <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-400">Loading slice…</div>}
        <div className="absolute left-3 top-3 rounded-full bg-black/60 text-white text-[11px] font-medium px-2.5 py-1 pointer-events-none">
          {index + 1} / {ct.slices}{view.zoom > 1 ? ` · ${view.zoom.toFixed(1)}×` : ''}
        </div>
        <div className="absolute right-3 top-3 flex flex-col gap-1.5">
          <button onClick={() => zoomAt(1.3, box.current.clientWidth / 2, box.current.clientWidth / 2)} aria-label="Zoom in"
            className="w-8 h-8 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80"><ZoomIn className="w-4 h-4" /></button>
          <button onClick={() => zoomAt(1 / 1.3, box.current.clientWidth / 2, box.current.clientWidth / 2)} aria-label="Zoom out"
            className="w-8 h-8 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80"><ZoomOut className="w-4 h-4" /></button>
          {view.zoom > 1 && (
            <button onClick={() => setView({ zoom: 1, x: 0, y: 0 })} aria-label="Reset view"
              className="w-8 h-8 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80"><RotateCcw className="w-4 h-4" /></button>
          )}
        </div>
        <div className="absolute inset-x-0 bottom-0 px-3 py-2 bg-gradient-to-t from-black/70 to-transparent text-[11px] text-white/85 pointer-events-none">
          Scroll: slices · Pinch or Ctrl/⌘ + scroll: zoom · Drag: move · Double-click: reset
        </div>
      </div>
      <input type="range" min={0} max={ct.slices - 1} value={index} onChange={(e) => setIndex(Number(e.target.value))}
        aria-label="Slice" className="w-full mt-3 accent-teal-700" />
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1.5">
        {structures.map((s) => (
          <span key={s.name} className="inline-flex items-center gap-1.5 text-xs text-slate-700">
            <span className="w-3 h-3 rounded-sm border-2" style={{ borderColor: rgb(s.color) }} aria-hidden="true" />{s.name}
          </span>
        ))}
        {dose && (
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-700 ml-auto">
            Dose
            <span className="w-20 h-2.5 rounded-full" style={{ background: 'linear-gradient(90deg, #2563eb, #06b6d4, #22c55e, #facc15, #ef4444)' }} aria-hidden="true" />
            20% to 105%
          </span>
        )}
      </div>
    </div>
  );
};

// Cumulative dose-volume curves, computed from the dose and outline files.
const DvhChart = ({ dvh, structures, rx }) => {
  const [hidden, setHidden] = useState(() => new Set());
  const colors = useMemo(() => Object.fromEntries(structures.map((s) => [s.name, rgb(s.color)])), [structures]);
  const names = useMemo(() => Object.keys(dvh), [dvh]);
  const rows = useMemo(() => {
    const first = dvh[names[0]] || [];
    return first.map(([d], i) => Object.fromEntries([['dose', d], ...names.map((n) => [n, dvh[n][i]?.[1]])]));
  }, [dvh, names]);
  const toggle = (n) => setHidden((h) => { const next = new Set(h); if (next.has(n)) next.delete(n); else next.add(n); return next; });
  return (
    <div className="card-raised rounded-2xl border border-slate-200/70 bg-white p-4" data-testid="rt-dvh">
      <h4 className="text-sm font-semibold text-slate-900">Dose-volume histogram</h4>
      <p className="text-xs text-slate-500">Share of each structure receiving at least a given dose; the dashed line is the prescription. Select a name to hide or show it.</p>
      <div className="h-64 mt-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 6, right: 10, bottom: 18, left: 0 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis dataKey="dose" type="number" domain={[0, 'dataMax']} tick={{ fontSize: 11, fill: '#64748b' }}
              label={{ value: 'Dose (Gy)', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#64748b' }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} width={38} unit="%" />
            <Tooltip formatter={(v, n) => [`${Number(v).toFixed(1)}%`, n]} labelFormatter={(d) => `${d} Gy`} contentStyle={{ fontSize: 12, borderRadius: 12 }} />
            {rx && <ReferenceLine x={rx} stroke="#0f766e" strokeDasharray="4 4" />}
            {names.filter((n) => !hidden.has(n)).map((n) => (
              <Line key={n} type="monotone" dataKey={n} stroke={colors[n] || '#64748b'} strokeWidth={2.4} dot={false} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-1.5 mt-1">
        {names.map((n) => (
          <button key={n} onClick={() => toggle(n)} aria-pressed={!hidden.has(n)}
            className={`inline-flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 border ${hidden.has(n) ? 'bg-white text-slate-400 border-slate-200' : 'bg-slate-50 text-slate-800 border-slate-200'}`}>
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: hidden.has(n) ? '#cbd5e1' : colors[n] }} aria-hidden="true" />{n}
          </button>
        ))}
      </div>
    </div>
  );
};

const RadiationPlan = ({ patientId, data }) => {
  const { plan, constraints, delivery, structures, dvh, ct, site, image_source: source, dose_note: doseNote } = data;
  const breaks = delivery.breaks || [];
  const missed = Math.max(0, delivery.planned - delivery.delivered);
  const met = constraints.filter((c) => c.ok).length;
  const dynamic = plan.beams.some((b) => b.type === 'DYNAMIC');
  const energy = [...new Set(plan.beams.map((b) => b.energy_mv).filter(Boolean))].map((e) => `${e} MV`).join(', ');
  const review = constraints.filter((c) => status(c) === 'review').length;
  const close = constraints.filter((c) => status(c) === 'close').length;
  return (
    <div className="space-y-5" data-testid="radiation-plan">
      {(source || doseNote) && (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950" data-testid="rt-source">
          {source && <p><b className="font-semibold">Images:</b> {source.label}{source.license ? ` · ${source.license}` : ''}{source.doi ? ` · doi ${source.doi}` : ''}</p>}
          {doseNote && <p className="mt-0.5"><b className="font-semibold">Dose:</b> {doseNote}</p>}
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-4">
        <Tile Icon={Radiation} label="Prescription" value={`${plan.rx_gy} Gy in ${plan.fractions} fractions`}
          sub={`${plan.dose_per_fraction_gy} Gy per fraction · ${plan.name}`} />
        <Tile Icon={Zap} label="Technique" value={dynamic ? `VMAT, ${plan.beams.length} arcs` : `${plan.beams.length} static fields`}
          sub={`${energy} photons · ${plan.approval === 'APPROVED' ? 'approved' : plan.approval.toLowerCase()} ${formatDate(isoDate(plan.date))}`} />
        <Tile Icon={met === constraints.length ? CircleCheck : TriangleAlert} tone={met === constraints.length ? 'emerald' : 'amber'}
          label="Constraint checks" value={`${met} of ${constraints.length} met`}
          sub={review ? `${review} need${review === 1 ? 's' : ''} review` : close ? `${close} close to ${close === 1 ? 'its limit' : 'their limits'}` : 'All with margin'} />
        <Tile Icon={CalendarDays} label="Delivered" value={`${delivery.delivered} of ${delivery.planned} fractions`}
          sub={delivery.first ? `${formatDate(delivery.first)} to ${formatDate(delivery.last)} · ${delivery.dose_delivered_gy} Gy` : 'Not started'}>
          <div className="mt-3 h-2 rounded-full bg-slate-100 overflow-hidden" aria-hidden="true">
            <div className="h-full rounded-full bg-teal-600" style={{ width: `${(delivery.delivered / delivery.planned) * 100}%` }} />
          </div>
          <p className={`mt-2 text-xs font-medium ${breaks.length || missed ? 'text-amber-800' : 'text-emerald-700'}`} data-testid="rt-delivery-exceptions">
            {breaks.length
              ? `Treatment break: ${breaks.map((b) => `${b.working_days_missed} working days after ${formatDate(b.after)}`).join('; ')}`
              : missed ? `${missed} fraction${missed === 1 ? '' : 's'} still to deliver` : 'No missed fractions or treatment breaks'}
          </p>
        </Tile>
      </div>

      <div className="grid xl:grid-cols-2 gap-5">
        {ct ? <SliceViewer patientId={patientId} ct={ct} structures={structures.filter((s) => !s.derived)} site={site} />
          : <div className="card-raised rounded-2xl border border-slate-200/70 bg-white p-4 text-sm text-slate-500"><ScanLine className="w-5 h-5 mb-2" />No planning CT in the picture archive.</div>}
        <div className="space-y-5">
          <DvhChart dvh={dvh} structures={structures} rx={plan.rx_gy} />
          <div className="card-raised rounded-2xl border border-slate-200/70 bg-white p-4" data-testid="rt-constraints">
            <h4 className="text-sm font-semibold text-slate-900">Plan checks</h4>
            <p className="text-xs text-slate-500">Computed in code from the plan files, not by AI. Example limits; the clinic’s own protocol applies.</p>
            <table className="w-full text-sm mt-3">
              <thead><tr className="text-left text-xs text-slate-500"><th className="font-medium pb-1.5">Check</th><th className="font-medium pb-1.5">Limit</th><th className="font-medium pb-1.5 text-right">Plan</th><th className="font-medium pb-1.5 text-right">Status</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {constraints.map((c) => {
                  const s = STATUS[status(c)];
                  return (
                    <tr key={c.label}>
                      <td className="py-2 pr-2 text-slate-900">{c.label}</td>
                      <td className="py-2 pr-2 text-slate-600 whitespace-nowrap">{c.limit}</td>
                      <td className="py-2 pr-2 text-right font-semibold text-slate-900 whitespace-nowrap">{c.value} {c.unit}</td>
                      <td className="py-2 text-right">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium rounded-full border px-2 py-0.5 whitespace-nowrap ${s.cls}`}>
                          <s.Icon className="w-3.5 h-3.5" aria-hidden="true" />{s.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

    </div>
  );
};

export default RadiationPlan;
