import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { FileText, FlaskConical, Image as ImageIcon, Info, ListChecks, Mic, Paperclip, ScanLine, Send, Square, TriangleAlert, Volume2, VolumeX, X } from 'lucide-react';
import { MessageContent } from './DeepSearchModal';
import { DocAssistOrb, formatDate } from './ChartVisuals';
import { useDictation, useSpeaker } from '../hooks/useVoice';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SUGGESTIONS = [
  { Icon: TriangleAlert, title: "What's concerning?", hint: 'Values out of range and stated findings' },
  { Icon: ListChecks, title: 'What changed since the last visit?', hint: 'New results compared with earlier ones' },
  { Icon: FlaskConical, title: 'Summarize the blood work.', hint: 'Counts, markers and their trends' },
  { Icon: ScanLine, title: 'Pull up the most recent scan.', hint: 'Shows it here, then offers to analyze the image' },
];

// "Ask about this section": which department systems a section draws on.
export const SECTION_SCOPE = {
  Labs: ['Blood Profile'],
  Imaging: ['MRI', 'CT Scan', 'X-Ray', 'ECG'],
  Treatment: ['Treatment'],
};

// "Pull up the latest chest x-ray" is a request to show a study, not a question
// for the model. It is answered from the chart, and analysis is offered, not assumed.
const SHOW_STUDY_RE = /\b(pull up|bring up|show|open|display|find|get)\b[^.?!]*\b(scans?|imaging|images?|x-?rays?|mri|ct|ecg)\b/i;
const MODALITY = [[/\bmri\b/i, 'MRI'], [/\bct\b/i, 'CT Scan'], [/\bx-?rays?\b/i, 'X-Ray'], [/\becg\b/i, 'ECG']];
const findStudy = (text, images) => {
  if (!SHOW_STUDY_RE.test(text)) return undefined;
  const wanted = MODALITY.find(([re]) => re.test(text))?.[1];
  return images.find((i) => (wanted ? i.department === wanted : i.department !== 'ECG')) || null;   // images are newest first
};

const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const AUDIO_TYPES = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/mp4', 'audio/m4a', 'audio/x-m4a', 'audio/aac', 'audio/webm', 'audio/ogg'];
const isAudio = (file) => AUDIO_TYPES.includes(file.type);
const ATTACH_OPTIONS = [
  { Icon: ImageIcon, label: 'Photo or scan', hint: 'PNG, JPEG or WebP', accept: IMAGE_TYPES.join(',') },
  { Icon: FileText, label: 'File', hint: 'PDF report or letter', accept: 'application/pdf' },
  { Icon: Mic, label: 'Recording', hint: 'Visit audio: MP3, M4A or WAV', accept: 'audio/*',
    info: 'A recorded visit is transcribed, each voice is labelled Doctor or Patient for the whole conversation, and you can then ask questions about what was said. Labels are assigned by AI, so check them.' },
];
const SPEAKER_STYLE = { Doctor: 'bg-teal-700 text-white', Patient: 'bg-slate-200 text-slate-900' };
const transcriptText = (t) => t.segments.map((seg) => `(${seg.start}) ${seg.speaker}: ${seg.text}`).join('\n');

// Long dashes read as noise on screen; answers and warnings use a colon instead.
const tidy = (text) => text.replace(/\s+—\s+/g, ': ').replace(/—/g, ', ');

// One clear sentence per failure the user can actually act on.
const explain = (error) => {
  const status = error.response?.status;
  const role = JSON.parse(localStorage.getItem('user') || '{}').role;
  if (status === 403) return `DocAssist answers are limited to physician accounts${role ? ` (you are signed in as ${role.toLowerCase()})` : ''}. The chart itself is fully available.`;
  if (status === 404 && error.response.data?.detail === 'Not Found') return 'The running server does not have this feature yet. Restart the backend and try again.';
  if ([404, 429, 502, 503].includes(status)) return error.response.data?.detail || 'The AI model is unavailable right now. The chart itself is unaffected.';
  if (!error.response) return 'The AI service did not respond. Check the connection and try again.';
  return 'The request could not be completed. Try rephrasing it.';
};

