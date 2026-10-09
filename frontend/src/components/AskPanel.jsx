import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { FlaskConical, ListChecks, Send, TriangleAlert } from 'lucide-react';
import { MessageContent } from './DeepSearchModal';
import { DocAssistOrb } from './ChartVisuals';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SUGGESTIONS = [
  { Icon: TriangleAlert, title: "What's concerning?", hint: 'Values out of range and stated findings' },
  { Icon: ListChecks, title: 'What changed since the last visit?', hint: 'New results compared with earlier ones' },
  { Icon: FlaskConical, title: 'Summarize the blood work.', hint: 'Counts, markers and their trends' },
];

// Long dashes read as noise on screen; answers and warnings use a colon instead.
const tidy = (text) => text.replace(/\s+—\s+/g, ': ').replace(/—/g, ', ');

// One clear sentence per failure the user can actually act on.
const explain = (error) => {
  const status = error.response?.status;
  const role = JSON.parse(localStorage.getItem('user') || '{}').role;
  if (status === 403) return `DocAssist answers are limited to physician accounts${role ? ` (you are signed in as ${role.toLowerCase()})` : ''}. The chart itself is fully available.`;
  if (status === 429 || status === 503) return error.response.data?.detail || 'The AI model is unavailable right now. The chart itself is unaffected.';
  if (!error.response) return 'The AI service did not respond. Check the connection and try again.';
  return 'The question could not be answered. Try rephrasing it.';
};

// DocAssist inside the chart: same /deep-query endpoint as the full-screen
// assistant, scoped to the open patient. No automatic first question, so
// opening a chart never spends an AI request.
const AskPanel = ({ patientId, patientName, request }) => {
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { setMessages([]); setHistory([]); setQuestion(''); }, [patientId]);
  useEffect(() => { endRef.current?.scrollIntoView?.({ block: 'nearest' }); }, [messages, loading]);
  // A question sent from the page (e.g. "Explain with AI"); request.id changes per click.
  useEffect(() => { if (request) ask(request.text); }, [request?.id]);

  const ask = async (text) => {
    if (!text.trim() || loading) return;
    setMessages((m) => [...m, { role: 'user', content: text }]);
    setQuestion('');
    setLoading(true);
    try {
      const res = await axios.post(`${API}/deep-query`, {
        patient_id: patientId, question: text, conversation_history: history.slice(-6),
      });
      setMessages((m) => [...m, { role: 'assistant', content: res.data.answer, evidence: res.data.evidence }]);
      setHistory((h) => [...h, { role: 'user', content: text }, { role: 'assistant', content: res.data.answer }]);
    } catch (e) {
      setMessages((m) => [...m, { role: 'error', content: explain(e) }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="flex flex-col h-full bg-slate-50" data-testid="ask-panel">
      <header className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-900 to-teal-900 text-white px-5 py-5">
        <span className="absolute -top-10 -right-6 w-40 h-40 rounded-full bg-teal-400/15" aria-hidden="true" />
        <div className="relative flex items-center gap-3">
          <DocAssistOrb size={48} />
          <div>
            <h3 className="text-base font-semibold">DocAssist</h3>
            <p className="text-xs text-slate-300">Reading {patientName}'s chart</p>
          </div>
        </div>
        <p className="relative text-xs text-slate-300 mt-3">AI-assisted. Verify against the record before acting.</p>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-3" aria-live="polite">
        {messages.length === 0 && (
          <div className="space-y-2">
            <p className="text-sm text-slate-600 mb-3">Pick a starting point, or type your own question below.</p>
            {SUGGESTIONS.map(({ Icon, title, hint }) => (
              <button key={title} onClick={() => ask(title)} disabled={loading}
                className="card-raised lift w-full flex items-center gap-3 text-left rounded-2xl bg-white border border-slate-200 px-4 py-3 disabled:opacity-50">
                <span className="w-9 h-9 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center shrink-0"><Icon className="w-4 h-4" aria-hidden="true" /></span>
                <span>
                  <span className="block text-sm font-medium text-slate-900">{title}</span>
                  <span className="block text-xs text-slate-500">{hint}</span>
                </span>
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => m.role === 'user' ? (
          <div key={i} className="flex justify-end rise-in">
            <p className="max-w-[85%] text-sm text-white bg-teal-700 rounded-2xl rounded-br-md px-3.5 py-2">{m.content}</p>
          </div>
        ) : m.role === 'error' ? (
          <p key={i} role="alert" className="rise-in text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-2xl px-3.5 py-2.5">{m.content}</p>
        ) : (
          <div key={i} className="flex gap-2 rise-in">
            <DocAssistOrb size={26} />
            <div className="flex-1 min-w-0 text-sm text-slate-800 bg-white border border-slate-200 rounded-2xl rounded-tl-md px-3.5 py-2.5 card-raised">
              <MessageContent text={tidy(m.content)} />
              {m.evidence?.length > 0 && (
                <details className="mt-2 text-xs text-slate-600">
                  <summary className="cursor-pointer font-medium text-teal-800">Records used ({m.evidence.length})</summary>
                  <ul className="mt-1.5 space-y-1">
                    {m.evidence.map((ev, j) => (
                      <li key={j} className="rounded-lg bg-slate-50 px-2 py-1">{ev.test_date || ev.treatment_date} · {ev.test_name || ev.treatment_name}: {tidy(ev.result)}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2" role="status" aria-label="DocAssist is reading the chart">
            <DocAssistOrb size={26} />
            <span className="flex gap-1 bg-white border border-slate-200 rounded-2xl px-3.5 py-3">
              {[0, 1, 2].map((n) => <span key={n} className="typing-dot w-1.5 h-1.5 rounded-full bg-slate-500" style={{ animationDelay: `${n * 0.15}s` }} />)}
            </span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form className="p-3 bg-white border-t border-slate-200 flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about results, treatment or history" aria-label="Question about this patient"
          className="flex-1 h-11 rounded-full bg-slate-100 px-4 text-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-600" />
        <button type="submit" disabled={loading || !question.trim()} aria-label="Send question"
          className="w-11 h-11 rounded-full bg-teal-700 text-white flex items-center justify-center hover:bg-teal-800 disabled:opacity-40">
          <Send className="w-4 h-4" />
        </button>
      </form>
    </section>
  );
};

export default AskPanel;
