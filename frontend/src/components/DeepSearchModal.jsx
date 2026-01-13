import React, { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Report Viewer Modal Component
const ReportViewerModal = ({ open, onClose, reportUrl, reportTitle }) => {
  if (!open) return null;
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-teal-600">📄 {reportTitle}</DialogTitle>
        </DialogHeader>
        <div className="relative w-full h-[70vh] bg-gray-100 rounded-lg overflow-hidden">
          <img 
            src={reportUrl} 
            alt={reportTitle}
            className="w-full h-full object-contain"
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = 'https://via.placeholder.com/800x600?text=Report+Image+Unavailable';
            }}
          />
        </div>
        <div className="flex justify-between items-center mt-4">
          <p className="text-sm text-gray-500">Medical report image</p>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => window.open(reportUrl, '_blank')}>
              Open in New Tab
            </Button>
            <Button onClick={onClose}>Close</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

const DeepSearchModal = ({ open, onClose }) => {
  const [step, setStep] = useState('search'); // search, confirm, chat
  const [patientInput, setPatientInput] = useState('');
  const [patientData, setPatientData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [reportModal, setReportModal] = useState({ open: false, url: '', title: '' });
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (step === 'search') {
          setPatientInput(transcript);
        } else if (step === 'chat') {
          setQuestion(transcript);
        }
        setIsListening(false);
      };

      recognitionRef.current.onerror = (event) => {
        setIsListening(false);
        if (event.error === 'not-allowed') {
          toast.error('Microphone access denied. Please allow microphone access in your browser settings.');
        } else if (event.error !== 'no-speech') {
          toast.error('Voice recognition error: ' + event.error);
        }
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      if (synthRef.current) {
        synthRef.current.cancel();
      }
    };
  }, [step]);

  const startListening = () => {
    if (recognitionRef.current) {
      try {
        setIsListening(true);
        recognitionRef.current.start();
      } catch (error) {
        setIsListening(false);
        toast.error('Could not start voice recognition. Please check microphone permissions.');
      }
    } else {
      toast.error('Speech recognition not supported in this browser. Please use Chrome or Edge.');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  };

  const speak = (text) => {
    if (!voiceEnabled) return;
    
    if (synthRef.current) {
      synthRef.current.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      synthRef.current.speak(utterance);
    }
  };

  const stopSpeaking = () => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }
  };

  const toggleVoice = () => {
    if (isSpeaking) {
      stopSpeaking();
    }
    setVoiceEnabled(!voiceEnabled);
    toast.success(voiceEnabled ? 'Voice output disabled' : 'Voice output enabled');
  };

  const handleSearchPatient = async () => {
    if (!patientInput.trim()) {
      toast.error('Please enter Patient ID or Name');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get(`${API}/search?term=${encodeURIComponent(patientInput)}`);
      if (response.data.profile) {
        setPatientData(response.data);
        setStep('confirm');
      } else {
        toast.error('Patient not found');
      }
    } catch (error) {
      toast.error('Error searching patient');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmPatient = () => {
    setStep('chat');
    const welcomeMsg = `Hello! I'm DocAssist, your AI clinical assistant. I have access to all medical records for ${patientData.profile.name} (${patientData.profile.patient_id}). You can ask me anything about their reports, tests, treatments, or medical history. You can also upload medical images or PDFs for AI analysis. How can I help you today?`;
    setMessages([{
      role: 'assistant',
      content: welcomeMsg
    }]);
    speak(welcomeMsg);
  };

  const handleAskQuestion = async () => {
    if (!question.trim()) return;

    const userMessage = { role: 'user', content: question };
    setMessages(prev => [...prev, userMessage]);
    const currentQuestion = question;
    setQuestion('');
    setLoading(true);

    try {
      const response = await axios.post(`${API}/deep-query`, {
        patient_id: patientData.profile.patient_id,
        question: currentQuestion
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        evidence: response.data.evidence,
        departments: response.data.matched_departments
      };

      setMessages(prev => [...prev, assistantMessage]);
      speak(response.data.answer);
    } catch (error) {
      const errorMsg = 'Sorry, I encountered an error processing your question. Please try again.';
      toast.error('Error processing question');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMsg
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'application/pdf'];
      if (!allowedTypes.includes(file.type)) {
        toast.error('Please upload PNG, JPEG, WebP images or PDF files only');
        return;
      }
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        toast.error('File size must be less than 10MB');
        return;
      }
      setUploadedFile(file);
      toast.success(`File "${file.name}" selected. Click "Analyze" to process.`);
    }
  };

  const handleFileAnalysis = async () => {
    if (!uploadedFile) {
      toast.error('Please select a file first');
      return;
    }

    setIsAnalyzing(true);
    const userMessage = { 
      role: 'user', 
      content: `📎 Uploaded file for analysis: ${uploadedFile.name}`,
      isFileUpload: true
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const formData = new FormData();
      formData.append('file', uploadedFile);
      formData.append('patient_id', patientData.profile.patient_id);
      formData.append('question', 'Analyze this medical document and provide a detailed summary with any notable findings.');

      const response = await axios.post(`${API}/analyze-document`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      const analysisMsg = {
        role: 'assistant',
        content: response.data.analysis,
        fileType: response.data.file_type,
        suggestions: response.data.suggestions,
        isAnalysis: true
      };

      setMessages(prev => [...prev, analysisMsg]);
      speak(response.data.analysis);
      setUploadedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      const errorMsg = 'Sorry, I encountered an error analyzing the document. Please try again.';
      toast.error('Error analyzing document');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMsg
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const openReportViewer = (url, title) => {
    setReportModal({ open: true, url, title });
  };

  const handleClose = () => {
    stopSpeaking();
    stopListening();
    setStep('search');
    setPatientInput('');
    setPatientData(null);
    setMessages([]);
    setQuestion('');
    setUploadedFile(null);
    onClose();
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-teal-600">🩺 DocAssist - Voice AI Clinical Assistant</DialogTitle>
          </DialogHeader>

          {/* Step 1: Search Patient */}
          {step === 'search' && (
            <div className="space-y-6">
              <p className="text-gray-600">Enter Patient ID or Name to begin clinical consultation</p>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter Patient ID (e.g., P1001) or Name"
                  value={patientInput}
                  onChange={(e) => setPatientInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearchPatient()}
                  className="flex-1"
                />
                <Button
                  onClick={isListening ? stopListening : startListening}
                  variant="outline"
                  className={isListening ? 'bg-red-100 animate-pulse' : ''}
                  title="Click to speak patient ID or name"
                >
                  {isListening ? '⏹️ Stop' : '🎤 Speak'}
                </Button>
              </div>
              {isListening && (
                <div className="text-center text-sm text-teal-600 animate-pulse">
                  🎤 Listening... Say the patient ID or name
                </div>
              )}
              <Button
                onClick={handleSearchPatient}
                disabled={loading}
                className="w-full bg-teal-600 hover:bg-teal-700"
              >
                {loading ? 'Searching...' : 'Search Patient'}
              </Button>
              
              {/* Microphone Permission Help */}
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-xs text-blue-700">
                  <strong>💡 Voice Input Tip:</strong> If the microphone isn't working, click the 🔒 lock icon in your browser's address bar and allow microphone access.
                </p>
              </div>
            </div>
          )}

          {/* Step 2: Confirm Patient */}
          {step === 'confirm' && patientData && (
            <div className="space-y-6">
              <Card className="p-6 bg-teal-50">
                <h3 className="text-xl font-bold mb-4">Patient Details</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Name</p>
                    <p className="font-semibold">{patientData.profile.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Patient ID</p>
                    <p className="font-semibold">{patientData.profile.patient_id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Age / Gender</p>
                    <p className="font-semibold">{patientData.profile.age} years / {patientData.profile.gender}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Blood Group</p>
                    <p className="font-semibold">{patientData.profile.blood_group}</p>
                  </div>
                </div>
                <div className="mt-4 p-3 bg-white rounded">
                  <p className="text-sm text-gray-600">Available Records</p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {patientData.mri_records?.length > 0 && <span className="px-3 py-1 bg-teal-100 text-teal-700 rounded text-xs">MRI ({patientData.mri_records.length})</span>}
                    {patientData.xray_records?.length > 0 && <span className="px-3 py-1 bg-cyan-100 text-cyan-700 rounded text-xs">X-Ray ({patientData.xray_records.length})</span>}
                    {patientData.ecg_records?.length > 0 && <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-xs">ECG ({patientData.ecg_records.length})</span>}
                    {patientData.blood_profile_records?.length > 0 && <span className="px-3 py-1 bg-red-100 text-red-700 rounded text-xs">Blood ({patientData.blood_profile_records.length})</span>}
                    {patientData.ct_scan_records?.length > 0 && <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded text-xs">CT Scan ({patientData.ct_scan_records.length})</span>}
                    {patientData.treatment_records?.length > 0 && <span className="px-3 py-1 bg-green-100 text-green-700 rounded text-xs">Treatment ({patientData.treatment_records.length})</span>}
                  </div>
                </div>
              </Card>
              <div className="flex gap-4">
                <Button onClick={() => setStep('search')} variant="outline" className="flex-1">Back</Button>
                <Button onClick={handleConfirmPatient} className="flex-1 bg-teal-600 hover:bg-teal-700">Confirm & Start Consultation</Button>
              </div>
            </div>
          )}

          {/* Step 3: Chat Interface */}
          {step === 'chat' && (
            <div className="space-y-4">
              {/* Patient Info Bar */}
              <Card className="p-3 bg-teal-50 flex items-center justify-between">
                <div>
                  <p className="font-semibold">{patientData.profile.name} ({patientData.profile.patient_id})</p>
                  <p className="text-xs text-gray-600">{patientData.profile.age}y / {patientData.profile.gender} / {patientData.profile.blood_group}</p>
                </div>
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    onClick={toggleVoice} 
                    variant="outline" 
                    className={voiceEnabled ? 'bg-green-100 hover:bg-green-200' : 'bg-gray-100 hover:bg-gray-200'}
                    data-testid="voice-toggle-btn"
                  >
                    {voiceEnabled ? '🔊 Voice On' : '🔇 Voice Off'}
                  </Button>
                  {isSpeaking && (
                    <Button size="sm" onClick={stopSpeaking} variant="outline" className="bg-red-100 hover:bg-red-200" data-testid="stop-speaking-btn">
                      ⏹️ Stop
                    </Button>
                  )}
                </div>
              </Card>

              {/* Chat Messages */}
              <div className="h-[350px] overflow-y-auto space-y-4 p-4 bg-gray-50 rounded">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] p-4 rounded-lg ${
                      msg.role === 'user' 
                        ? 'bg-teal-600 text-white' 
                        : 'bg-white border border-gray-200'
                    }`}>
                      {msg.isFileUpload && <p className="text-sm mb-1">📎 File Upload</p>}
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      
                      {/* Analysis-specific display */}
                      {msg.isAnalysis && msg.suggestions && (
                        <div className="mt-3 p-2 bg-blue-50 rounded">
                          <p className="text-xs font-semibold text-blue-700 mb-1">📝 Suggestions:</p>
                          <ul className="text-xs text-blue-600 list-disc list-inside">
                            {msg.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                          </ul>
                        </div>
                      )}
                      
                      {/* Evidence Cards with View Report Button */}
                      {msg.evidence && msg.evidence.length > 0 && (
                        <div className="mt-3 space-y-2">
                          <p className="text-xs font-semibold text-gray-500">📋 Supporting Evidence:</p>
                          {msg.evidence.map((ev, i) => (
                            <Card key={i} className="p-3 text-sm bg-gray-50">
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <p className="font-semibold text-teal-700">{ev.test_name || ev.treatment_name}</p>
                                  <p className="text-xs text-gray-600">📅 Date: {ev.test_date || ev.treatment_date}</p>
                                  <p className="text-xs">🔬 Result: <span className="font-medium">{ev.result}</span></p>
                                  {ev.medicines && <p className="text-xs">💊 Medicines: {ev.medicines}</p>}
                                  {ev.doctor && <p className="text-xs">👨‍⚕️ Doctor: {ev.doctor}</p>}
                                </div>
                                {ev.report_image && (
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    className="ml-2 text-xs bg-teal-50 hover:bg-teal-100"
                                    onClick={() => openReportViewer(ev.report_image, ev.test_name || ev.treatment_name)}
                                    data-testid={`view-report-btn-${i}`}
                                  >
                                    📄 View Report
                                  </Button>
                                )}
                              </div>
                            </Card>
                          ))}
                        </div>
                      )}
                      
                      {/* Department Tags */}
                      {msg.departments && msg.departments.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {msg.departments.map((dept, i) => (
                            <span key={i} className="px-2 py-0.5 bg-teal-100 text-teal-700 rounded text-xs">{dept}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {(loading || isAnalyzing) && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 p-4 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-teal-600 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-teal-600 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                        <div className="w-2 h-2 bg-teal-600 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                        <span className="text-sm text-gray-500 ml-2">
                          {isAnalyzing ? 'Analyzing document...' : 'DocAssist is thinking...'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* File Upload Section */}
              <div className="flex items-center gap-2 p-2 bg-gray-100 rounded-lg">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  accept="image/png,image/jpeg,image/webp,application/pdf"
                  className="hidden"
                  id="file-upload"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-white"
                  disabled={isAnalyzing}
                >
                  📎 Upload File
                </Button>
                {uploadedFile && (
                  <>
                    <span className="text-sm text-gray-600 truncate max-w-[200px]">
                      {uploadedFile.name}
                    </span>
                    <Button
                      size="sm"
                      onClick={handleFileAnalysis}
                      disabled={isAnalyzing}
                      className="bg-purple-600 hover:bg-purple-700"
                    >
                      {isAnalyzing ? 'Analyzing...' : '🔍 Analyze'}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setUploadedFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                    >
                      ✕
                    </Button>
                  </>
                )}
                <span className="text-xs text-gray-500 ml-auto">PNG, JPEG, PDF (max 10MB)</span>
              </div>

              {/* Input Area */}
              <div className="flex gap-2">
                <Input
                  placeholder="Ask anything about the patient's medical records..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !loading && !isAnalyzing && handleAskQuestion()}
                  className="flex-1"
                  data-testid="chat-input"
                />
                <Button
                  onClick={isListening ? stopListening : startListening}
                  variant="outline"
                  className={isListening ? 'bg-red-100 animate-pulse' : 'hover:bg-teal-50'}
                  disabled={loading || isAnalyzing}
                  data-testid="mic-button"
                  title="Click to speak your question"
                >
                  {isListening ? '🎤 Listening...' : '🎤'}
                </Button>
                <Button
                  onClick={handleAskQuestion}
                  disabled={loading || isAnalyzing || !question.trim()}
                  className="bg-teal-600 hover:bg-teal-700"
                  data-testid="send-button"
                >
                  Send
                </Button>
              </div>
              
              {/* Voice Status Indicator */}
              {isListening && (
                <div className="text-center text-sm text-teal-600 animate-pulse">
                  🎤 Listening... Speak your question now
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Report Viewer Modal */}
      <ReportViewerModal 
        open={reportModal.open}
        onClose={() => setReportModal({ open: false, url: '', title: '' })}
        reportUrl={reportModal.url}
        reportTitle={reportModal.title}
      />
    </>
  );
};

export default DeepSearchModal;
