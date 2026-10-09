import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Activity, ArrowUpRight, CalendarClock, CalendarDays, Database, HeartPulse, Maximize2, Minimize2, Ruler, Thermometer, Weight, Wind, FlaskConical, LayoutDashboard, Pill, ScanLine, Stethoscope, Syringe,
  TriangleAlert, Users, X,
} from 'lucide-react';
import { Skeleton } from '../components/ui/skeleton';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import AskPanel from '../components/AskPanel';
import {
  StatTile, FindingCard, RangeGauge, Sparkline, LabTrendChart, SystemsTimeline, TreatmentTimeline, DocAssistOrb,
  SYSTEM_COLORS, RANGE_LETTER, RANGE_WORD, formatDate,
} from '../components/ChartVisuals';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SECTIONS = [
  { id: 'Summary', Icon: LayoutDashboard },
  { id: 'Labs', Icon: FlaskConical },
  { id: 'Imaging', Icon: ScanLine },
  { id: 'Treatment', Icon: Syringe },
  { id: 'Medications', Icon: Pill },
  { id: 'Visits', Icon: CalendarDays },
  { id: 'Timeline', Icon: Activity },
];
const IMAGE_DEPARTMENTS = ['MRI', 'CT Scan', 'X-Ray', 'ECG'];
const SUMMARY_QUESTION = "Summarize this patient's current status in a few bullet points.";

