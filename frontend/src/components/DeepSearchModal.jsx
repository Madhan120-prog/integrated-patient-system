import React, { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DeepSearchModal = ({ open, onClose }) => {
  const [step, setStep] = useState('search'); // search, confirm, chat
  const [patientInput, setPatientInput] = useState('');
  const [patientData, setPatientData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true); // Voice output toggle
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize speech recognition
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
        if (event.error !== 'no-speech') {
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
        toast.error('Could not start voice recognition');
      }
    } else {
      toast.error('Speech recognition not supported in this browser');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  };

  const speak = (text) => {
    if (!voiceEnabled) return; // Skip if voice is disabled
    
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
    const welcomeMsg = `Hello! I'm DocAssist, your AI clinical assistant. I have access to all medical records for ${patientData.profile.name} (${patientData.profile.patient_id}). You can ask me anything about their reports, tests, treatments, or medical history. How can I help you today?`;
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

  const handleClose = () => {
    stopSpeaking();
    stopListening();
    setStep('search');
    setPatientInput('');
    setPatientData(null);
    setMessages([]);
    setQuestion('');
    onClose();
  };

  return (
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
                className={isListening ? 'bg-red-100' : ''}
              >
                {isListening ? '⏹️ Stop' : '🎤 Speak'}
              </Button>
            </div>
            <Button
              onClick={handleSearchPatient}
              disabled={loading}
              className="w-full bg-teal-600 hover:bg-teal-700"
            >
              {loading ? 'Searching...' : 'Search Patient'}
            </Button>
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
                {/* Voice Toggle Button */}
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
            <div className="h-[400px] overflow-y-auto space-y-4 p-4 bg-gray-50 rounded">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] p-4 rounded-lg ${
                    msg.role === 'user' 
                      ? 'bg-teal-600 text-white' 
                      : 'bg-white border border-gray-200'
                  }`}>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    {msg.evidence && msg.evidence.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs font-semibold text-gray-500">📋 Supporting Evidence:</p>
                        {msg.evidence.map((ev, i) => (
                          <Card key={i} className="p-3 text-sm bg-gray-50">
                            <p className="font-semibold text-teal-700">{ev.test_name || ev.treatment_name}</p>
                            <p className="text-xs text-gray-600">📅 Date: {ev.test_date || ev.treatment_date}</p>
                            <p className="text-xs">🔬 Result: <span className="font-medium">{ev.result}</span></p>
                            {ev.medicines && <p className="text-xs">💊 Medicines: {ev.medicines}</p>}
                          </Card>
                        ))}
                      </div>
                    )}
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
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 p-4 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-teal-600 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-teal-600 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                      <div className="w-2 h-2 bg-teal-600 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                      <span className="text-sm text-gray-500 ml-2">DocAssist is thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="flex gap-2">
              <Input
                placeholder="Ask anything about the patient's medical records..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !loading && handleAskQuestion()}
                className="flex-1"
                data-testid="chat-input"
              />
              <Button
                onClick={isListening ? stopListening : startListening}
                variant="outline"
                className={isListening ? 'bg-red-100 animate-pulse' : 'hover:bg-teal-50'}
                disabled={loading}
                data-testid="mic-button"
              >
                {isListening ? '🎤 Listening...' : '🎤'}
              </Button>
              <Button
                onClick={handleAskQuestion}
                disabled={loading || !question.trim()}
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
  );
};

export default DeepSearchModal;
