import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';
import DeepSearchModal from '../components/DeepSearchModal';

const SearchPage = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [deepSearchOpen, setDeepSearchOpen] = useState(false);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/results?term=${encodeURIComponent(searchTerm)}`);
    }
  };

  const departments = [
    {
      name: 'MRI Scan',
      icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774299.png',
      color: 'from-teal-400 to-teal-600',
      route: 'mri'
    },
    {
      name: 'X-Ray',
      icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774337.png',
      color: 'from-cyan-400 to-cyan-600',
      route: 'xray'
    },
    {
      name: 'ECG',
      icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774278.png',
      color: 'from-blue-400 to-blue-600',
      route: 'ecg'
    },
    {
      name: 'Blood Test',
      icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774220.png',
      color: 'from-red-400 to-red-600',
      route: 'blood-test'
    },
    {
      name: 'CT Scan',
      icon: 'https://cdn-icons-png.flaticon.com/512/2966/2966334.png',
      color: 'from-purple-400 to-purple-600',
      route: 'ct-scan'
    },
    {
      name: 'Treatment',
      icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774286.png',
      color: 'from-green-400 to-green-600',
      route: 'treatment'
    }
  ];

  const handleDepartmentClick = (route) => {
    navigate(`/department/${route}`);
  };

  return (
    <div className="min-h-screen p-4 py-8" style={{
      background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
    }}>
      <div className="max-w-6xl mx-auto">
        {/* Back Button */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/welcome')}
            className="flex items-center text-gray-600 hover:text-teal-600 transition-colors"
            data-testid="back-button"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Home
          </button>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Search Section */}
          <div>
            <Card className="p-10 bg-white/90 backdrop-blur-sm shadow-2xl border-0">
              {/* Header */}
              <div className="text-center mb-10">
                <div className="w-16 h-16 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                  <svg className="w-9 h-9 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-3" data-testid="search-heading">
                  Search Patient Records
                </h1>
                <p className="text-gray-600">
                  Enter Patient ID (e.g., P1001) or Patient Name
                </p>
              </div>

              {/* Search Form */}
              <form onSubmit={handleSearch} className="space-y-6">
                <div>
                  <Input
                    data-testid="search-input"
                    type="text"
                    placeholder="Enter Patient ID or Name..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="h-14 text-lg border-2 border-gray-200 focus:border-teal-500 rounded-lg px-5"
                  />
                </div>

                <Button
                  data-testid="search-button"
                  type="submit"
                  className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700 text-white rounded-lg shadow-md hover:shadow-lg transition-all duration-300"
                >
                  Search Records
                </Button>

                {/* Deep Search Button */}
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg blur opacity-25"></div>
                  <Button
                    type="button"
                    onClick={() => setDeepSearchOpen(true)}
                    className="relative w-full h-14 text-lg font-semibold bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-lg shadow-md hover:shadow-xl transition-all duration-300"
                  >
                    <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    🔍 Deep Search - AI Assistant
                  </Button>
                </div>
              </form>

              {/* Deep Search Modal */}
              <DeepSearchModal open={deepSearchOpen} onClose={() => setDeepSearchOpen(false)} />

              {/* Info Cards */}
              <div className="mt-10 grid grid-cols-2 gap-4">
                <div className="bg-teal-50 rounded-lg p-4 border border-teal-100">
                  <p className="text-sm font-semibold text-teal-700 mb-1">Search by ID</p>
                  <p className="text-xs text-gray-600">Use format: P1001</p>
                </div>
                <div className="bg-cyan-50 rounded-lg p-4 border border-cyan-100">
                  <p className="text-sm font-semibold text-cyan-700 mb-1">Search by Name</p>
                  <p className="text-xs text-gray-600">Partial matches supported</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Departments Section */}
          <div>
            <Card className="p-8 bg-white/90 backdrop-blur-sm shadow-2xl border-0">
              <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">Available Profiles</h2>
              <div className="grid grid-cols-2 gap-4">
                {departments.map((dept, index) => (
                  <div 
                    key={index} 
                    onClick={() => handleDepartmentClick(dept.route)}
                    className="group p-4 bg-gradient-to-br from-gray-50 to-white rounded-xl border-2 border-gray-100 hover:border-teal-300 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 cursor-pointer"
                    data-testid={`department-${dept.name.toLowerCase().replace(' ', '-')}`}
                  >
                    <div className="flex flex-col items-center text-center space-y-3">
                      <div className={`w-20 h-20 bg-gradient-to-br ${dept.color} rounded-2xl flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-300 p-3`}>
                        {dept.name === 'MRI Scan' && (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="3" opacity="0.3"/>
                            <circle cx="32" cy="32" r="20" stroke="currentColor" strokeWidth="2.5"/>
                            <circle cx="32" cy="32" r="12" stroke="currentColor" strokeWidth="2"/>
                            <path d="M32 20 L32 12 M32 44 L32 52 M20 32 L12 32 M44 32 L52 32" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                            <circle cx="32" cy="32" r="4" fill="currentColor"/>
                          </svg>
                        )}
                        {dept.name === 'X-Ray' && (
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
                        )}
                        {dept.name === 'ECG' && (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <rect x="8" y="20" width="48" height="24" stroke="currentColor" strokeWidth="2" rx="3" opacity="0.3"/>
                            <polyline points="8,32 16,32 20,24 24,40 28,28 32,32 36,32 40,24 44,40 48,28 52,32 56,32" 
                              stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                            <circle cx="32" cy="32" r="2" fill="currentColor"/>
                          </svg>
                        )}
                        {dept.name === 'Blood Test' && (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <path d="M32 12 C28 18, 24 24, 24 32 C24 40, 28 44, 32 44 C36 44, 40 40, 40 32 C40 24, 36 18, 32 12 Z" 
                              fill="currentColor" opacity="0.8"/>
                            <path d="M28 32 C28 36, 29 38, 32 38 C35 38, 36 36, 36 32 C36 28, 34 24, 32 20 C30 24, 28 28, 28 32 Z" 
                              fill="currentColor" opacity="0.5"/>
                            <rect x="26" y="44" width="12" height="8" rx="1" stroke="currentColor" strokeWidth="2" fill="none"/>
                            <line x1="26" y1="48" x2="38" y2="48" stroke="currentColor" strokeWidth="1"/>
                          </svg>
                        )}
                        {dept.name === 'CT Scan' && (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <circle cx="32" cy="32" r="24" stroke="currentColor" strokeWidth="3" opacity="0.3"/>
                            <circle cx="32" cy="32" r="16" stroke="currentColor" strokeWidth="2.5"/>
                            <ellipse cx="32" cy="32" rx="8" ry="16" stroke="currentColor" strokeWidth="2" opacity="0.6"/>
                            <ellipse cx="32" cy="32" rx="16" ry="8" stroke="currentColor" strokeWidth="2" opacity="0.6"/>
                            <circle cx="32" cy="32" r="4" fill="currentColor"/>
                            <path d="M32 8 L32 14 M32 50 L32 56 M8 32 L14 32 M50 32 L56 32" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                          </svg>
                        )}
                        {dept.name === 'Treatment' && (
                          <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                            <rect x="28" y="12" width="8" height="40" rx="2" fill="currentColor"/>
                            <rect x="12" y="28" width="40" height="8" rx="2" fill="currentColor"/>
                            <circle cx="32" cy="32" r="8" stroke="currentColor" strokeWidth="2.5" fill="none"/>
                            <path d="M38 20 L44 20 C46 20, 48 22, 48 24 L48 28" 
                              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.7"/>
                            <circle cx="48" cy="32" r="3" fill="currentColor" opacity="0.7"/>
                          </svg>
                        )}
                      </div>
                      <p className="text-sm font-semibold text-gray-700">{dept.name}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-center text-gray-500 mt-6">
                Click on any profile to view all patient records
              </p>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SearchPage;