import React, { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceArea, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import {
  CircleCheck, Info, Pill, Radiation, Scissors, ShieldPlus, Sparkles, Syringe, TriangleAlert,
} from 'lucide-react';

// ── Shared tokens ────────────────────────────────────────────────────────────
// Categorical colours are a validated colour-blind-safe set, used in this fixed
// order. Identity is never colour alone: every lane, step and chip is labelled.
const INK = { primary: '#0f172a', secondary: '#475569', muted: '#94a3b8', grid: '#e2e8f0', surface: '#ffffff' };
const SERIES = '#2a78d6';
// One colour means "outside the reference range"; the letter says which side.
// Low and high are not ranked against each other, because the record doesn't rank them.
export const OUT_OF_RANGE = '#d03b3b';
export const RANGE_LETTER = { LOW: 'L', HIGH: 'H' };
export const RANGE_WORD = { LOW: 'Below range', HIGH: 'Above range', 'IN RANGE': 'In range' };

// One colour per department system, in the validated order. Keys are the
// department names the backend sends (the same names as the search page).
export const SYSTEM_COLORS = {
  Treatment: '#2a78d6',
  'Blood Test': '#eb6834',
  'MRI Scan': '#1baf7a',
  'CT Scan': '#eda100',
  'X-Ray': '#e87ba4',
  ECG: '#008300',
};
const TREATMENT = {
  Surgery: { color: '#2a78d6', Icon: Scissors },
  Chemotherapy: { color: '#eb6834', Icon: Syringe },
  'Radiation Therapy': { color: '#1baf7a', Icon: Radiation },
  Immunotherapy: { color: '#eda100', Icon: ShieldPlus },
  'Hormone Therapy': { color: '#e87ba4', Icon: Pill },
  Medication: { color: '#008300', Icon: Pill },
};
const OTHER_TREATMENT = { color: '#64748b', Icon: Pill };

const ts = (d) => new Date(`${d}T00:00:00`).getTime();
export const formatDate = (d) =>
  d ? new Date(`${d}T00:00:00`).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '';
const tickDate = (t) => new Date(t).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });

// ── DocAssist orb: the assistant's mark, used on the button and in the drawer ─

export const DocAssistOrb = ({ size = 40 }) => (
  <span className="docassist-orb inline-flex items-center justify-center shrink-0" style={{ width: size, height: size }} aria-hidden="true">
    <span className="rounded-full bg-slate-950/85 flex items-center justify-center" style={{ width: size - 6, height: size - 6 }}>
      <Sparkles className="text-white" style={{ width: size * 0.42, height: size * 0.42 }} />
    </span>
  </span>
);

// ── Stat tile ────────────────────────────────────────────────────────────────

const TILE = {
  rose: { cls: 'from-rose-50 to-white border-rose-100', icon: '#e11d48' },
  sky: { cls: 'from-sky-50 to-white border-sky-100', icon: '#0284c7' },
  violet: { cls: 'from-violet-50 to-white border-violet-100', icon: '#7c3aed' },
  emerald: { cls: 'from-emerald-50 to-white border-emerald-100', icon: '#059669' },
};

export const StatTile = ({ tone, Icon, label, value, children }) => (
  <div className={`card-raised lift rounded-2xl border bg-gradient-to-br p-4 ${TILE[tone].cls}`}>
    <div className="flex items-start gap-3">
      <span className="w-10 h-10 rounded-xl flex items-center justify-center text-white shrink-0 shadow-sm" style={{ background: TILE[tone].icon }}>
        <Icon className="w-5 h-5" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className="text-lg font-semibold text-slate-900 leading-snug break-words">{value}</p>
      </div>
    </div>
    {children && <div className="mt-3 text-xs text-slate-600">{children}</div>}
  </div>
);

// ── Key finding card: the finding and its basis, both visible ────────────────

const TONE = {
  attention: { Icon: TriangleAlert, label: 'Needs review', cls: 'from-rose-50 to-white border-rose-200', chip: 'bg-rose-600' },
  info: { Icon: Info, label: 'For context', cls: 'from-sky-50 to-white border-sky-200', chip: 'bg-sky-600' },
  clear: { Icon: CircleCheck, label: 'Stated absent', cls: 'from-emerald-50 to-white border-emerald-200', chip: 'bg-emerald-600' },
};

