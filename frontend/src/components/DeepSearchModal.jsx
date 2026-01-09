import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card } from "./ui/card";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000";
const API = `${BACKEND_URL}/api`;

/**
 * DeepSearchModal flow:
 * 1) NEED_PATIENT -> ask for patient id/name -> call GET /api/search?term=...
 * 2) VERIFY_PATIENT -> show patient -> confirm/change
 * 3) LOCKED -> doctor asks question -> call POST /api/deep-query { patient_id, query }
 */

export default function DeepSearchModal({ open, onClose }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // conversation messages
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  // patient gate states
  const [stage, setStage] = useState("NEED_PATIENT"); // NEED_PATIENT | VERIFY_PATIENT | LOCKED
  const [selectedPatient, setSelectedPatient] = useState(null);

  // loading
  const [isLoading, setIsLoading] = useState(false);

  const listRef = useRef(null);

  // reset when modal opens
  useEffect(() => {
    if (!open) return;

    setIsFullscreen(false);
    setMessages([
      {
        role: "assistant",
        text:
          "Hi Doctor 👋 I’m Deep Search. First, please enter the Patient ID (e.g., P1001) or Patient Name (min 3 letters).",
      },
    ]);
    setInput("");
    setStage("NEED_PATIENT");
    setSelectedPatient(null);
    setIsLoading(false);
  }, [open]);

  // auto scroll
  useEffect(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, isLoading, stage]);

  const containerClass = useMemo(() => {
    if (!open) return "hidden";
    return "fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4";
  }, [open]);

  const modalClass = useMemo(() => {
    if (isFullscreen) {
      return "w-full h-full max-w-none bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col";
    }
    return "w-full max-w-3xl bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col";
  }, [isFullscreen]);

  // ---- Validation helpers (blocks "Hi") ----
  const isValidPatientId = (text) => /^P\d{3,}$/i.test(text.trim());
  const isValidPatientName = (text) => {
    const t = text.trim();
    const letters = t.replace(/[^a-zA-Z]/g, "");
    return letters.length >= 3;
  };
  const isValidPatientQuery = (text) => isValidPatientId(text) || isValidPatientName(text);

  const pushMsg = (role, text) => setMessages((prev) => [...prev, { role, text }]);

  // ---- Backend calls ----
  const fetchPatientByTerm = async (term) => {
    const url = `${API}/search`;
    const res = await axios.get(url, { params: { term } });
    // your backend returns { profile, ... }
    return res?.data?.profile || null;
  };

  const runDeepQuery = async ({ patient_id, query }) => {
    const url = `${API}/deep-query`;
    const res = await axios.post(url, { patient_id, query });
    return res?.data || null;
  };

  const handleChangePatient = () => {
    setSelectedPatient(null);
    setStage("NEED_PATIENT");
    pushMsg("assistant", "Okay ✅ Please enter the Patient ID (P1001) or Patient Name (min 3 letters).");
  };

  const handleConfirmPatient = () => {
    if (!selectedPatient) return;
    setStage("LOCKED");
    pushMsg(
      "assistant",
      `Great ✅ Patient locked: ${selectedPatient.name || "Unknown"} (${selectedPatient.patient_id || "N/A"}). Now ask your question.`
    );
  };

  const renderEvidence = (evidence) => {
    if (!Array.isArray(evidence) || evidence.length === 0) return null;

    return (
      <Card className="p-4 bg-white border shadow-sm">
        <div className="text-sm font-semibold text-gray-700 mb-2">Evidence (from MongoDB)</div>
        <div className="space-y-3">
          {evidence.slice(0, 6).map((ev, idx) => (
            <div key={idx} className="border rounded-lg p-3 text-sm">
              <div className="font-semibold text-gray-800">
                {ev?.department || "department"} • {ev?.date || "date"}
              </div>
              <div className="text-gray-700">Test: {ev?.title || ev?.test_name || "N/A"}</div>
              <div className="text-gray-700">Result: {ev?.result || "N/A"}</div>
              <div className="text-gray-700">Doctor: {ev?.doctor || "N/A"}</div>
              {ev?.report_image && (
                <div className="mt-2">
                  <a
                    href={ev.report_image}
                    target="_blank"
                    rel="noreferrer"
                    className="text-teal-700 underline"
                  >
                    Open report image
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
    );
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;

    // user message
    pushMsg("user", text);
    setInput("");

    // --- STAGE: NEED_PATIENT ---
    if (stage === "NEED_PATIENT") {
      if (!isValidPatientQuery(text)) {
        pushMsg(
          "assistant",
          "Please enter a valid Patient ID like **P1001** or a Patient Name (minimum **3 letters**). Example: **Tara Smith**."
        );
        return;
      }

      setIsLoading(true);
      pushMsg("assistant", "Got it ✅ Fetching patient details...");

      try {
        const profile = await fetchPatientByTerm(text);

        if (!profile) {
          pushMsg("assistant", "I couldn't find a patient with that ID/Name. Please try again (example: P1001).");
          return;
        }

        setSelectedPatient(profile);
        setStage("VERIFY_PATIENT");

        const summaryLines = [
          "Please verify the patient details below:",
          `• Name: ${profile.name || "N/A"}`,
          `• ID: ${profile.patient_id || "N/A"}`,
          `• Age: ${profile.age ?? "N/A"}`,
          `• Gender: ${profile.gender || "N/A"}`,
          `• Blood Group: ${profile.blood_group || "N/A"}`,
        ].join("\n");

        pushMsg("assistant", summaryLines);
        pushMsg("assistant", "Is this the correct patient? Click **Confirm** or **Change Patient**.");
      } catch (err) {
        console.error(err);
        pushMsg("assistant", "Error fetching patient details. Please check backend is running and try again.");
      } finally {
        setIsLoading(false);
      }

      return;
    }

    // --- STAGE: VERIFY_PATIENT ---
    if (stage === "VERIFY_PATIENT") {
      pushMsg("assistant", "Please use the buttons below: **Confirm** or **Change Patient**.");
      return;
    }

    // --- STAGE: LOCKED (REAL backend deep-query) ---
    if (stage === "LOCKED") {
      // optional: block super-short nonsense (Hi / Hbsh etc.)
      const letters = text.replace(/[^a-zA-Z]/g, "");
      if (letters.length < 3) {
        pushMsg("assistant", "Please type a clearer question (minimum 3 letters). Example: “fetch blood reports”.");
        return;
      }

      if (!selectedPatient?.patient_id) {
        pushMsg("assistant", "Patient is not locked correctly (missing patient_id). Please Change Patient and select again.");
        return;
      }

      setIsLoading(true);
      try {
        const data = await runDeepQuery({
          patient_id: selectedPatient.patient_id,
          query: text,
        });

        if (!data) {
          pushMsg("assistant", "Backend returned empty response. Check backend logs.");
          return;
        }

        // Show backend answer
        if (data.answer) pushMsg("assistant", data.answer);
        else pushMsg("assistant", "Backend responded, but no 'answer' field found.");

        // Show evidence in UI (as extra message + card)
        if (Array.isArray(data.evidence) && data.evidence.length > 0) {
          pushMsg("assistant", "I also found supporting records (see below).");
          // Inject a special message object to render evidence card
          setMessages((prev) => [...prev, { role: "evidence", evidence: data.evidence }]);
        }
      } catch (err) {
        const detail =
          err?.response?.data ? JSON.stringify(err.response.data) : err?.message || "Unknown error";
        console.error("deep-query error:", err);
        pushMsg("assistant", `Backend deep-query failed. Details: ${detail}`);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleMicClick = () => {
    pushMsg("assistant", "🎙️ Mic is UI-only for now. Next step: wire Web Speech API / Whisper + send transcript here.");
  };

  if (!open) return null;

  return (
    <div className={containerClass}>
      <div className={modalClass}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-gradient-to-r from-teal-600 to-cyan-600 text-white">
          <div>
            <div className="text-lg font-bold">Deep Search</div>
            <div className="text-xs opacity-90">Patient-aware chat + backend deep-query</div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsFullscreen((p) => !p)}
              className="text-xs bg-white/20 hover:bg-white/30 px-3 py-1 rounded-md"
              type="button"
            >
              {isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
            </button>
            <button
              onClick={onClose}
              className="text-xl leading-none bg-white/20 hover:bg-white/30 w-9 h-9 rounded-md flex items-center justify-center"
              aria-label="Close"
              type="button"
            >
              ×
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 p-4 bg-gray-50 overflow-hidden flex flex-col">
          <div ref={listRef} className="flex-1 overflow-y-auto space-y-3 pr-2" style={{ scrollbarWidth: "thin" }}>
            {messages.map((m, idx) => {
              if (m.role === "evidence") {
                return (
                  <div key={idx} className="mr-auto max-w-[95%]">
                    {renderEvidence(m.evidence)}
                  </div>
                );
              }

              return (
                <div
                  key={idx}
                  className={`max-w-[90%] whitespace-pre-line rounded-xl px-4 py-3 shadow-sm ${
                    m.role === "user" ? "ml-auto bg-teal-600 text-white" : "mr-auto bg-white text-gray-800 border"
                  }`}
                >
                  {m.text}
                </div>
              );
            })}

            {isLoading && (
              <div className="mr-auto bg-white text-gray-700 border rounded-xl px-4 py-3 shadow-sm">
                Loading...
              </div>
            )}

            {/* Patient Verify Panel */}
            {stage === "VERIFY_PATIENT" && selectedPatient && (
              <Card className="p-4 bg-white border shadow-sm">
                <div className="text-sm font-semibold text-gray-700 mb-3">Selected Patient</div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-gray-500 text-xs">Name</div>
                    <div className="font-semibold">{selectedPatient.name || "N/A"}</div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs">Patient ID</div>
                    <div className="font-semibold">{selectedPatient.patient_id || "N/A"}</div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs">Age</div>
                    <div className="font-semibold">{selectedPatient.age ?? "N/A"}</div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs">Gender</div>
                    <div className="font-semibold">{selectedPatient.gender || "N/A"}</div>
                  </div>
                </div>

                <div className="flex gap-2 mt-4">
                  <Button onClick={handleConfirmPatient} className="bg-teal-600 hover:bg-teal-700" type="button">
                    Confirm
                  </Button>
                  <Button variant="secondary" onClick={handleChangePatient} type="button">
                    Change Patient
                  </Button>
                </div>

                <div className="text-xs text-gray-500 mt-3">Confirm the patient above to start Deep Search queries.</div>
              </Card>
            )}
          </div>

          {/* Footer input */}
          <div className="mt-3 flex gap-2 items-center">
            <Button type="button" variant="secondary" onClick={handleMicClick} className="w-20">
              Mic
            </Button>

            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                stage === "NEED_PATIENT"
                  ? 'Enter Patient ID (P1001) or Name (min 3 letters)'
                  : stage === "LOCKED"
                  ? 'Example: "fetch blood reports"'
                  : "Use Confirm / Change Patient"
              }
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
            />

            <Button onClick={handleSend} className="bg-teal-600 hover:bg-teal-700" type="button">
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}