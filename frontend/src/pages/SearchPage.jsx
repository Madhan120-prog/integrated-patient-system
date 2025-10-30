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

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{
      background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
    }}>
      <div className="max-w-2xl w-full">
        {/* Back Button */}
        <button
          onClick={() => navigate('/')}
          className="mb-8 flex items-center text-gray-600 hover:text-teal-600 transition-colors"
          data-testid="back-button"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Home
        </button>

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
    </div>
  );
};

export default SearchPage;