export const FindingCard = ({ finding }) => {
  const t = TONE[finding.tone];
  return (
    <li className={`card-raised lift rounded-2xl border bg-gradient-to-br p-4 ${t.cls}`}>
      <div className="flex items-center gap-2">
        <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-white ${t.chip}`}><t.Icon className="w-4 h-4" aria-hidden="true" /></span>
        <span className="text-xs font-medium text-slate-600">{t.label}</span>
        {finding.date && <span className="text-xs text-slate-500 ml-auto">{formatDate(finding.date)}</span>}
      </div>
      <p className="text-[15px] font-semibold text-slate-900 leading-snug mt-3">{finding.title}</p>
      <p className="text-sm text-slate-600 leading-snug mt-1">{finding.detail}</p>
    </li>
  );
};

// ── Range gauge: where the latest value sits against its reference range ─────

export const RangeGauge = ({ row }) => {
  const latestDate = Object.keys(row.cells).sort().pop();
  const { value, status } = row.cells[latestDate];
  const span = row.high - row.low || 1;
  const min = Math.min(value, row.low) - span * 0.35, max = Math.max(value, row.high) + span * 0.35;
  const pct = (v) => ((v - min) / (max - min)) * 100;
  const out = status !== 'IN RANGE';
  return (
    <div className="py-2" data-testid={`gauge-${row.analyte}`}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-slate-900">{row.analyte}</span>
        <span className="text-sm tabular-nums text-slate-900">
          {value} <span className="text-slate-500">{row.unit}</span>
          <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-md ${out ? 'bg-rose-100 text-rose-900' : 'bg-emerald-100 text-emerald-900'}`}>{RANGE_WORD[status]}</span>
        </span>
      </div>
      <div className="relative h-2.5 mt-2 rounded-full bg-slate-200" role="img"
        aria-label={`${row.analyte} ${value} ${row.unit}, ${RANGE_WORD[status]}, reference range ${row.low} to ${row.high}`}>
        <span className="absolute inset-y-0 rounded-full bg-emerald-300" style={{ left: `${pct(row.low)}%`, width: `${pct(row.high) - pct(row.low)}%` }} />
        <span className="absolute top-1/2 w-4 h-4 -mt-2 -ml-2 rounded-full border-2 border-white shadow" style={{ left: `${pct(value)}%`, background: out ? OUT_OF_RANGE : SERIES }} />
      </div>
      <div className="relative h-4 mt-1 text-[11px] text-slate-500 tabular-nums">
        <span className="absolute -translate-x-1/2" style={{ left: `${pct(row.low)}%` }}>{row.low}</span>
        <span className="absolute -translate-x-1/2" style={{ left: `${pct(row.high)}%` }}>{row.high}</span>
      </div>
    </div>
  );
};

// ── Sparkline: the shape of one analyte's readings, for a flowsheet row ───────

export const Sparkline = ({ row }) => {
  const points = Object.entries(row.cells).sort(([a], [b]) => a.localeCompare(b)).map(([, c]) => c);
  if (points.length < 2) return null;
  const W = 84, H = 26, pad = 4;
  const values = points.map((p) => p.value);
  const min = Math.min(...values), max = Math.max(...values);
  const x = (i) => pad + (i / (points.length - 1)) * (W - pad * 2);
  const y = (v) => (max === min ? H / 2 : H - pad - ((v - min) / (max - min)) * (H - pad * 2));
  const last = points[points.length - 1];
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true" className="inline-block align-middle">
      <polyline points={points.map((p, i) => `${x(i)},${y(p.value)}`).join(' ')} fill="none" stroke={SERIES} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(points.length - 1)} cy={y(last.value)} r="3.5" fill={last.status === 'IN RANGE' ? SERIES : OUT_OF_RANGE} stroke={INK.surface} strokeWidth="1.5" />
    </svg>
  );
};

