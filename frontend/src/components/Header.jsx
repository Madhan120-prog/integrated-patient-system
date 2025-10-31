import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from './ui/button';

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isLoginPage = location.pathname === '/';

  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('user');
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
          <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-md overflow-hidden">
            <img 
              src="https://customer-assets.emergentagent.com/job_patient-hub-17/artifacts/u6w0dqw1_Screenshot%202025-10-31%20at%2012.56.03%E2%80%AFPM.png" 
              alt="Hospital Logo" 
              className="w-full h-full object-contain p-1"
            />
          </div>
          <div>
            <h1 className="text-white text-xl font-bold" data-testid="hospital-name">City General Hospital</h1>
            <p className="text-teal-100 text-xs">Patient Record System</p>
          </div>
        </div>

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