const shortDate = (d) => new Date(`${d}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
const ts = (d) => new Date(`${d}T00:00:00`).getTime();
const initials = (name) => name.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase();

const OutChip = ({ status, children }) => (
  <span className="inline-block px-1.5 rounded-md bg-rose-100 text-rose-900" title={RANGE_WORD[status]}>
    {children} {RANGE_LETTER[status]}
  </span>
);

// Patient header: one compact card. Every field shows in full and wraps; nothing is cut short.
const PatientHero = ({ profile, flagCount }) => {
  const facts = [
    ['Diagnosis', profile.diagnosis], ['Stage', profile.stage], ['Biomarkers', profile.biomarkers],
    ['Regimen', profile.regimen], ['Allergies', profile.allergies],
  ].filter(([, value]) => value);
  return (
    <section aria-label="Patient" data-testid="chart-banner"
      className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-teal-700 via-teal-600 to-cyan-600 text-white card-raised">
      <span className="absolute -top-20 -right-10 w-56 h-56 rounded-full bg-white/10" aria-hidden="true" />
      <div className="relative p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className="w-12 h-12 rounded-2xl bg-white/20 flex items-center justify-center text-lg font-semibold ring-1 ring-white/30">{initials(profile.name)}</span>
          <div className="min-w-0">
            <h2 className="text-xl font-semibold leading-tight">{profile.name}</h2>
            <p className="text-sm text-teal-50">
              {profile.age} years · {profile.gender} · {profile.mrn || profile.patient_id}{profile.mrn ? ` · ${profile.patient_id}` : ''}
              {profile.primary_oncologist ? ` · Oncologist ${profile.primary_oncologist}` : ''}
            </p>
          </div>
          <span data-testid="chart-flag-count"
            className={`ml-auto inline-flex items-center gap-2 text-sm font-medium px-3.5 py-1.5 rounded-full ${flagCount ? 'bg-white text-rose-700' : 'bg-white/20 text-white'}`}>
            {flagCount > 0 && <TriangleAlert className="w-4 h-4" aria-hidden="true" />}
            {flagCount ? `${flagCount} lab value${flagCount > 1 ? 's' : ''} out of range` : 'No lab values out of range'}
          </span>
        </div>
        {(facts.length > 0 || profile.ecog != null) && (
          <dl className="mt-3 flex flex-wrap gap-2">
            {facts.map(([label, value]) => (
              <div key={label} className="rounded-xl bg-white/10 ring-1 ring-white/15 px-3 py-1.5 max-w-full">
                <dt className="inline text-xs text-teal-100">{label} </dt>
                <dd className="inline text-sm font-medium">{value}</dd>
              </div>
            ))}
            {profile.ecog != null && (
              <div className="rounded-xl bg-white/10 ring-1 ring-white/15 px-3 py-1.5 flex items-center gap-2">
                <dt className="text-xs text-teal-100">ECOG</dt>
                <dd className="flex items-center gap-2 text-sm font-medium">
                  {profile.ecog} of 4
                  <span className="flex gap-0.5" aria-hidden="true">
                    {[0, 1, 2, 3, 4].map((n) => <span key={n} className={`w-3.5 h-1.5 rounded-full ${n <= profile.ecog ? 'bg-white' : 'bg-white/25'}`} />)}
                  </span>
                </dd>
              </div>
            )}
          </dl>
        )}
      </div>
    </section>
  );
};

const Panel = ({ title, note, action, children }) => (
  <section className="card-raised bg-white border border-slate-200/70 rounded-2xl">
    <header className="px-5 pt-4 pb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
      <div>
        <h3 className="text-base font-semibold text-slate-900">{title}</h3>
        {note && <p className="text-xs text-slate-500 mt-0.5">{note}</p>}
      </div>
      {action}
    </header>
    <div className="px-5 pb-5">{children}</div>
  </section>
);

const Empty = ({ children }) => <p className="text-sm text-slate-500">{children}</p>;

const SystemTag = ({ system }) => (
  <span className="inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
    <span className="w-2 h-2 rounded-full" style={{ background: SYSTEM_COLORS[system] }} aria-hidden="true" />{system}
  </span>
);

const RecordList = ({ items }) =>
  items.length === 0 ? <Empty>No records in this view.</Empty> : (
    <ol className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="rounded-xl border border-slate-200 bg-white px-4 py-3 flex gap-4 text-sm">
          <span className="w-1 rounded-full shrink-0" style={{ background: SYSTEM_COLORS[item.system] }} aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-semibold text-slate-900">{item.title}</span>
              <SystemTag system={item.system} />
              <time className="text-xs text-slate-500 ml-auto tabular-nums">{formatDate(item.date)}</time>
            </div>
            <p className="text-slate-700 mt-1">{item.result}</p>
            {item.medicines && item.medicines !== 'N/A' && <p className="text-slate-500 text-xs mt-1">{item.medicines}</p>}
          </div>
        </li>
      ))}
    </ol>
  );

const Flowsheet = ({ flowsheet }) =>
  flowsheet.rows.length === 0 ? <Empty>No numeric lab values on file for this patient.</Empty> : (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table className="w-full text-sm border-collapse" data-testid="lab-flowsheet">
        <caption className="sr-only">Lab values by date. L marks a value below its reference range, H a value above it.</caption>
        <thead>
          <tr className="text-left text-xs text-slate-600 bg-slate-50">
            <th scope="col" className="sticky left-0 bg-slate-50 py-2.5 px-4 font-medium">Analyte and reference range</th>
            {flowsheet.dates.map((d) => <th key={d} scope="col" className="py-2.5 px-3 font-medium text-right whitespace-nowrap">{shortDate(d)}</th>)}
            <th scope="col" className="py-2.5 px-3 font-medium text-center">Trend</th>
            <th scope="col" className="py-2.5 px-4 font-medium text-right whitespace-nowrap">First to latest</th>
          </tr>
        </thead>
        <tbody>
          {flowsheet.rows.map((row) => (
            <tr key={row.analyte} className="border-t border-slate-100 hover:bg-slate-50/60">
              <th scope="row" className="sticky left-0 bg-white py-2.5 px-4 text-left font-semibold text-slate-900 whitespace-nowrap">
                {row.analyte}
                <span className="font-normal text-slate-500"> {row.low} to {row.high} {row.unit}</span>
              </th>
              {flowsheet.dates.map((d) => {
                const cell = row.cells[d];
                return (
                  <td key={d} className="py-2.5 px-3 text-right tabular-nums">
                    {!cell ? null : cell.status !== 'IN RANGE' ? <OutChip status={cell.status}>{cell.value}</OutChip> : cell.value}
                  </td>
                );
              })}
              <td className="py-1 px-3 text-center"><Sparkline row={row} /></td>
              <td className="py-2.5 px-4 text-right tabular-nums text-slate-600 whitespace-nowrap">
                {row.trend ? `${row.trend.direction} ${Math.abs(row.trend.pct_change)}%` : ''}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

// A thumbnail that says so when the image is missing or fails to load.
const Thumb = ({ src }) => {
  const [failed, setFailed] = useState(false);
  return src && !failed
    ? <img src={src} alt="" loading="lazy" onError={() => setFailed(true)} className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
    : <span className="text-xs text-slate-400">{src ? 'Image could not be loaded' : 'No image attached'}</span>;
};

const ImageGallery = ({ items, onOpen }) =>
  items.length === 0 ? <Empty>No imaging or tracings on file.</Empty> : (
    <ul className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="image-gallery">
      {items.map((item, i) => (
        <li key={i}>
          <button onClick={() => onOpen(item)} className="group card-raised lift w-full text-left rounded-2xl border border-slate-200 bg-white overflow-hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-700">
            <div className="h-40 bg-slate-900 flex items-center justify-center overflow-hidden">
              <Thumb src={item.image} />
            </div>
            <div className="px-4 py-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                <span className="text-xs text-slate-500 whitespace-nowrap">{formatDate(item.date)}</span>
              </div>
              <p className="text-sm text-slate-700 mt-1">{item.result}</p>
            </div>
          </button>
        </li>
      ))}
    </ul>
  );

// A calendar-style date block: month on top, day large, year below.
const DateBlock = ({ date, tone = 'slate' }) => {
  const d = new Date(`${date}T00:00:00`);
  const head = tone === 'teal' ? 'bg-teal-700' : 'bg-slate-700';
  return (
    <span className="w-14 shrink-0 rounded-xl overflow-hidden border border-slate-200 bg-white text-center card-raised" aria-label={formatDate(date)}>
      <span className={`block text-[11px] font-medium text-white py-0.5 ${head}`}>{d.toLocaleDateString('en-US', { month: 'short' })}</span>
      <span className="block text-lg font-semibold text-slate-900 leading-tight pt-0.5">{d.getDate()}</span>
      <span className="block text-[11px] text-slate-500 pb-1">{d.getFullYear()}</span>
    </span>
  );
};

const DoctorChip = ({ name, isViewer }) => (
  <span className={`inline-flex items-center gap-1.5 text-xs pl-1 pr-2.5 py-0.5 rounded-full ${isViewer ? 'bg-teal-700 text-white' : 'bg-slate-100 text-slate-700'}`}>
    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-semibold ${isViewer ? 'bg-white/25' : 'bg-white'}`} aria-hidden="true">
      {name.replace('Dr. ', '').slice(0, 1)}
    </span>
    {name}{isViewer ? ' (you)' : ''}
  </span>
);

