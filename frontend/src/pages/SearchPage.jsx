import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowRight, ArrowUpRight, Building2, Search, Stethoscope, Users } from 'lucide-react';
import DocAssistDialog from '../components/DocAssistDialog';
import { DocAssistOrb } from '../components/ChartVisuals';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DEPARTMENTS = [
  { name: 'MRI Scan', color: 'from-teal-400 to-teal-600', route: 'mri', caption: 'Brain, breast and spine studies' },
  { name: 'X-Ray', color: 'from-cyan-400 to-cyan-600', route: 'xray', caption: 'Chest and skeletal films' },
  { name: 'ECG', color: 'from-blue-400 to-blue-600', route: 'ecg', caption: 'Cardiac tracings' },
  { name: 'Blood Test', color: 'from-red-400 to-red-600', route: 'blood-test', caption: 'Counts, markers and panels' },
  { name: 'CT Scan', color: 'from-purple-400 to-purple-600', route: 'ct-scan', caption: 'Chest and abdominal scans' },
  { name: 'Treatment', color: 'from-green-400 to-green-600', route: 'treatment', caption: 'Surgery, chemotherapy and more' },
];

// The six department icons, unchanged from the original page.
const DepartmentIcon = ({ name }) => {
  switch (name) {
    case 'MRI Scan': return (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="3" opacity="0.3"/>
                            <circle cx="32" cy="32" r="20" stroke="currentColor" strokeWidth="2.5"/>
                            <circle cx="32" cy="32" r="12" stroke="currentColor" strokeWidth="2"/>
                            <path d="M32 20 L32 12 M32 44 L32 52 M20 32 L12 32 M44 32 L52 32" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                            <circle cx="32" cy="32" r="4" fill="currentColor"/>
                          </svg>
    );
    case 'X-Ray': return (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <rect x="8" y="8" width="48" height="48" stroke="currentColor" strokeWidth="2" rx="4" opacity="0.2"/>
                            <path d="M20 18 L44 18 L42 24 L22 24 Z" fill="currentColor" opacity="0.6"/>
                            <path d="M26 26 L26 48" stroke="currentColor" strokeWidth="2.5"/>
                            <path d="M32 26 L32 48" stroke="currentColor" strokeWidth="2.5"/>
                            <path d="M38 26 L38 48" stroke="currentColor" strokeWidth="2.5"/>
                            <path d="M20 32 L24 32 M40 32 L44 32" stroke="currentColor" strokeWidth="2"/>
                            <path d="M20 40 L24 40 M40 40 L44 40" stroke="currentColor" strokeWidth="2"/>
                            <circle cx="32" cy="48" r="3" fill="currentColor"/>
                          </svg>
    );
    case 'ECG': return (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <rect x="8" y="20" width="48" height="24" stroke="currentColor" strokeWidth="2" rx="3" opacity="0.3"/>
                            <polyline points="8,32 16,32 20,24 24,40 28,28 32,32 36,32 40,24 44,40 48,28 52,32 56,32" 
                              stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                            <circle cx="32" cy="32" r="2" fill="currentColor"/>
                          </svg>
    );
    case 'Blood Test': return (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <path d="M32 12 C28 18, 24 24, 24 32 C24 40, 28 44, 32 44 C36 44, 40 40, 40 32 C40 24, 36 18, 32 12 Z" 
                              fill="currentColor" opacity="0.8"/>
                            <path d="M28 32 C28 36, 29 38, 32 38 C35 38, 36 36, 36 32 C36 28, 34 24, 32 20 C30 24, 28 28, 28 32 Z" 
                              fill="currentColor" opacity="0.5"/>
                            <rect x="26" y="44" width="12" height="8" rx="1" stroke="currentColor" strokeWidth="2" fill="none"/>
                            <line x1="26" y1="48" x2="38" y2="48" stroke="currentColor" strokeWidth="1"/>
                          </svg>
    );
    case 'CT Scan': return (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <circle cx="32" cy="32" r="24" stroke="currentColor" strokeWidth="3" opacity="0.3"/>
                            <circle cx="32" cy="32" r="16" stroke="currentColor" strokeWidth="2.5"/>
                            <ellipse cx="32" cy="32" rx="8" ry="16" stroke="currentColor" strokeWidth="2" opacity="0.6"/>
                            <ellipse cx="32" cy="32" rx="16" ry="8" stroke="currentColor" strokeWidth="2" opacity="0.6"/>
                            <circle cx="32" cy="32" r="4" fill="currentColor"/>
                            <path d="M32 8 L32 14 M32 50 L32 56 M8 32 L14 32 M50 32 L56 32" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                          </svg>
    );
    case 'Treatment': return (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <rect x="28" y="12" width="8" height="40" rx="2" fill="currentColor"/>
                            <rect x="12" y="28" width="40" height="8" rx="2" fill="currentColor"/>
                            <circle cx="32" cy="32" r="8" stroke="currentColor" strokeWidth="2.5" fill="none"/>
                            <path d="M38 20 L44 20 C46 20, 48 22, 48 24 L48 28" 
                              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.7"/>
                            <circle cx="48" cy="32" r="3" fill="currentColor" opacity="0.7"/>
                          </svg>
    );
    default: return null;
  }
};

