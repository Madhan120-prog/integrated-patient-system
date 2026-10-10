import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { ArrowRight, Mic, Search } from 'lucide-react';
import { Dialog, DialogContent, DialogTitle } from './ui/dialog';
import AskPanel from './AskPanel';
import { DocAssistOrb } from './ChartVisuals';
import { useDictation } from '../hooks/useVoice';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const IMAGE_DEPARTMENTS = ['MRI', 'CT Scan', 'X-Ray', 'ECG'];

// DocAssist opened from the landing page: choose a patient, then the same
// conversation as the chart drawer (one assistant, one set of abilities).
const DocAssistDialog = ({ open, onClose }) => {
  const [term, setTerm] = useState('');
  const [chart, setChart] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const dictation = useDictation(setTerm);

  useEffect(() => { if (!open) { setTerm(''); setChart(null); setError(''); } }, [open]);

  const find = async (e) => {
    e.preventDefault();
    if (!term.trim() || loading) return;
    setLoading(true);
    setError('');
    try {
      const res = await axios.get(`${API}/chart`, { params: { term: term.trim() } });
      setChart(res.data);
    } catch (err) {
      setError(err.response?.status === 404 ? `No patient matches “${term.trim()}”. Check the ID or name.` : 'The records service did not respond. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className={`p-0 overflow-hidden gap-0 [&>button]:z-20 ${chart ? 'max-w-3xl h-[85vh] [&>button]:text-white' : 'max-w-lg [&>button]:text-white'}`} data-testid="docassist-dialog">
        <DialogTitle className="sr-only">DocAssist</DialogTitle>
        {chart ? (
          <div className="relative h-full min-h-0">
            <AskPanel patientId={chart.profile.patient_id} patientName={chart.profile.name}
              images={chart.timeline.filter((i) => IMAGE_DEPARTMENTS.includes(i.department))} />
            <button onClick={() => setChart(null)} className="absolute top-4 right-12 z-20 text-xs font-medium rounded-full px-3 py-1.5 bg-white/10 text-white hover:bg-white/20">
              Change patient
            </button>
          </div>
        ) : (
          <div>
            <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-900 to-teal-900 text-white px-6 py-6">
              <span className="absolute -top-10 -right-6 w-40 h-40 rounded-full bg-teal-400/15" aria-hidden="true" />
              <div className="relative flex items-center gap-3">
                <DocAssistOrb size={52} />
                <div>
                  <h2 className="text-lg font-semibold">DocAssist Clinical Assistant</h2>
                  <p className="text-sm text-slate-300">Which patient is this about?</p>
                </div>
              </div>
            </div>
            <form onSubmit={find} className="p-6 space-y-3">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" aria-hidden="true" />
                  <input autoFocus value={term} onChange={(e) => setTerm(e.target.value)} aria-label="Patient ID or name" data-testid="docassist-patient-input"
                    placeholder={dictation.listening ? 'Listening… say the name or ID' : 'Patient ID (P1001) or name'}
                    className={`w-full h-12 rounded-full bg-slate-100 pl-11 pr-4 text-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-600 ${dictation.listening ? 'ring-2 ring-rose-400' : ''}`} />
                </div>
                <button type="button" onClick={dictation.toggle} aria-pressed={dictation.listening} aria-label={dictation.listening ? 'Stop dictation' : 'Say the patient name or ID'}
                  className={`relative w-12 h-12 rounded-full flex items-center justify-center shrink-0 ${dictation.listening ? 'mic-live bg-rose-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                  <Mic className="relative w-4 h-4" />
                </button>
              </div>
              {(error || dictation.error) && <p role="alert" className="text-sm text-amber-800">{error || dictation.error}</p>}
              <button type="submit" disabled={loading || !term.trim()}
                className="w-full h-12 rounded-full bg-teal-700 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 hover:bg-teal-800 disabled:opacity-40">
                {loading ? 'Opening…' : 'Start'}<ArrowRight className="w-4 h-4" aria-hidden="true" />
              </button>
              <p className="text-xs text-slate-500">Ask about results, pull up a scan, attach a report or a visit recording. AI-assisted; verify against the record.</p>
            </form>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default DocAssistDialog;