// ── Lab trend chart: one analyte, shaded reference range, shared date axis ───

const TrendDot = ({ cx, cy, payload }) => {
  if (cx == null || cy == null) return null;
  const out = payload.status !== 'IN RANGE';
  return (
    <g>
      <circle cx={cx} cy={cy} r={5} fill={out ? OUT_OF_RANGE : SERIES} stroke={INK.surface} strokeWidth={2} />
      {out && <text x={cx} y={cy - 10} textAnchor="middle" fontSize={11} fontWeight={600} fill={INK.primary}>{RANGE_LETTER[payload.status]}</text>}
    </g>
  );
};

const TrendTooltip = ({ active, payload, unit }) => {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs shadow-md">
      <p className="text-slate-500">{formatDate(p.date)}</p>
      <p className="font-medium text-slate-900">{p.value} {unit}</p>
      <p className={p.status === 'IN RANGE' ? 'text-slate-600' : 'text-rose-700'}>{RANGE_WORD[p.status]}</p>
    </div>
  );
};

export const LabTrendChart = ({ row, domain, events = [], height = 150 }) => {
  const data = Object.entries(row.cells).map(([date, c]) => ({ t: ts(date), date, ...c })).sort((a, b) => a.t - b.t);
  const last = data[data.length - 1];
  const gradient = `fill-${row.analyte.replace(/[^a-z0-9]/gi, '')}`;
  return (
    <figure className="min-w-0" data-testid={`trend-${row.analyte}`}>
      <figcaption className="flex items-baseline justify-between gap-2 mb-1">
        <span className="text-sm font-semibold text-slate-900">{row.analyte} <span className="font-normal text-slate-500">{row.unit}</span></span>
        <span className="text-xs text-slate-600 tabular-nums">
          latest {last.value}{row.trend ? ` · ${row.trend.direction} ${Math.abs(row.trend.pct_change)}%` : ''}
        </span>
      </figcaption>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={SERIES} stopOpacity={0.22} />
              <stop offset="100%" stopColor={SERIES} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke={INK.grid} />
          <ReferenceArea y1={row.low} y2={row.high} fill="#34d399" fillOpacity={0.16} ifOverflow="extendDomain" />
          {events.map((e, i) => <ReferenceLine key={i} x={ts(e.date)} stroke={INK.muted} strokeWidth={1} />)}
          <XAxis dataKey="t" type="number" scale="time" domain={domain} tickFormatter={tickDate} tickCount={4}
            tick={{ fontSize: 11, fill: INK.secondary }} axisLine={{ stroke: INK.grid }} tickLine={false} />
          <YAxis domain={['auto', 'auto']} width={38} tick={{ fontSize: 11, fill: INK.secondary }} axisLine={false} tickLine={false} tickCount={4} />
          <Tooltip content={<TrendTooltip unit={row.unit} />} cursor={{ stroke: INK.muted, strokeWidth: 1 }} />
          <Area type="linear" dataKey="value" stroke={SERIES} strokeWidth={2} fill={`url(#${gradient})`} dot={<TrendDot />} activeDot={{ r: 6 }} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
      <p className="text-[11px] text-slate-500 mt-0.5">Green band is the reference range, {row.low} to {row.high}{events.length ? '. Vertical lines are treatment events' : ''}.</p>
    </figure>
  );
};

// ── All-systems timeline: one lane per source system ─────────────────────────

