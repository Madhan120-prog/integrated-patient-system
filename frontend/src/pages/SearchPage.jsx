import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card } from '../components/ui/card';

const SearchPage = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

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
              </form>

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
                      <div className={`w-20 h-20 bg-gradient-to-br ${dept.color} rounded-2xl flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-300 p-2`}>
                        {dept.name === 'MRI Scan' && (
                          <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h10v2H7z"/>
                          </svg>
                        )}
                        {dept.name === 'X-Ray' && (
                          <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM8 17.5c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5-1.5.67-1.5 1.5.67 1.5 1.5 1.5zM12 13c.55 0 1-.45 1-1s-.45-1-1-1-1 .45-1 1 .45 1 1 1zm4 4.5c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5-1.5.67-1.5 1.5.67 1.5 1.5 1.5z"/>
                          </svg>
                        )}
                        {dept.name === 'ECG' && (
                          <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M20.57 14.86L22 13.43 20.57 12 17 15.57 8.43 7 12 3.43 10.57 2 9.14 3.43 7.71 2 5.57 4.14 4.14 2.71 2.71 4.14l1.43 1.43L2 7.71l1.43 1.43L2 10.57 3.43 12 7 8.43 15.57 17 12 20.57 13.43 22l1.43-1.43L16.29 22l2.14-2.14 1.43 1.43 1.43-1.43-1.43-1.43L22 16.29z"/>
                          </svg>
                        )}
                        {dept.name === 'Blood Test' && (
                          <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2c-1.1 0-2 .9-2 2v7c0 2.21 1.79 4 4 4s4-1.79 4-4V4c0-1.1-.9-2-2-2h-4zm2 11c-1.1 0-2-.9-2-2V4h4v7c0 1.1-.9 2-2 2zm-2 3c0 2.76 2.24 5 5 5s5-2.24 5-5h-2c0 1.65-1.35 3-3 3s-3-1.35-3-3h-2z"/>
                          </svg>
                        )}
                        {dept.name === 'CT Scan' && (
                          <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm1-13h-2v6l5.25 3.15.75-1.23-4-2.42z"/>
                          </svg>
                        )}
                        {dept.name === 'Treatment' && (
                          <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M19 3H5c-1.1 0-1.99.9-1.99 2L3 19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zM11 7h2v2h-2zm0 4h2v6h-2z"/>
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