const VisitList = ({ visits, viewer }) =>
  visits.length === 0 ? <Empty>No visits in this view.</Empty> : (
    <ol className="space-y-3" data-testid="visit-list">
      {visits.map((v) => (
        <li key={v.date} className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-4">
          <DateBlock date={v.date} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap gap-1.5">
              {v.doctors.map((d) => <DoctorChip key={d} name={d} isViewer={d === viewer} />)}
            </div>
            <ul className="mt-2.5 space-y-1.5">
              {v.items.map((item, i) => (
                <li key={i} className="flex gap-2.5 text-sm">
                  <span className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: SYSTEM_COLORS[item.system] }} aria-hidden="true" />
                  <span><span className="font-medium text-slate-900">{item.title}</span><span className="text-slate-600">: {item.result}</span>
                    <span className="text-xs text-slate-500"> · {item.doctor}</span></span>
                </li>
              ))}
            </ul>
          </div>
        </li>
      ))}
    </ol>
  );

// One page, many sections: each has an anchor the sidebar scrolls to and watches.
const Section = ({ id, children }) => {
  const { Icon } = SECTIONS.find((sec) => sec.id === id);
  return (
    <section id={`section-${id}`} data-section={id} aria-label={id} className="scroll-mt-5 space-y-5">
      {id !== 'Summary' && (
        <h2 className="flex items-center gap-2.5 text-lg font-semibold text-slate-900 pt-3">
          <span className="w-8 h-8 rounded-xl bg-teal-700 text-white flex items-center justify-center"><Icon className="w-4 h-4" aria-hidden="true" /></span>
          {id}
        </h2>
      )}
      {children}
    </section>
  );
};

const ChartSkeleton = () => (
  <div className="min-h-screen bg-slate-50" aria-busy="true" aria-label="Loading chart">
    <div className="max-w-[1320px] mx-auto px-4 py-5 grid gap-4">
      <Skeleton className="h-48 w-full rounded-3xl" />
      <div className="grid grid-cols-2 gap-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 rounded-2xl" />)}</div>
      <Skeleton className="h-64 w-full rounded-2xl" />
    </div>
  </div>
);