export const SystemsTimeline = ({ timeline, domain }) => {
  const [selected, setSelected] = useState(null);
  const lanes = Object.keys(SYSTEM_COLORS).filter((s) => timeline.some((i) => i.system === s));
  const [min, max] = domain;
  const span = max - min || 1;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => min + span * f);
  if (!timeline.length) return <p className="text-sm text-slate-500">No records on file.</p>;
  return (
    <div data-testid="systems-timeline">
      <div className="space-y-1.5">
        {lanes.map((system) => {
          const seen = {};
          return (
            <div key={system} className="grid grid-cols-[6.5rem_1fr] items-center gap-3">
              <span className="flex items-center gap-2 text-xs font-medium text-slate-700 leading-tight">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: SYSTEM_COLORS[system] }} aria-hidden="true" />
                {system}
              </span>
              <div className="relative h-9 rounded-full bg-slate-100 mx-3">
                {timeline.filter((i) => i.system === system).map((item, k) => {
                  const nudge = (seen[item.date] = (seen[item.date] ?? -1) + 1) * 10;   // same-day records sit side by side
                  const isSel = selected === item;
                  return (
                    <button
                      key={k}
                      onClick={() => setSelected(isSel ? null : item)}
                      title={`${formatDate(item.date)} · ${item.title}: ${item.result}`}
                      aria-label={`${item.title}, ${formatDate(item.date)}`}
                      aria-pressed={isSel}
                      className="absolute top-1/2 w-6 h-6 -mt-3 -ml-3 flex items-center justify-center rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900"
                      style={{ left: `calc(${((ts(item.date) - min) / span) * 100}% + ${nudge}px)` }}
                    >
                      <span className={`rounded-full border-2 border-white shadow-sm transition-all ${isSel ? 'w-5 h-5 ring-2 ring-slate-900' : 'w-3.5 h-3.5 hover:w-4 hover:h-4'}`} style={{ background: SYSTEM_COLORS[system] }} />
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
        <div className="grid grid-cols-[6.5rem_1fr] gap-3">
          <span />
          <div className="relative h-5 mx-3">
            {ticks.map((t, i) => (
              <span key={i} className="absolute text-[11px] text-slate-500 -translate-x-1/2 whitespace-nowrap" style={{ left: `${(i / 4) * 100}%` }}>{tickDate(t)}</span>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-2 min-h-[3.5rem] rounded-xl bg-slate-50 border border-slate-200 px-4 py-2.5 text-sm" aria-live="polite">
        {selected ? (
          <div className="rise-in">
            <p className="font-semibold text-slate-900">{selected.title}</p>
            <p className="text-xs text-slate-500">{formatDate(selected.date)} · {selected.system}</p>
            <p className="text-slate-700 mt-1">{selected.result}</p>
          </div>
        ) : <p className="text-slate-500">Select any point to read that record.</p>}
      </div>
    </div>
  );
};

// ── Treatment course: ordered steps on a connecting line ─────────────────────

export const TreatmentTimeline = ({ treatments }) =>
  treatments.length === 0 ? <p className="text-sm text-slate-500">No treatment on record.</p> : (
    <ol className="flex overflow-x-auto pb-2 snap-x" data-testid="treatment-timeline">
      {treatments.map((t, i) => {
        const { color, Icon } = TREATMENT[t.category] || OTHER_TREATMENT;
        return (
          <li key={i} className="shrink-0 w-56 snap-start">
            <div className="flex items-center" aria-hidden="true">
              <span className="w-10 h-10 rounded-full flex items-center justify-center text-white shadow-md ring-4 ring-white" style={{ background: color }}>
                <Icon className="w-5 h-5" />
              </span>
              {i < treatments.length - 1 && <span className="flex-1 h-0.5 bg-slate-200" />}
            </div>
            <div className="card-raised lift rounded-xl border border-slate-200 bg-white mt-3 mr-3 p-3">
              <p className="text-xs font-medium text-slate-500">{t.category}</p>
              <p className="text-sm font-semibold text-slate-900 leading-snug [overflow-wrap:anywhere]">
                {t.name.split('/').map((part, k, all) => <React.Fragment key={k}>{part}{k < all.length - 1 && <>/<wbr /></>}</React.Fragment>)}
              </p>
              <p className="text-xs text-slate-500 mt-1">{formatDate(t.date)}</p>
              <div className="flex flex-wrap gap-1 mt-2">
                <span className={`text-[11px] px-2 py-0.5 rounded-full ${t.status === 'In progress' ? 'bg-sky-100 text-sky-900' : 'bg-slate-100 text-slate-700'}`}>{t.status}</span>
                {t.modified && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-rose-100 text-rose-900 flex items-center gap-1" title={t.result}>
                    <TriangleAlert className="w-3 h-3" aria-hidden="true" />Modified
                  </span>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
