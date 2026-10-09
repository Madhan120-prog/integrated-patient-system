import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from './ui/button';
import axios from 'axios';

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isLoginPage = location.pathname === '/';

  const [term, setTerm] = useState('');
  const [patients, setPatients] = useState([]);

  // Names and IDs for the native autocomplete list; refetched after sign-in.
  useEffect(() => {
    if (isLoginPage || patients.length) return;
    axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/patients`)
      .then((res) => setPatients(res.data.patients || []))
      .catch(() => {});   // search still works by typing an ID or name
  }, [isLoginPage, patients.length]);

  const openChart = (e) => {
    e.preventDefault();
    const value = term.trim();
    if (!value) return;
    // "P1002 · Patricia Williams" (picked from the list) or free text
    navigate(`/chart/${encodeURIComponent(value.split(' · ')[0])}`);
    setTerm('');
  };

  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    navigate('/');
  };

  if (isLoginPage) {
    return null;
  }

  return (
    <header className="bg-gradient-to-r from-teal-600 to-cyan-600 shadow-md" data-testid="header">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Logo and Hospital Name */}
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center shadow-md overflow-hidden p-1">
            <img 
              src="/logo.png"
              alt="Patient Records System Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <div>
            <h1 className="text-white text-xl font-bold" data-testid="hospital-name">Patient Records System</h1>
            <p className="text-teal-100 text-xs">Integrated Patient Record System</p>
          </div>
        </div>

        <form onSubmit={openChart} role="search" className="flex-1 max-w-md mx-6 hidden sm:block">
          <input
            list="header-patient-list"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder="Search patient name or ID"
            aria-label="Search patient name or ID"
            data-testid="header-patient-search"
            className="w-full h-10 px-3 rounded-md text-sm text-slate-900 placeholder-slate-500 bg-white border border-white focus:outline-none focus:ring-2 focus:ring-teal-200"
          />
          <datalist id="header-patient-list">
            {patients.map((p) => <option key={p.patient_id} value={`${p.patient_id} · ${p.name}`} />)}
          </datalist>
        </form>

        {/* Logout Button */}
        <Button
          onClick={handleLogout}
          variant="outline"
          className="bg-white text-teal-600 hover:bg-teal-50 border-white"
          data-testid="header-logout-button"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Logout
        </Button>
      </div>
    </header>
  );
};

export default Header;