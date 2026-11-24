import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { ExternalLink, FlaskConical, RotateCcw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
// The tumour review desk runs only on this computer (scans never leave it), so this works when the portal does too.
const DESK = process.env.REACT_APP_REVIEW_DESK || 'http://127.0.0.1:8765';

const noteText = (c) => {
  const r = c.review;
  return [
    `Tumour outline (RESEARCH DRAFT, public demo scan ${c.demo_scan}, not this patient's own CT): ` +
      `${r.decision} by ${r.reviewer || 'unnamed reviewer'} on ${r.signed}, at ${Math.round(r.cut * 100)}% sureness.`,
    c.volume_cc != null && `AI outline: ${c.volume_cc} cc, ${c.size_mm.join(' x ')} mm.`,
    r.note && `Reviewer's note: ${r.note}`,
    `Reviewed in the local tumour review desk, case ${c.id}.`,
  ].filter(Boolean).join('\n');
};

// "Tumour outline (research)": opens the local review desk for this patient and shows its sign-off.
const TumourOutline = ({ patientId, onSaved }) => {
  const [cases, setCases] = useState(null);       // null = asking, 'off' = desk not running
  const [saved, setSaved] = useState({});
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setCases(null);
    fetch(`${DESK}/api/portal/${encodeURIComponent(patientId)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setCases)
      .catch(() => setCases('off'));
  }, [patientId]);
  useEffect(load, [load]);

  const save = async (c) => {
    setError('');
    try {
      const { data } = await axios.post(`${API}/chart-notes/${patientId}`, { text: noteText(c), reviewed: true });
      setSaved((s) => ({ ...s, [c.id]: true }));
      onSaved?.(data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not save to the chart.');
    }
  };

  const latest = Array.isArray(cases) ? cases[0] : null;
  return (
    <section className="card-raised bg-white border border-slate-200/70 rounded-2xl mt-4" data-testid="tumour-outline">
      <header className="px-5 pt-4 pb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div>
          <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-amber-700" aria-hidden="true" />Tumour outline (research)
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">AI lung tumour outline, reviewed by a doctor. Uses a public demo scan until the hospital approves.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50">
            <RotateCcw className="w-4 h-4" aria-hidden="true" />Refresh
          </button>
          <a href={`${DESK}/?portal=${encodeURIComponent(patientId)}`} target="_blank" rel="noopener noreferrer" data-testid="open-review-desk"
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-xl bg-teal-700 text-white hover:bg-teal-800">
            <ExternalLink className="w-4 h-4" aria-hidden="true" />Open review desk
          </a>
        </div>
      </header>
      <div className="px-5 pb-5 text-sm" role="status">
        {cases === null && <p className="text-slate-500">Checking the review desk…</p>}
        {cases === 'off' && (
          <p className="text-slate-600">The review desk is not running on this computer. Start it with
            <code className="mx-1 px-1.5 py-0.5 rounded bg-slate-100 text-xs">.venv/bin/python prototype/server.py</code>
            in <code className="px-1.5 py-0.5 rounded bg-slate-100 text-xs">research/tumor-ai</code>, then press Refresh.</p>
        )}
        {Array.isArray(cases) && !latest && <p className="text-slate-600">No outline yet. Open the review desk to start one.</p>}
        {latest && !latest.review && (
          <p className="text-slate-600">{latest.state === 'done' ? 'Outline ready, waiting for a doctor to sign it off in the review desk.' : 'The AI is outlining the demo scan…'}</p>
        )}
        {latest?.review && (
          <div className="space-y-2">
            <p className="text-slate-900">
              <span className="font-semibold capitalize">{latest.review.decision}</span> by {latest.review.reviewer || 'unnamed reviewer'}, {latest.review.signed},
              at {Math.round(latest.review.cut * 100)}% sureness{latest.volume_cc != null && <> · {latest.volume_cc} cc, {latest.size_mm.join(' × ')} mm</>}
            </p>
            {latest.review.note && <p className="text-slate-600">“{latest.review.note}”</p>}
            <p className="text-xs text-amber-800">Demo scan {latest.demo_scan} (public data), not this patient's own CT.</p>
            <button onClick={() => save(latest)} disabled={saved[latest.id]} data-testid="save-outline-note"
              className="text-sm px-3 py-1.5 rounded-xl border border-teal-700 text-teal-800 hover:bg-teal-50 disabled:opacity-60">
              {saved[latest.id] ? 'Saved to the chart' : 'Save sign-off to the chart'}
            </button>
            {error && <p className="text-rose-800">{error}</p>}
          </div>
        )}
      </div>
    </section>
  );
};

export default TumourOutline;
