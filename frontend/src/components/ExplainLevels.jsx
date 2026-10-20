import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FlaskConical, RefreshCw, Stethoscope, TriangleAlert, User, Dna } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const ICONS = { patient: User, physician: Stethoscope, lab: FlaskConical, drug: Dna };

// The patient's main finding for four readers. All four come from one fact sheet built
// from the record; every number is checked against it on the server.
const ExplainLevels = ({ patientId, open, onOpenChange }) => {
  const [data, setData] = useState(null);
  const [level, setLevel] = useState('patient');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = (refresh = false) => {
    setLoading(true);
    setError(null);
    axios.get(`${API}/explain-levels/${patientId}`, { params: { refresh } })
      .then((res) => setData(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'The explanation could not be loaded.'))
      .finally(() => setLoading(false));
  };
  useEffect(() => { if (open && !data) load(); }, [open]);
  useEffect(() => { setData(null); setLevel('patient'); }, [patientId]);

  const current = data?.levels.find((l) => l.id === level);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[88vh] overflow-y-auto" data-testid="explain-levels">
        <DialogHeader>
          <DialogTitle>One finding, four explanations</DialogTitle>
          <p className="text-sm text-slate-500">The same facts from the record, explained for different readers.</p>
        </DialogHeader>
        {loading && <p className="text-sm text-slate-500 py-8 text-center" role="status">Writing the four explanations…</p>}
        {error && <p role="alert" className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-xl px-3.5 py-2.5">{error}</p>}
        {data && !loading && (
          <>
            <div role="tablist" className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {data.levels.map((l) => {
                const Icon = ICONS[l.id];
                return (
                  <button key={l.id} role="tab" aria-selected={level === l.id} onClick={() => setLevel(l.id)} data-testid={`level-${l.id}`}
                    className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-left text-sm font-medium ${level === l.id ? 'bg-teal-700 text-white border-teal-700' : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'}`}>
                    <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />{l.label}
                  </button>
                );
              })}
            </div>
            {current && (
              <div role="tabpanel" className="rounded-2xl border border-slate-200 bg-white p-4" data-testid="level-text">
                <p className="text-xs text-slate-500">Written for {current.audience}</p>
                <div className="mt-2 space-y-2 text-[15px] leading-relaxed text-slate-800">
                  {current.text.split(/(?<=\.)\s+(?=(?:Patient-specific|Background):)/).map((part) => (
                    <p key={part}>{part.split(/^(Patient-specific:|Background:)/).map((bit, k) => (k === 1
                      ? <b key={k} className={bit.startsWith('Patient') ? 'text-teal-800' : 'text-slate-500'}>{bit} </b> : bit))}</p>
                  ))}
                </div>
                {current.notes.map((n) => (
                  <p key={n} className="mt-3 flex gap-1.5 text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5">
                    <TriangleAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" aria-hidden="true" />{n}
                  </p>
                ))}
                {current.id === 'patient' && (
                  <p className="mt-3 text-xs text-slate-500">For the care team to review before sharing with the patient.</p>
                )}
              </div>
            )}
            <details className="text-sm text-slate-700">
              <summary className="cursor-pointer font-medium text-teal-800">Facts used ({data.facts.length})</summary>
              <ul className="mt-2 space-y-1">
                {data.facts.map((f) => (
                  <li key={f.label} className="rounded-lg bg-slate-50 px-2.5 py-1.5"><b className="font-medium">{f.label}:</b> {f.value} <span className="text-slate-400">· {f.source}</span></li>
                ))}
              </ul>
            </details>
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
              <span>{data.source === 'model' ? `Written by AI (${data.model}) from the facts above. Every number is checked against them.` : 'Saved, pre-checked version, shown because the AI model was slow or unavailable.'}</span>
              <button onClick={() => load(true)} className="inline-flex items-center gap-1 text-teal-800 hover:underline"><RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />Write again</button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ExplainLevels;
