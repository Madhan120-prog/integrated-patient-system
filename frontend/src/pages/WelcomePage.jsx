import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const WelcomePage = () => {
  const navigate = useNavigate();
  const [isInitializing, setIsInitializing] = React.useState(false);
  const [userName, setUserName] = React.useState('');

  useEffect(() => {
    // Get user info
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    setUserName(user.name || 'User');
    
    // Initialize data on page load
    initializeData();
  }, []);

  const initializeData = async () => {
    setIsInitializing(true);
    try {
      const response = await axios.post(`${API}/init-data`);
      console.log('Data initialized:', response.data);
    } catch (error) {
      console.error('Error initializing data:', error);
    } finally {
      setIsInitializing(false);
    }
  };

  const handleContinue = () => {
    navigate('/search');
  };

  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('user');
    navigate('/');
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4 relative"
      style={{
        backgroundImage: 'url(https://images.unsplash.com/photo-1565262353342-6e919eab5b58)',
        backgroundSize: 'cover',
        backgroundPosition: 'center'
      }}
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-white/80 backdrop-blur-sm"></div>
      
      <div className="relative z-10 max-w-4xl w-full">
        {/* Logout Button */}
        <div className="flex justify-end mb-4">
          <Button
            onClick={handleLogout}
            variant="outline"
            className="bg-white/90"
            data-testid="logout-button"
          >
            Logout
          </Button>
        </div>

        <div className="text-center mb-12 space-y-6">
          {/* Medical Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-24 h-24 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-2xl flex items-center justify-center shadow-2xl transform hover:scale-105 transition-transform duration-300">
              <svg 
                className="w-14 h-14 text-white" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
                />
              </svg>
            </div>
          </div>

          {/* Heading */}
          <div>
            <p className="text-lg text-teal-600 font-semibold mb-2">Welcome, {userName}</p>
            <h1 
              className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-800 leading-tight"
              data-testid="welcome-heading"
            >
              United Patient Record
              <br />
              <span className="bg-gradient-to-r from-teal-600 to-cyan-600 bg-clip-text text-transparent">
                System
              </span>
            </h1>
          </div>

          {/* Subheading */}
          <p className="text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed">
            Seamlessly access and integrate patient records from multiple hospital departments including MRI, X-Ray, ECG, CT Scan, Blood Profile, and Treatment centers - all in one unified platform.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Card className="p-6 bg-white/90 backdrop-blur-sm border-teal-100 hover:shadow-lg transition-all duration-300 hover:-translate-y-1" data-testid="feature-card-multi">
            <div className="w-12 h-12 bg-teal-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Multi-Department</h3>
            <p className="text-sm text-gray-600">Access records from MRI, X-Ray, ECG, CT Scan, Blood Profile, and Treatment departments</p>
          </Card>

          <Card className="p-6 bg-white/90 backdrop-blur-sm border-cyan-100 hover:shadow-lg transition-all duration-300 hover:-translate-y-1" data-testid="feature-card-instant">
            <div className="w-12 h-12 bg-cyan-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Instant Search</h3>
            <p className="text-sm text-gray-600">Search by Patient ID or Name with partial match support</p>
          </Card>

          <Card className="p-6 bg-white/90 backdrop-blur-sm border-teal-100 hover:shadow-lg transition-all duration-300 hover:-translate-y-1" data-testid="feature-card-organized">
            <div className="w-12 h-12 bg-teal-100 rounded-lg flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Medical Reports</h3>
            <p className="text-sm text-gray-600">View detailed medical imaging and test reports with visual documentation</p>
          </Card>
        </div>

        {/* Continue Button */}
        <div className="text-center">
          <Button
            data-testid="continue-button"
            onClick={handleContinue}
            disabled={isInitializing}
            className="px-12 py-6 text-lg font-semibold bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700 text-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
          >
            {isInitializing ? 'Initializing System...' : 'Continue to Search'}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default WelcomePage;
