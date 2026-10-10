import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ── Speaking: turn an on-screen answer into short sentences worth saying ─────

const APPENDED_WARNING_RE = /\n\n⚠ \*\*(?:Low confidence|Drug dosage mentioned|Unverified claim|Diagnostic language detected|Range check)\*\*[^\n]*/g;
const SPOKEN = [
  [/K\/µL/g, 'thousand per microlitre'], [/g\/dL/g, 'grams per decilitre'], [/ng\/mL/g, 'nanograms per millilitre'],
  [/U\/mL/g, 'units per millilitre'], [/U\/L/g, 'units per litre'], [/mg\/dL/g, 'milligrams per decilitre'],
  [/mg\/m²/g, 'milligrams per square metre'], [/mcg\/kg/g, 'micrograms per kilogram'],
  [/↓/g, 'down'], [/↑/g, 'up'], [/→/g, 'to'], [/[·—–]/g, ','], [/⚠/g, ''], [/\*\*|[*#_`]/g, ''],
];
const MAX_SENTENCES = 12;

// Safety warnings stay on screen and are announced once, not read out word for word.
export const spokenSentences = (text) => {
  const hadWarning = APPENDED_WARNING_RE.test(text);
  let spoken = text.replace(APPENDED_WARNING_RE, '');
  SPOKEN.forEach(([re, word]) => { spoken = spoken.replace(re, word); });
  const parts = spoken.split(/(?<=[.!?])\s+|\n+/).map((s) => s.replace(/^[-•\s]+/, '').trim()).filter((s) => /[a-z0-9]/i.test(s));
  const out = parts.slice(0, MAX_SENTENCES);
  if (parts.length > MAX_SENTENCES) out.push('The rest is on screen.');
  if (hadWarning) out.push('A safety note is attached. Please read it on screen.');
  return out;
};

// Voice replies. Off by default. The answer is sent one sentence at a time and
// the next sentence is fetched while the current one plays, so speech starts
// about as soon as the text appears instead of after the whole answer is synthesised.
export const useSpeaker = () => {
  const [enabled, setEnabled] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const run = useRef(0);
  const audio = useRef(null);
  const release = useRef(null);

  const stop = useCallback(() => {
    run.current += 1;
    audio.current?.pause();
    release.current?.();
    setSpeaking(false);
  }, []);
  useEffect(() => stop, [stop]);

  const fetchClip = (sentence) => axios.post(`${API}/tts`, { text: sentence }, { responseType: 'blob' }).then((res) => URL.createObjectURL(res.data));
  const play = (url) => new Promise((resolve) => {
    const a = new Audio(url);
    audio.current = a;
    release.current = resolve;
    a.onended = resolve;
    a.onerror = resolve;
    a.play().catch(resolve);
  });

  const speak = useCallback(async (text) => {
    stop();
    const id = run.current;
    const sentences = spokenSentences(text);
    if (!sentences.length) return;
    setSpeaking(true);
    let next = fetchClip(sentences[0]);
    for (let i = 0; i < sentences.length && run.current === id; i += 1) {
      const pending = next;
      next = i + 1 < sentences.length ? fetchClip(sentences[i + 1]) : null;
      let url;
      try { url = await pending; } catch { break; }   // voice service unavailable: the text is still on screen
      if (run.current === id) await play(url);
      URL.revokeObjectURL(url);
    }
    if (run.current === id) setSpeaking(false);
  }, [stop]);

  const toggle = () => { if (enabled) stop(); setEnabled(!enabled); };
  return { enabled, toggle, speaking, speak, stop };
};

// ── Dictation: the browser's speech recognition fills the question box ───────

export const useDictation = (onText) => {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState('');
  const recognition = useRef(null);
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  useEffect(() => () => recognition.current?.abort(), []);

  const start = () => {
    if (!Recognition) { setError('Dictation needs Chrome or Edge.'); return; }
    const r = new Recognition();
    r.lang = 'en-US';
    r.interimResults = true;      // words appear as they are spoken
    r.continuous = false;         // stops by itself on a pause
    r.onresult = (e) => onText(Array.from(e.results).map((res) => res[0].transcript).join(''));
    r.onerror = (e) => {
      if (e.error === 'not-allowed') setError('Microphone access is blocked. Allow it in the address bar and try again.');
      else if (e.error !== 'no-speech' && e.error !== 'aborted') setError('Dictation stopped. Try again.');
    };
    r.onend = () => setListening(false);
    recognition.current = r;
    setError('');
    setListening(true);
    try { r.start(); } catch { setListening(false); }
  };
  const toggle = () => (listening ? recognition.current?.stop() : start());
  return { listening, toggle, error, supported: !!Recognition };
};