const ChartPage = () => {
  const { term } = useParams();
  const navigate = useNavigate();
  const [chart, setChart] = useState(null);
  const [error, setError] = useState(null);
  const [section, setSection] = useState('Summary');
  const [systemFilter, setSystemFilter] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [askOpen, setAskOpen] = useState(false);
  const [askRequest, setAskRequest] = useState(null);
  const [mineOnly, setMineOnly] = useState(false);
  const [askWidth, setAskWidth] = useState(432);
  const [analyte, setAnalyte] = useState(null);
  const viewer = JSON.parse(localStorage.getItem('user') || '{}').name;

  const load = useCallback(async () => {
    setChart(null);
    setError(null);
    try {
      const res = await axios.get(`${API}/chart`, { params: { term } });
      setChart(res.data);
    } catch (e) {
      setError(e.response?.status === 404
        ? { title: 'No patient found', body: `Nothing matches “${term}”. Check the ID or name and search again.` }
        : { title: 'The chart could not be loaded', body: 'The records service did not respond. Your sign-in is still valid.', retry: true });
    }
  }, [term]);

  useEffect(() => { setSection('Summary'); setSystemFilter(null); setAskOpen(false); window.scrollTo(0, 0); load(); }, [load]);
  // Highlight the section currently near the top of the window.
  useEffect(() => {
    if (!chart) return undefined;
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) setSection(e.target.dataset.section); }),
      { rootMargin: '-15% 0px -75% 0px' },
    );
    document.querySelectorAll('[data-section]').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [chart]);
  const goTo = (id) => document.getElementById(`section-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  // DocAssist drawer width: drag its left edge, or use the widen button.
  const resizeTo = (px) => setAskWidth(Math.round(Math.max(380, Math.min(px, window.innerWidth - 80, 1100))));
  const startResize = (e) => {
    e.preventDefault();
    const onMove = (ev) => resizeTo(window.innerWidth - ev.clientX);
    const onUp = () => { window.removeEventListener('pointermove', onMove); window.removeEventListener('pointerup', onUp); };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setAskOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  if (error) {
    return (
      <main className="max-w-xl mx-auto px-4 py-16 text-center" role="alert">
        <h2 className="text-lg font-semibold text-slate-900">{error.title}</h2>
        <p className="text-sm text-slate-600 mt-2">{error.body}</p>
        <div className="mt-4 flex justify-center gap-2">
          {error.retry && <Button onClick={load}>Try again</Button>}
          <Button variant="outline" onClick={() => navigate('/search')}>Back to search</Button>
        </div>
      </main>
    );
  }
  if (!chart) return <ChartSkeleton />;

  // Defaults keep the page usable against a backend that predates these fields.
  const { profile, findings = [], treatments = [], tumor_markers: markerNames = ['CEA', 'CA 15-3', 'PSA'],
    vitals = null, care_team: careTeam = [], problems = [],
    visits = [], medications = { current: [], history: [] }, upcoming = { items: [], note: '' },
    timeline, flowsheet, out_of_range: outOfRange, sources } = chart;
  const myVisits = visits.filter((v) => v.doctors.includes(viewer));
  const systems = [...new Set(timeline.map((i) => i.system))];
  const totalRecords = sources.reduce((n, s) => n + s.records, 0);
  const stamps = timeline.map((i) => ts(i.date));
  const domain = stamps.length ? [Math.min(...stamps), Math.max(...stamps)] : [0, 1];   // every chart shares this date axis
  const markers = flowsheet.rows.filter((r) => markerNames.includes(r.analyte));
  // Trend explorer: anything with two or more readings; opens on a value that is out of range if there is one.
  const explorable = flowsheet.rows.filter((r) => Object.keys(r.cells).length > 1);
  const explored = explorable.find((r) => r.analyte === analyte)
    || explorable.find((r) => outOfRange.some((o) => o.analyte === r.analyte)) || explorable[0];
  const images = timeline.filter((i) => IMAGE_DEPARTMENTS.includes(i.department));
  const lastImaging = images.find((i) => i.department !== 'ECG');
  const current = [...treatments].reverse().find((t) => t.status === 'In progress');
  const explain = () => { setAskOpen(true); setAskRequest({ id: Date.now(), text: SUMMARY_QUESTION }); };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-teal-50/40 to-sky-50" data-testid="chart-page">
      <div className="max-w-[1320px] mx-auto px-4 py-5 grid grid-cols-1 lg:grid-cols-[13rem_minmax(0,1fr)] gap-5 items-start">
        <aside className="lg:sticky lg:top-5 space-y-4">
          <nav aria-label="Chart sections" className="card-raised bg-white border border-slate-200/70 rounded-2xl p-2 flex lg:flex-col gap-1 overflow-x-auto">
            {SECTIONS.map(({ id, Icon }) => (
              <button
                key={id}
                onClick={() => goTo(id)}
                aria-current={section === id ? 'page' : undefined}
                className={`flex items-center gap-2.5 text-left text-sm px-3 py-2.5 rounded-xl whitespace-nowrap transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-700 ${
                  section === id ? 'bg-teal-700 text-white font-medium shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />{id}
              </button>
            ))}
            <button onClick={() => navigate('/search')} className="flex items-center gap-2.5 text-left text-sm px-3 py-2.5 rounded-xl text-slate-500 hover:bg-slate-100 whitespace-nowrap lg:mt-1 lg:border-t lg:border-slate-100 lg:rounded-t-none lg:pt-3">
              <Users className="w-4 h-4" aria-hidden="true" />Other patients
            </button>
          </nav>

          <div className="hidden lg:block card-raised rounded-2xl bg-slate-900 text-white p-4 relative overflow-hidden">
            <span className="absolute -top-8 -right-8 w-28 h-28 rounded-full bg-teal-400/20" aria-hidden="true" />
            <DocAssistOrb size={44} />
            <p className="text-sm font-semibold mt-3">DocAssist</p>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">Ask about this patient in plain language. Answers cite the records they used.</p>
            <button onClick={() => setAskOpen(true)} data-testid="open-docassist"
              className="mt-3 w-full inline-flex items-center justify-center gap-1.5 text-sm font-medium rounded-xl bg-white text-slate-900 px-3 py-2 hover:bg-teal-50">
              Ask a question<ArrowUpRight className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </aside>

        <main className="space-y-5 min-w-0">
          <PatientHero profile={profile} flagCount={outOfRange.length} />

          <Section id="Summary">
              <div className="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-4" data-testid="stat-boxes">
                <StatTile tone="rose" Icon={TriangleAlert} label="Lab values out of range" value={outOfRange.length ? `${outOfRange.length} to review` : 'None'}>
                  {outOfRange.length ? (
                    <div className="flex flex-wrap gap-1.5">
                      {outOfRange.map((o) => <span key={o.analyte} className="px-2 py-0.5 rounded-full bg-rose-100 text-rose-900">{o.analyte} {o.display} {RANGE_LETTER[o.status]}</span>)}
                    </div>
                  ) : 'All within reference range at the latest reading.'}
                </StatTile>
                <StatTile tone="sky" Icon={ScanLine} label="Latest imaging" value={lastImaging ? lastImaging.title : 'None on file'}>
                  {lastImaging && <>{lastImaging.result}<br /><span className="text-slate-500">{formatDate(lastImaging.date)}</span></>}
                </StatTile>
                <StatTile tone="violet" Icon={Stethoscope} label="Current therapy" value={current ? current.name : 'None in progress'}>
                  {current ? <>{current.category}<br /><span className="text-slate-500">Since {formatDate(current.date)}</span></> : profile.regimen}
                </StatTile>
                <StatTile tone="emerald" Icon={Database} label="Sources unified" value={`${sources.length} systems, ${totalRecords} records`}>
                  <div className="flex h-2 rounded-full overflow-hidden gap-0.5" aria-hidden="true">
                    {sources.map((s) => <span key={s.department} style={{ flex: s.records, background: SYSTEM_COLORS[s.system] }} />)}
                  </div>
                  <p className="mt-1.5">One chart from separate department systems (simulated).</p>
                </StatTile>
              </div>

              <Panel title="Key findings" note="Computed from the records, not written by AI"
                action={(
                  <button onClick={explain} data-testid="explain-with-ai"
                    className="inline-flex items-center gap-2 text-sm font-medium rounded-full pl-1.5 pr-4 py-1.5 bg-slate-900 text-white hover:bg-slate-800">
                    <DocAssistOrb size={26} />Explain with AI
                  </button>
                )}>
                {findings.length === 0 ? <Empty>Nothing out of range, modified or newly reported.</Empty> : (
                  <ul className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">{findings.map((f, i) => <FindingCard key={i} finding={f} />)}</ul>
                )}
              </Panel>

              {(vitals || careTeam.length > 0 || problems.length > 0) && (
                <div className="grid xl:grid-cols-2 gap-5">
                  {vitals && (
                    <Panel title="Vitals" note={`Recorded ${formatDate(vitals.recorded)}`}>
                      <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3" data-testid="vitals">
                        {[
                          [HeartPulse, 'Blood pressure', vitals.bp, 'mmHg'], [Activity, 'Pulse', vitals.pulse, 'bpm'],
                          [Thermometer, 'Temperature', vitals.temp_c, '°C'], [Wind, 'Oxygen saturation', vitals.spo2, '%'],
                          [Weight, 'Weight', vitals.weight_kg, 'kg'], [Ruler, 'Body surface area', vitals.bsa_m2, 'm²'],
                        ].map(([Icon, label, value, unit]) => (
                          <div key={label} className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2.5">
                            <dt className="flex items-center gap-1.5 text-xs text-slate-500"><Icon className="w-3.5 h-3.5 text-teal-700" aria-hidden="true" />{label}</dt>
                            <dd className="text-lg font-semibold text-slate-900 leading-tight mt-1 tabular-nums">{value} <span className="text-xs font-normal text-slate-500">{unit}</span></dd>
                          </div>
                        ))}
                      </dl>
                    </Panel>
                  )}
                  {(careTeam.length > 0 || problems.length > 0) && (
                    <Panel title="Care team and problem list">
                      {careTeam.length > 0 && (
                        <ul className="grid sm:grid-cols-2 gap-2" data-testid="care-team">
                          {careTeam.map((m) => (
                            <li key={m.role} className="flex items-center gap-2.5">
                              <span className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold ${m.name === viewer ? 'bg-teal-700 text-white' : 'bg-slate-100 text-slate-700'}`} aria-hidden="true">
                                {m.name.replace(/^(Dr\.|Nurse)\s/, '').slice(0, 1)}
                              </span>
                              <span className="min-w-0">
                                <span className="block text-sm font-medium text-slate-900">{m.name}{m.name === viewer ? ' (you)' : ''}</span>
                                <span className="block text-xs text-slate-500">{m.role}</span>
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                      {problems.length > 0 && (
                        <div className={careTeam.length > 0 ? 'mt-4 pt-4 border-t border-slate-100' : ''}>
                          <p className="text-xs font-medium text-slate-500 mb-2">Problems stated in the record</p>
                          <ul className="flex flex-wrap gap-2" data-testid="problem-list">
                            {problems.map((p) => (
                              <li key={p.label} title={p.source} className="text-sm px-3 py-1 rounded-full bg-amber-50 text-amber-900 border border-amber-200">{p.label}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </Panel>
                  )}
                </div>
              )}

              <div className="grid xl:grid-cols-2 gap-5">
                {markers.length > 0 && (
                  <Panel title="Tumor marker" note="Against the full treatment course">
                    <div className="grid gap-6">{markers.map((row) => <LabTrendChart key={row.analyte} row={row} domain={domain} events={treatments} height={210} />)}</div>
                  </Panel>
                )}
                {flowsheet.rows.length > 0 && (
                  <Panel title="Latest lab values" note="Where each value sits against its reference range">
                    <div className="divide-y divide-slate-100">{flowsheet.rows.map((row) => <RangeGauge key={row.analyte} row={row} />)}</div>
                  </Panel>
                )}
              </div>
          </Section>

          <Section id="Labs">
              {explorable.length > 0 && (
                <Panel title="Trend explorer" note="Pick a value to see it against the treatment course"
                  action={(
                    <div className="flex flex-wrap gap-1.5" role="group" aria-label="Lab value to chart">
                      {explorable.map((row) => {
                        const latest = row.cells[Object.keys(row.cells).sort().pop()];
                        return (
                          <button key={row.analyte} onClick={() => setAnalyte(row.analyte)} aria-pressed={explored.analyte === row.analyte}
                            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${explored.analyte === row.analyte ? 'bg-teal-700 text-white border-teal-700' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'}`}>
                            {row.analyte}{latest.status !== 'IN RANGE' ? ` ${RANGE_LETTER[latest.status]}` : ''}
                          </button>
                        );
                      })}
                    </div>
                  )}>
                  <LabTrendChart key={explored.analyte} row={explored} domain={domain} events={treatments} height={260} />
                </Panel>
              )}
              <Panel title="Lab flowsheet" note="L marks a value below range, H a value above range">
                <Flowsheet flowsheet={flowsheet} />
              </Panel>
          </Section>

          <Section id="Imaging">
            <Panel title="Imaging and tracings" note="MRI, CT, X-ray and ECG. Select one to enlarge.">
              <ImageGallery items={images} onOpen={setViewing} />
            </Panel>
          </Section>

          <Section id="Treatment">
              <Panel title="Treatment course" note={`${treatments.length} entries from the Treatment system`}>
                <TreatmentTimeline treatments={treatments} />
              </Panel>
          </Section>

          <Section id="Medications">
              <Panel title="Current medications" note="From treatment still in progress">
                {medications.current.length === 0 ? <Empty>No medication is recorded as in progress.</Empty> : (
                  <ul className="grid sm:grid-cols-2 gap-4" data-testid="current-medications">
                    {medications.current.map((m) => (
                      <li key={m.name} className="card-raised lift rounded-2xl border border-violet-100 bg-gradient-to-br from-violet-50 to-white p-4 flex gap-3">
                        <span className="w-10 h-10 rounded-xl bg-violet-600 text-white flex items-center justify-center shrink-0"><Pill className="w-5 h-5" aria-hidden="true" /></span>
                        <div>
                          <p className="text-base font-semibold text-slate-900">{m.name}</p>
                          <p className="text-sm text-slate-700">{m.dose}</p>
                          <p className="text-xs text-slate-500 mt-1">Since {formatDate(m.since)} · {m.for}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
              <Panel title="Medication history" note="Every drug written on a treatment record, most recent first">
                {medications.history.length === 0 ? <Empty>No medications on record.</Empty> : (
                  <div className="overflow-x-auto rounded-xl border border-slate-200">
                    <table className="w-full text-sm" data-testid="medication-history">
                      <thead>
                        <tr className="text-left text-xs text-slate-600 bg-slate-50">
                          <th scope="col" className="py-2.5 px-4 font-medium">Medication</th>
                          <th scope="col" className="py-2.5 px-3 font-medium">Last dose</th>
                          <th scope="col" className="py-2.5 px-3 font-medium">Last given</th>
                          <th scope="col" className="py-2.5 px-3 font-medium text-right">Times given</th>
                          <th scope="col" className="py-2.5 px-4 font-medium">Given for</th>
                        </tr>
                      </thead>
                      <tbody>
                        {medications.history.map((m) => (
                          <tr key={m.name} className="border-t border-slate-100 hover:bg-slate-50/60">
                            <th scope="row" className="py-2.5 px-4 text-left font-semibold text-slate-900">{m.name}</th>
                            <td className="py-2.5 px-3 text-slate-700">{m.last_dose}</td>
                            <td className="py-2.5 px-3 text-slate-700 whitespace-nowrap">{formatDate(m.last_given)}</td>
                            <td className="py-2.5 px-3 text-right tabular-nums">{m.times_given}</td>
                            <td className="py-2.5 px-4 text-slate-600">{m.last_for}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>
          </Section>

          <Section id="Visits">
              <Panel title="Next expected doses" note="Estimated from the treatment schedule">
                {upcoming.items.length > 0 && (
                  <ul className="grid sm:grid-cols-2 gap-4 mb-3" data-testid="upcoming-estimates">
                    {upcoming.items.map((u) => (
                      <li key={u.date} className="flex gap-4 rounded-2xl border border-dashed border-teal-300 bg-teal-50/60 p-4">
                        <DateBlock date={u.date} tone="teal" />
                        <div>
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-white text-teal-800 border border-teal-200">
                            <CalendarClock className="w-3 h-3" aria-hidden="true" />Estimate
                          </span>
                          <p className="text-sm font-semibold text-slate-900 mt-1.5">{u.title}</p>
                          <p className="text-xs text-slate-600">{u.basis}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="text-sm text-slate-600 flex items-start gap-2">
                  <TriangleAlert className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" aria-hidden="true" />{upcoming.note}
                </p>
              </Panel>
              <Panel title="Visits" note="Each date with records is one visit"
                action={(
                  <div className="inline-flex rounded-full bg-slate-100 p-1" role="group" aria-label="Which visits to show">
                    {[[false, `All visits (${visits.length})`], [true, `My consultations (${myVisits.length})`]].map(([mine, label]) => (
                      <button key={label} onClick={() => setMineOnly(mine)} aria-pressed={mineOnly === mine}
                        className={`text-xs px-3 py-1.5 rounded-full transition-colors ${mineOnly === mine ? 'bg-white text-slate-900 font-medium shadow-sm' : 'text-slate-600'}`}>
                        {label}
                      </button>
                    ))}
                  </div>
                )}>
                <VisitList visits={mineOnly ? myVisits : visits} viewer={viewer} />
              </Panel>
          </Section>

          <Section id="Timeline">
              <Panel title="All systems over time" note={`${sources.length} department systems (simulated), ${totalRecords} records. Select a point to read that record.`}>
                <SystemsTimeline timeline={timeline} domain={domain} />
              </Panel>
              <Panel title="Every record" note="Newest first">
                <div className="flex flex-wrap gap-2 mb-4" role="group" aria-label="Filter by source system">
                  {[null, ...systems].map((s) => (
                    <button
                      key={s || 'all'}
                      onClick={() => setSystemFilter(s)}
                      aria-pressed={systemFilter === s}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${systemFilter === s ? 'bg-teal-700 text-white border-teal-700' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'}`}
                    >
                      {s || 'All systems'}
                    </button>
                  ))}
                </div>
                <RecordList items={systemFilter ? timeline.filter((i) => i.system === systemFilter) : timeline} />
              </Panel>
          </Section>
        </main>
      </div>

      {/* Floating DocAssist button on narrow screens, where the sidebar card is hidden */}
      {!askOpen && (
        <button onClick={() => setAskOpen(true)} data-testid="docassist-fab" aria-label="Ask DocAssist"
          className="lg:hidden fixed bottom-6 right-6 z-30 inline-flex items-center gap-3 rounded-full bg-slate-900 text-white pl-2 pr-5 py-2 shadow-2xl hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700">
          <DocAssistOrb size={40} />
          <span className="text-left leading-tight">
            <span className="block text-sm font-semibold">Ask DocAssist</span>
            <span className="block text-[11px] text-slate-300">About {profile.name.split(' ')[0]}'s chart</span>
          </span>
        </button>
      )}

      {/* DocAssist drawer: always mounted so a conversation survives closing it */}
      {askOpen && <div className="fixed inset-0 z-30 bg-slate-900/30 backdrop-blur-[2px]" onClick={() => setAskOpen(false)} aria-hidden="true" />}
      <aside
        role="dialog" aria-label="DocAssist" aria-hidden={!askOpen}
        className={`fixed top-0 right-0 z-40 h-full max-w-full bg-white shadow-2xl transition-transform duration-300 ${askOpen ? 'translate-x-0' : 'translate-x-full invisible'}`}
        style={{ width: askWidth }}
        data-testid="docassist-drawer"
      >
        <div
          role="separator" aria-orientation="vertical" aria-label="Resize DocAssist. Drag, or use the left and right arrow keys." tabIndex={0}
          onPointerDown={startResize}
          onKeyDown={(e) => { if (e.key === 'ArrowLeft') resizeTo(askWidth + 60); if (e.key === 'ArrowRight') resizeTo(askWidth - 60); }}
          className="group absolute left-0 top-0 z-20 h-full w-3 -ml-1.5 cursor-ew-resize flex items-center justify-center focus-visible:outline-none"
          data-testid="docassist-resize"
        >
          <span className="h-14 w-1.5 rounded-full bg-slate-300 group-hover:bg-teal-600 group-focus-visible:bg-teal-600 transition-colors" />
        </div>
        <button onClick={() => resizeTo(askWidth > 500 ? 432 : window.innerWidth * 0.6)} aria-label={askWidth > 500 ? 'Narrow DocAssist' : 'Widen DocAssist'}
          className="absolute top-4 right-12 z-10 p-1.5 rounded-full text-white/80 hover:bg-white/15" data-testid="docassist-widen">
          {askWidth > 500 ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>
        <button onClick={() => setAskOpen(false)} aria-label="Close DocAssist" className="absolute top-4 right-4 z-10 p-1.5 rounded-full text-white/80 hover:bg-white/15">
          <X className="w-4 h-4" />
        </button>
        <AskPanel patientId={profile.patient_id} patientName={profile.name} request={askRequest} />
      </aside>

      <Dialog open={!!viewing} onOpenChange={(open) => !open && setViewing(null)}>
        <DialogContent className="max-w-4xl">
          {viewing && (
            <>
              <DialogHeader>
                <DialogTitle className="text-base">{viewing.title} · {formatDate(viewing.date)}</DialogTitle>
              </DialogHeader>
              <div className="grid md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] gap-4">
                <div className="bg-slate-900 rounded-xl flex items-center justify-center min-h-[16rem] overflow-hidden">
                  {viewing.image ? <img src={viewing.image} alt={`${viewing.title} report`} className="max-h-[70vh] w-auto object-contain" />
                    : <span className="text-sm text-slate-400">No image attached</span>}
                </div>
                <div className="text-sm space-y-2">
                  <SystemTag system={viewing.system} />
                  <p className="text-slate-900">{viewing.result}</p>
                  <p className="text-slate-500">Reported by {viewing.doctor}</p>
                  <p className="text-xs text-slate-500">Illustrative image for synthetic data.</p>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ChartPage;
