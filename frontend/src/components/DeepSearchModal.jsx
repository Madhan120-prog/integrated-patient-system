import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card } from "./ui/card";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000";
const API = `${BACKEND_URL}/api`;

/**
 * DeepSearchModal
 * Flow:
 * 1) Ask Patient ID/Name
 * 2) Fetch patient profile via GET /api/search?term=...
 * 3) Verify -> Confirm
 * 4) Locked -> Send question -> POST /api/deep-query
 * 5) Render:
 *    - clean assistant answer
 *    - evidence cards (View Report button if report_image exists)
 *    - Open Patient Overview shortcut (/results?term=P1001)
 */

export default function DeepSearchModal({ open, onClose }) {
  const navigate = useNavigate();

  const [isFullscreen, setIsFullscreen] = useState(false);

  // conversation
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  // patient gating
  const [stage, setStage] = useState("NEED_PATIENT"); // NEED_PATIENT | VERIFY_PATIENT | LOCKED
  const [selectedPatient, setSelectedPatient] = useState(null);

  // evidence + answer from deep query
  const [lastAnswer, setLastAnswer] = useState(null); // string
  const [lastEvidence, setLastEvidence] = useState([]); // array
  const [lastMatchedDepartments, setLastMatchedDepartments] = useState([]); // array

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

    setLastAnswer(null);
    setLastEvidence([]);
    setLastMatchedDepartments([]);

    setIsLoading(false);
  }, [open]);

  // auto scroll
  useEffect(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, isLoading, lastAnswer, lastEvidence]);

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

  // ---- Validation helpers ----
  const isValidPatientId = (text) => /^P\d{3,}$/i.test(text.trim());
  const isValidPatientName = (text) => {
    const t = text.trim();
    const letters = t.replace(/[^a-zA-Z]/g, "");
    if (letters.length < 3) return false;
    return /[a-zA-Z]/.test(t);
  };
  const isValidPatientQuery = (text) => isValidPatientId(text) || isValidPatientName(text);

  const pushMsg = (role, text) => {
    setMessages((prev) => [...prev, { role, text }]);
  };

  // ---- Fetch patient using GET /api/search?term=... ----
  const fetchPatientByTerm = async (term) => {
    const url = `${API}/search?term=${encodeURIComponent(term)}`;
    const res = await axios.get(url);
    if (!res?.data) return null;

    if (res.data.profile) return res.data.profile;

    // if backend ever returns {patient: {...}} or {results: [...]}
    if (res.data.patient) return res.data.patient;
    if (Array.isArray(res.data.results) && res.data.results.length > 0) return res.data.results[0];

    return null;
  };

  // ---- Deep Query: POST /api/deep-query ----
  const runDeepQuery = async (patientId, query) => {
    const payload = {
      patient_id: patientId,
      query,
    };

    const res = await axios.post(`${API}/deep-query`, payload, {
      headers: { "Content-Type": "application/json" },
    });

    return res?.data || null;
  };

  const handleChangePatient = () => {
    setSelectedPatient(null);
    setStage("NEED_PATIENT");
    setLastAnswer(null);
    setLastEvidence([]);
    setLastMatchedDepartments([]);
    pushMsg("assistant", "Okay ✅ Please enter the Patient ID (P1001) or Patient Name (min 3 letters).");
  };

  const handleConfirmPatient = () => {
    if (!selectedPatient) return;
    setStage("LOCKED");
    pushMsg(
      "assistant",
      `Great ✅ Patient locked: ${selectedPatient.name || "Unknown"} (${selectedPatient.patient_id || "N/A"}). Now ask your question.`
    );
    pushMsg("assistant", `Tip: try “fetch blood reports” or “show mri records”.`);
  };

  const handleOpenOverview = () => {
    if (!selectedPatient?.patient_id) return;
    onClose?.();
    navigate(`/results?term=${encodeURIComponent(selectedPatient.patient_id)}`);
  };

  const handleViewReport = (evidenceItem) => {
    const url = evidenceItem?.record?.report_image || evidenceItem?.report_image;
    if (!url) return;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;

    pushMsg("user", text);
    setInput("");

    // Stage: NEED_PATIENT
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

    // Stage: VERIFY_PATIENT
    if (stage === "VERIFY_PATIENT") {
      pushMsg("assistant", "Please use the buttons below: **Confirm** or **Change Patient**.");
      return;
    }

    // Stage: LOCKED
    if (stage === "LOCKED") {
      const pid = selectedPatient?.patient_id;
      if (!pid) {
        pushMsg("assistant", "Patient ID missing. Please Change Patient and select again.");
        return;
      }

      setIsLoading(true);
      try {
        const data = await runDeepQuery(pid, text);

        // Clean parse
        const answer = data?.answer || "✅ Done. (No answer text returned.)";
        const evidence = Array.isArray(data?.evidence) ? data.evidence : [];
        const matched = Array.isArray(data?.matched_departments) ? data.matched_departments : [];

        // Save for UI panels
        setLastAnswer(answer);
        setLastEvidence(evidence);
        setLastMatchedDepartments(matched);

        // Also put a short assistant message into chat timeline
        pushMsg("assistant", answer);
        if (matched.length > 0) {
          pushMsg("assistant", `Matched: ${matched.join(", ")}`);
        }
        if (evidence.length > 0) {
          pushMsg("assistant", `I found supporting records (see Evidence below).`);
        } else {
          pushMsg("assistant", `No supporting records were returned for this query.`);
        }
      } catch (err) {
        console.error(err);
        pushMsg("assistant", "Deep query failed. Please check `/api/deep-query` in Swagger and backend logs.");
      } finally {
        setIsLoading(false);
      }

      return;
    }
  };

  const handleMicClick = () => {
    pushMsg("assistant", "🎙️ Mic is UI-only for now. Next step: enable Web Speech API / Whisper and send transcript here.");
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
          <div ref={listRef} className="flex-1 overflow-y-auto space-y-3 pr-2">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`max-w-[90%] whitespace-pre-line rounded-xl px-4 py-3 shadow-sm ${
                  m.role === "user"
                    ? "ml-auto bg-teal-600 text-white"
                    : "mr-auto bg-white text-gray-800 border"
                }`}
              >
                {m.text}
              </div>
            ))}

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
                  <Button onClick={handleConfirmPatient} className="bg-teal-600 hover:bg-teal-700">
                    Confirm
                  </Button>
                  <Button variant="secondary" onClick={handleChangePatient}>
                    Change Patient
                  </Button>
                </div>

                <div className="text-xs text-gray-500 mt-3">
                  Confirm the patient above to start patient-aware Deep Search.
                </div>
              </Card>
            )}

            {/* Evidence Panel (only when LOCKED and we have evidence) */}
            {stage === "LOCKED" && selectedPatient && (
              <Card className="p-4 bg-white border shadow-sm">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-gray-700">Patient</div>
                    <div className="text-xs text-gray-500">
                      {selectedPatient.name} ({selectedPatient.patient_id})
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" variant="secondary" onClick={handleOpenOverview}>
                      Open Patient Overview
                    </Button>
                    <Button type="button" variant="secondary" onClick={handleChangePatient}>
                      Change Patient
                    </Button>
                  </div>
                </div>

                {lastMatchedDepartments?.length > 0 && (
                  <div className="mt-3 text-xs text-gray-600">
                    <span className="font-semibold">Matched:</span> {lastMatchedDepartments.join(", ")}
                  </div>
                )}

                {lastEvidence?.length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm font-semibold text-gray-700 mb-2">Evidence (from MongoDB)</div>

                    <div className="space-y-2">
                      {lastEvidence.map((ev, i) => {
                        const rec = ev?.record || ev || {};
                        const dept = ev?.department || rec?.department || "unknown_department";
                        const date = ev?.date || rec?.test_date || rec?.date || "N/A";
                        const title = ev?.title || rec?.test_name || rec?.title || "Record";
                        const result = ev?.result || rec?.result || "N/A";
                        const doctor = ev?.doctor || rec?.doctor || "N/A";
                        const hasReport = Boolean(rec?.report_image || ev?.report_image);

                        return (
                          <div key={i} className="border rounded-xl p-3 bg-gray-50">
                            <div className="text-xs text-gray-500">{dept} • {date}</div>
                            <div className="text-sm font-semibold text-gray-800">{title}</div>
                            <div className="text-xs text-gray-700 mt-1">Result: {result}</div>
                            <div className="text-xs text-gray-700">Doctor: {doctor}</div>

                            <div className="mt-2 flex gap-2">
                              <Button
                                type="button"
                                variant="secondary"
                                disabled={!hasReport}
                                onClick={() => handleViewReport(ev)}
                              >
                                View Report
                              </Button>
                            </div>

                            {!hasReport && (
                              <div className="text-[11px] text-gray-500 mt-1">
                                No report image/link available for this record yet.
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
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
                  ? 'Example: "fetch blood reports" or "show MRI records"'
                  : "Use Confirm / Change Patient"
              }
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
            />

            <Button onClick={handleSend} className="bg-teal-600 hover:bg-teal-700">
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}