// DocAssist inside the chart. Three ways to give it something to work on, all
// ending in the same conversation:
//   1. type a question (optionally scoped to one chart section),
//   2. ask it to pull up a study, or drag one in from the Imaging section,
//   3. attach or drop a file.
// A study or file is shown first; the image is analyzed only when the doctor says so.
const AskPanel = ({ patientId, patientName, images = [], request }) => {
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [attachOpen, setAttachOpen] = useState(false);
  const [infoFor, setInfoFor] = useState(null);
  const [transcript, setTranscript] = useState(null);   // set while questions are about a recording
  const endRef = useRef(null);
  const fileRef = useRef(null);
  const push = (m) => setMessages((all) => [...all, m]);
  const speaker = useSpeaker();
  const dictation = useDictation(setQuestion);
  // An answer appears on screen (already through the safety checks) and, if voice is on, is spoken at once.
  const answer = (m) => { push({ role: 'assistant', ...m }); if (speaker.enabled) speaker.speak(m.content); };

  useEffect(() => { setMessages([]); setHistory([]); setQuestion(''); setScope(null); setTranscript(null); speaker.stop(); }, [patientId]);
  useEffect(() => { endRef.current?.scrollIntoView?.({ block: 'nearest' }); }, [messages, loading]);
  // Something sent from the chart page; request.id changes per click.
  useEffect(() => {
    if (!request) return;
    if (request.scope) setScope(request.scope);
    if (request.study) offerStudy(request.study, 'Here is that study.');
    if (request.text) ask(request.text);
  }, [request?.id]);

  const offerStudy = (study, lead) => push({ role: 'offer', study, lead });
  const offerFile = (file) => {
    if (![...IMAGE_TYPES, 'application/pdf'].includes(file.type) && !isAudio(file)) {
      push({ role: 'error', content: 'That file type is not supported. Attach an image, a PDF or an audio recording.' });
    } else if (file.size > (isAudio(file) ? 15 : 10) * 1024 * 1024) {
      push({ role: 'error', content: `That file is larger than ${isAudio(file) ? 15 : 10} MB.` });
    } else {
      push({ role: 'offer', file, lead: isAudio(file) ? 'Recording received.' : 'File received.' });
    }
  };

  const ask = async (text) => {
    if (!text.trim() || loading) return;
    speaker.stop();
    push({ role: 'user', content: text, scope });
    setQuestion('');
    const study = findStudy(text, images);
    if (study !== undefined) {
      if (study) offerStudy(study, 'Here is the most recent one on file.');
      else push({ role: 'error', content: 'There is no study of that kind on file for this patient.' });
      return;
    }
    setLoading(true);
    if (transcript) {   // questions go to the recording until its chip is removed
      try {
        const res = await axios.post(`${API}/ask-transcript`, { patient_id: patientId, transcript, question: text });
        answer({ content: res.data.answer, footnote: 'Answered from the recording transcript only.' });
      } catch (e) {
        push({ role: 'error', content: explain(e) });
      } finally {
        setLoading(false);
      }
      return;
    }
    try {
      const res = await axios.post(`${API}/deep-query`, {
        patient_id: patientId, question: text, conversation_history: history.slice(-6), scope: SECTION_SCOPE[scope] || [],
      });
      answer({ content: res.data.answer, evidence: res.data.evidence });
      setHistory((h) => [...h, { role: 'user', content: text }, { role: 'assistant', content: res.data.answer }]);
    } catch (e) {
      push({ role: 'error', content: explain(e) });
    } finally {
      setLoading(false);
    }
  };

  // The doctor said yes: analyze the study image or the attached file.
  const analyze = async (offer, index) => {
    if (loading) return;
    setMessages((all) => all.map((m, i) => (i === index ? { ...m, answered: true } : m)));
    setLoading(true);
    try {
      let content, footnote;
      if (offer.study) {
        const { department, title, date } = offer.study;
        const res = await axios.post(`${API}/analyze-study`, { patient_id: patientId, department, title, date });
        content = res.data.analysis;
        footnote = `Written report on record: ${tidy(res.data.report)}. ${res.data.note}`;
      } else if (isAudio(offer.file)) {
        const form = new FormData();
        form.append('file', offer.file);
        form.append('patient_id', patientId);
        const res = await axios.post(`${API}/transcribe-recording`, form);
        push({ role: 'transcript', data: res.data, name: offer.file.name });
        setTranscript(transcriptText(res.data));
        return;
      } else {
        const form = new FormData();
        form.append('file', offer.file);
        form.append('patient_id', patientId);
        const res = await axios.post(`${API}/analyze-document`, form);
        content = res.data.analysis;
        footnote = 'AI reading of an uploaded file. Check it against the original document.';
      }
      answer({ content, footnote });
      setHistory((h) => [...h, { role: 'assistant', content }]);
    } catch (e) {
      push({ role: 'error', content: explain(e) });
    } finally {
      setLoading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const study = e.dataTransfer.getData('application/x-study');
    if (study) offerStudy(JSON.parse(study), 'Study received.');
    else if (e.dataTransfer.files?.[0]) offerFile(e.dataTransfer.files[0]);
  };

  return (
    <section className="relative flex flex-col h-full bg-slate-50" data-testid="ask-panel"
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setDragOver(false); }} onDrop={onDrop}>
      <header className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-900 to-teal-900 text-white px-5 py-5">
        <span className="absolute -top-10 -right-6 w-40 h-40 rounded-full bg-teal-400/15" aria-hidden="true" />
        <div className="relative flex items-center gap-3">
          <DocAssistOrb size={48} />
          <div>
            <h3 className="text-base font-semibold">DocAssist</h3>
            <p className="text-xs text-slate-300">Reading {patientName}'s chart</p>
          </div>
        </div>
        <div className="relative mt-3 flex flex-wrap items-center gap-2">
          <button type="button" onClick={speaker.toggle} role="switch" aria-checked={speaker.enabled} data-testid="voice-toggle"
            className={`inline-flex items-center gap-2 text-xs font-medium rounded-full pl-1 pr-3 py-1 transition-colors ${speaker.enabled ? 'bg-teal-400 text-slate-900' : 'bg-white/10 text-slate-200 hover:bg-white/15'}`}>
            <span className={`w-6 h-6 rounded-full flex items-center justify-center ${speaker.enabled ? 'bg-slate-900 text-teal-300' : 'bg-white/15'}`}>
              {speaker.enabled ? <Volume2 className="w-3.5 h-3.5" aria-hidden="true" /> : <VolumeX className="w-3.5 h-3.5" aria-hidden="true" />}
            </span>
            Voice replies {speaker.enabled ? 'on' : 'off'}
            {speaker.speaking && (
              <span className="flex items-end gap-0.5 h-3" aria-hidden="true">
                {[0, 1, 2, 3].map((n) => <span key={n} className="voice-bar w-0.5 bg-slate-900 rounded-full" style={{ animationDelay: `${n * 0.12}s` }} />)}
              </span>
            )}
          </button>
          {speaker.speaking && (
            <button type="button" onClick={speaker.stop} data-testid="voice-stop"
              className="inline-flex items-center gap-1.5 text-xs font-medium rounded-full px-3 py-1.5 bg-white text-slate-900 hover:bg-slate-100">
              <Square className="w-3 h-3" aria-hidden="true" />Stop
            </button>
          )}
          <span className="text-xs text-slate-300">AI-assisted. Verify against the record before acting.</span>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-3" aria-live="polite">
        {messages.length === 0 && (
          <div className="space-y-2">
            <p className="text-sm text-slate-600 mb-3">Ask a question, pick a starting point, or drag in a scan or a file.</p>
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
          <div key={i} className="flex flex-col items-end rise-in">
            {m.scope && <span className="text-[11px] text-slate-500 mb-0.5">About {m.scope}</span>}
            <p className="max-w-[85%] text-sm text-white bg-teal-700 rounded-2xl rounded-br-md px-3.5 py-2">{m.content}</p>
          </div>
        ) : m.role === 'error' ? (
          <p key={i} role="alert" className="rise-in text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-2xl px-3.5 py-2.5">{m.content}</p>
        ) : m.role === 'offer' ? (
          <div key={i} className="flex gap-2 rise-in" data-testid="analysis-offer">
            <DocAssistOrb size={26} />
            <div className="flex-1 min-w-0 bg-white border border-slate-200 rounded-2xl rounded-tl-md overflow-hidden card-raised">
              {m.study ? (
                <>
                  {m.study.image && <img src={m.study.image} alt={`${m.study.title} image`} className="w-full max-h-56 object-cover bg-slate-900" />}
                  <div className="px-3.5 pt-2.5 text-sm">
                    <p className="text-slate-600">{m.lead}</p>
                    <p className="font-semibold text-slate-900 mt-1">{m.study.title} <span className="font-normal text-slate-500">· {formatDate(m.study.date)}</span></p>
                    <p className="text-slate-700">Report: {m.study.result}</p>
                  </div>
                </>
              ) : (
                <div className="px-3.5 pt-2.5 text-sm flex items-center gap-2.5">
                  <span className="w-9 h-9 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center shrink-0"><FileText className="w-4 h-4" aria-hidden="true" /></span>
                  <span className="min-w-0"><span className="block text-slate-600">{m.lead}</span><span className="block font-semibold text-slate-900 break-all">{m.file.name}</span></span>
                </div>
              )}
              <div className="px-3.5 py-3">
                {m.answered ? <p className="text-xs text-slate-500">Request noted.</p> : (
                  <>
                    <p className="text-sm text-slate-900">Would you like me to {m.file && isAudio(m.file) ? 'transcribe this recording' : `analyze ${m.study ? 'this image' : 'this file'}`}?</p>
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => analyze(m, i)} disabled={loading || (m.study && !m.study.image)}
                        className="text-sm font-medium px-3.5 py-1.5 rounded-full bg-teal-700 text-white hover:bg-teal-800 disabled:opacity-40">{m.file && isAudio(m.file) ? 'Yes, transcribe' : 'Yes, analyze'}</button>
                      <button onClick={() => setMessages((all) => all.map((x, k) => (k === i ? { ...x, answered: true } : x)))}
                        className="text-sm px-3.5 py-1.5 rounded-full border border-slate-300 text-slate-700 hover:bg-slate-50">Not now</button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        ) : m.role === 'transcript' ? (
          <div key={i} className="flex gap-2 rise-in" data-testid="transcript">
            <DocAssistOrb size={26} />
            <div className="flex-1 min-w-0 bg-white border border-slate-200 rounded-2xl rounded-tl-md px-3.5 py-3 card-raised">
              <p className="text-sm font-semibold text-slate-900">Transcript <span className="font-normal text-slate-500 break-all">· {m.name}</span></p>
              <ol className="mt-2 space-y-2">
                {m.data.segments.map((seg, k) => (
                  <li key={k} className="grid grid-cols-[2.75rem_1fr] gap-2 text-sm">
                    <span className="text-xs text-slate-500 tabular-nums pt-0.5">{seg.start}</span>
                    <span>
                      <span className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded-full mr-1.5 ${SPEAKER_STYLE[seg.speaker] || 'bg-amber-100 text-amber-900'}`}>{seg.speaker}</span>
                      <span className="text-slate-800">{seg.text}</span>
                    </span>
                  </li>
                ))}
              </ol>
              {m.data.summary.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <p className="text-xs font-medium text-slate-500">What was discussed</p>
                  <ul className="mt-1 list-disc pl-5 text-sm text-slate-800 space-y-0.5">{m.data.summary.map((b, k) => <li key={k}>{tidy(b)}</li>)}</ul>
                </div>
              )}
              <p className="mt-3 text-xs text-slate-500">{m.data.note} You can now ask questions about this conversation.</p>
            </div>
          </div>
        ) : (
          <div key={i} className="flex gap-2 rise-in">
            <DocAssistOrb size={26} />
            <div className="flex-1 min-w-0 text-sm text-slate-800 bg-white border border-slate-200 rounded-2xl rounded-tl-md px-3.5 py-2.5 card-raised">
              <MessageContent text={tidy(m.content)} />
              {m.footnote && <p className="mt-2 pt-2 border-t border-slate-100 text-xs text-slate-500">{m.footnote}</p>}
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
          <div className="flex items-center gap-2" role="status" aria-label="DocAssist is working">
            <DocAssistOrb size={26} />
            <span className="flex gap-1 bg-white border border-slate-200 rounded-2xl px-3.5 py-3">
              {[0, 1, 2].map((n) => <span key={n} className="typing-dot w-1.5 h-1.5 rounded-full bg-slate-500" style={{ animationDelay: `${n * 0.15}s` }} />)}
            </span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="bg-white border-t border-slate-200 p-3">
        {transcript && (
          <p className="mb-2 mr-2 inline-flex items-center gap-1.5 text-xs pl-3 pr-1.5 py-1 rounded-full bg-teal-50 text-teal-900 border border-teal-200" data-testid="recording-chip">
            Asking about the recording
            <button onClick={() => setTranscript(null)} aria-label="Stop asking about the recording" className="p-0.5 rounded-full hover:bg-teal-100"><X className="w-3 h-3" /></button>
          </p>
        )}
        {scope && !transcript && (
          <p className="mb-2 inline-flex items-center gap-1.5 text-xs pl-3 pr-1.5 py-1 rounded-full bg-teal-50 text-teal-900 border border-teal-200" data-testid="scope-chip">
            Asking about {scope}
            <button onClick={() => setScope(null)} aria-label={`Stop asking only about ${scope}`} className="p-0.5 rounded-full hover:bg-teal-100"><X className="w-3 h-3" /></button>
          </p>
        )}
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
          <input ref={fileRef} type="file" className="hidden"
            onChange={(e) => { if (e.target.files[0]) offerFile(e.target.files[0]); e.target.value = ''; }} />
          <div className="relative">
            <button type="button" onClick={() => setAttachOpen(!attachOpen)} aria-label="Attach" aria-haspopup="menu" aria-expanded={attachOpen} data-testid="attach-button"
              className={`w-11 h-11 rounded-full flex items-center justify-center ${attachOpen ? 'bg-teal-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
              <Paperclip className="w-4 h-4" />
            </button>
            {attachOpen && (
              <div role="menu" className="absolute bottom-full left-0 mb-2 w-72 rounded-2xl bg-white border border-slate-200 shadow-xl p-1.5 rise-in" data-testid="attach-menu">
                {ATTACH_OPTIONS.map(({ Icon, label, hint, accept, info }) => (
                  <div key={label}>
                    <div className="flex items-center rounded-xl hover:bg-slate-100">
                      <button type="button" role="menuitem"
                        onClick={() => { setAttachOpen(false); setInfoFor(null); fileRef.current.accept = accept; fileRef.current.click(); }}
                        className="flex-1 flex items-center gap-3 text-left px-2.5 py-2">
                        <span className="w-8 h-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center shrink-0"><Icon className="w-4 h-4" aria-hidden="true" /></span>
                        <span><span className="block text-sm font-medium text-slate-900">{label}</span><span className="block text-xs text-slate-500">{hint}</span></span>
                      </button>
                      {info && (
                        <button type="button" onClick={() => setInfoFor(infoFor === label ? null : label)} aria-expanded={infoFor === label}
                          aria-label={`What DocAssist does with a ${label.toLowerCase()}`} data-testid="recording-info"
                          className="mr-1.5 w-7 h-7 rounded-full text-slate-500 hover:bg-white hover:text-teal-800 flex items-center justify-center">
                          <Info className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                    {info && infoFor === label && <p className="mx-2.5 mb-2 mt-1 text-xs text-slate-600 bg-slate-50 rounded-lg px-2.5 py-2">{info}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
          <input value={question} onChange={(e) => setQuestion(e.target.value)}
            placeholder={dictation.listening ? 'Listening… speak your question' : transcript ? 'Ask about the recorded conversation' : scope ? `Ask about ${scope.toLowerCase()}` : 'Ask about results, treatment or history'} aria-label="Question about this patient"
            className={`flex-1 min-w-0 h-11 rounded-full bg-slate-100 px-4 text-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-600 ${dictation.listening ? 'ring-2 ring-rose-400' : ''}`} />
          <button type="button" onClick={dictation.toggle} aria-pressed={dictation.listening} data-testid="mic-button"
            aria-label={dictation.listening ? 'Stop dictation' : 'Dictate a question'} title={dictation.supported ? undefined : 'Dictation needs Chrome or Edge'}
            className={`relative w-11 h-11 rounded-full flex items-center justify-center shrink-0 transition-colors ${dictation.listening ? 'mic-live bg-rose-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            <Mic className="relative w-4 h-4" />
          </button>
          <button type="submit" disabled={loading || !question.trim()} aria-label="Send question"
            className="w-11 h-11 rounded-full bg-teal-700 text-white flex items-center justify-center hover:bg-teal-800 disabled:opacity-40">
            <Send className="w-4 h-4" />
          </button>
        </form>
        {dictation.error && <p role="alert" className="mt-2 text-xs text-amber-800">{dictation.error}</p>}
      </div>

      {dragOver && (
        <div className="absolute inset-0 z-10 m-3 rounded-3xl border-2 border-dashed border-teal-500 bg-teal-50/90 flex flex-col items-center justify-center gap-2 pointer-events-none">
          <DocAssistOrb size={52} />
          <p className="text-sm font-medium text-teal-900">Drop it here</p>
          <p className="text-xs text-teal-800">I will show it first and ask before analyzing.</p>
        </div>
      )}
    </section>
  );
};

export default AskPanel;