// Landing screen after sign-in: search for a patient, or open a department's
// full record list. Search opens the patient chart.
const SearchPage = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [patients, setPatients] = useState([]);
  const [deepSearchOpen, setDeepSearchOpen] = useState(false);
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    axios.get(`${API}/patients`).then((res) => setPatients(res.data.patients || [])).catch(() => {});
  }, []);

  const openChart = (term) => navigate(`/chart/${encodeURIComponent(term)}`);
  const handleSearch = (e) => {
    e.preventDefault();
    if (searchTerm.trim()) openChart(searchTerm.trim());   // V5: search opens the chart; /results still exists
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-teal-50/40 to-sky-50 px-4 py-6">
      <div className="max-w-6xl mx-auto space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-slate-500">{user.name ? `Welcome back, ${user.name}` : 'Welcome back'}</p>
            <h1 className="text-2xl font-semibold text-slate-900" data-testid="search-heading">Search Patient Records</h1>
          </div>
          <dl className="flex flex-wrap gap-2">
            {[[Users, 'Patients', patients.length || ''], [Building2, 'Department systems', DEPARTMENTS.length], [Stethoscope, 'Signed in as', user.role ? user.role.toLowerCase() : '']]
              .filter(([, , value]) => value !== '').map(([Icon, label, value]) => (
                <div key={label} className="card-raised flex items-center gap-2.5 rounded-2xl bg-white border border-slate-200/70 px-3.5 py-2">
                  <span className="w-8 h-8 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center"><Icon className="w-4 h-4" aria-hidden="true" /></span>
                  <span><dt className="text-[11px] text-slate-500 leading-tight">{label}</dt><dd className="text-sm font-semibold text-slate-900 leading-tight capitalize">{value}</dd></span>
                </div>
              ))}
          </dl>
        </div>

        <div className="grid md:grid-cols-2 gap-5 items-start">
          <div className="space-y-5">
            <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-teal-700 via-teal-600 to-cyan-600 text-white card-raised p-6 sm:p-7">
              <span className="absolute -top-16 -right-12 w-56 h-56 rounded-full bg-white/10" aria-hidden="true" />
              <span className="absolute -bottom-20 -left-10 w-48 h-48 rounded-full bg-cyan-300/20" aria-hidden="true" />
              <div className="relative">
                <span className="w-12 h-12 rounded-2xl bg-white/20 ring-1 ring-white/30 flex items-center justify-center"><Search className="w-6 h-6" aria-hidden="true" /></span>
                <h2 className="text-xl font-semibold mt-4">Find a patient</h2>
                <p className="text-sm text-teal-50 mt-1">One search across every department system. Opens the full chart.</p>
                <form onSubmit={handleSearch} className="mt-5 space-y-3">
                  <input
                    data-testid="search-input"
                    type="text"
                    placeholder="Enter Patient ID or Name..."
                    aria-label="Patient ID or name"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full h-14 rounded-2xl bg-white px-5 text-base text-slate-900 placeholder-slate-400 shadow-lg focus:outline-none focus:ring-4 focus:ring-white/40"
                  />
                  <button data-testid="search-button" type="submit"
                    className="w-full py-3.5 rounded-2xl bg-slate-900 text-white text-base font-semibold inline-flex items-center justify-center gap-2 shadow-lg transition-transform hover:-translate-y-0.5 hover:bg-slate-800 active:translate-y-0">
                    Search Records<ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </button>
                </form>
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-2xl bg-white/10 ring-1 ring-white/15 px-4 py-3">
                    <p className="font-medium">Search by ID</p><p className="text-xs text-teal-100">Use format: P1001</p>
                  </div>
                  <div className="rounded-2xl bg-white/10 ring-1 ring-white/15 px-4 py-3">
                    <p className="font-medium">Search by Name</p><p className="text-xs text-teal-100">Partial matches supported</p>
                  </div>
                </div>
              </div>
            </section>

            <section className="relative overflow-hidden card-raised rounded-3xl bg-slate-900 text-white p-5">
              <span className="absolute -top-10 -right-8 w-36 h-36 rounded-full bg-teal-400/20" aria-hidden="true" />
              <div className="relative flex items-center gap-4">
                <DocAssistOrb size={52} />
                <div className="min-w-0 flex-1">
                  <h2 className="text-base font-semibold">DocAssist Clinical Assistant</h2>
                  <p className="text-xs text-slate-300 mt-0.5">Ask by voice or text, pull up a scan, or attach a report or visit recording.</p>
                </div>
              </div>
              <button type="button" onClick={() => setDeepSearchOpen(true)} data-testid="docassist-button"
                className="relative mt-4 w-full inline-flex items-center justify-center gap-1.5 rounded-2xl bg-white text-slate-900 text-sm font-semibold px-4 py-3 transition-transform hover:-translate-y-0.5 hover:bg-teal-50">
                Open DocAssist<ArrowUpRight className="w-4 h-4" aria-hidden="true" />
              </button>
            </section>
            <DocAssistDialog open={deepSearchOpen} onClose={() => setDeepSearchOpen(false)} />
          </div>

          <section className="card-raised rounded-3xl bg-white border border-slate-200/70 p-6" aria-label="Available profiles">
            <h2 className="text-xl font-semibold text-slate-900">Available Profiles</h2>
            <p className="text-sm text-slate-500 mt-1">Each is a separate department system. Open one to see all its patient records.</p>
            <div className="grid grid-cols-2 gap-4 mt-5">
              {DEPARTMENTS.map((dept) => (
                <button
                  key={dept.name}
                  onClick={() => navigate(`/department/${dept.route}`)}
                  data-testid={`department-${dept.name.toLowerCase().replace(' ', '-')}`}
                  className="group lift card-raised text-left rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-700"
                >
                  <div className={`w-16 h-16 bg-gradient-to-br ${dept.color} rounded-2xl flex items-center justify-center shadow-md p-3 transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-3`}>
                    <DepartmentIcon name={dept.name} />
                  </div>
                  <p className="text-base font-semibold text-slate-900 mt-3 flex items-center gap-1.5">
                    {dept.name}
                    <ArrowRight className="w-4 h-4 text-slate-400 transition-transform duration-300 group-hover:translate-x-1 group-hover:text-teal-700" aria-hidden="true" />
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">{dept.caption}</p>
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default SearchPage;
