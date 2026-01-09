import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";

import DeepSearchModal from "../components/DeepSearchModal";

const SearchPage = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");

  // ✅ Deep Search modal open/close only (no more inline modal logic here)
  const [isDeepOpen, setIsDeepOpen] = useState(false);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/results?term=${encodeURIComponent(searchTerm)}`);
    }
  };

  const departments = [
    {
      name: "MRI Scan",
      icon: "https://cdn-icons-png.flaticon.com/512/2913/2913133.png",
      color: "from-teal-400 to-teal-600",
      route: "mri",
    },
    {
      name: "X-Ray",
      icon: "https://cdn-icons-png.flaticon.com/512/2913/2913149.png",
      color: "from-cyan-400 to-cyan-600",
      route: "xray",
    },
    {
      name: "ECG",
      icon: "https://cdn-icons-png.flaticon.com/512/2913/2913099.png",
      color: "from-blue-400 to-blue-600",
      route: "ecg",
    },
    {
      name: "Blood Test",
      icon: "https://cdn-icons-png.flaticon.com/512/2913/2913145.png",
      color: "from-red-400 to-red-600",
      route: "blood-test",
    },
    {
      name: "CT Scan",
      icon: "https://cdn-icons-png.flaticon.com/512/2913/2913155.png",
      color: "from-purple-400 to-purple-600",
      route: "ct-scan",
    },
    {
      name: "Treatment",
      icon: "https://cdn-icons-png.flaticon.com/512/2913/2913115.png",
      color: "from-green-400 to-green-600",
      route: "treatment",
    },
  ];

  const handleDepartmentClick = (route) => {
    navigate(`/department/${route}`);
  };

  return (
    <div
      className="min-h-screen p-4 py-8"
      style={{
        background: "linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)",
      }}
    >
      <div className="max-w-6xl mx-auto">
        {/* Back Button */}
        <div className="mb-8">
          <button
            onClick={() => navigate("/welcome")}
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
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                </div>
                <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-3" data-testid="search-heading">
                  Search Patient Records
                </h1>
                <p className="text-gray-600">Enter Patient ID (e.g., P1001) or Patient Name</p>
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

                {/* Buttons Row */}
                <div className="grid grid-cols-2 gap-4">
                  <Button
                    data-testid="search-button"
                    type="submit"
                    className="h-14 text-lg font-semibold bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700 text-white rounded-lg shadow-md hover:shadow-lg transition-all duration-300"
                  >
                    Search Records
                  </Button>

                  <Button
                    type="button"
                    onClick={() => setIsDeepOpen(true)}
                    className="h-14 text-lg font-semibold bg-gray-900 hover:bg-black text-white rounded-lg shadow-md hover:shadow-lg transition-all duration-300"
                    data-testid="deep-search-button"
                  >
                    Deep Search
                  </Button>
                </div>
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
              <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">Available Departments</h2>
              <div className="grid grid-cols-2 gap-4">
                {departments.map((dept, index) => (
                  <div
                    key={index}
                    onClick={() => handleDepartmentClick(dept.route)}
                    className="group p-4 bg-gradient-to-br from-gray-50 to-white rounded-xl border-2 border-gray-100 hover:border-teal-300 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 cursor-pointer"
                    data-testid={`department-${dept.name.toLowerCase().replace(" ", "-")}`}
                  >
                    <div className="flex flex-col items-center text-center space-y-3">
                      <div
                        className={`w-16 h-16 bg-gradient-to-br ${dept.color} rounded-full flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-300`}
                      >
                        <img src={dept.icon} alt={dept.name} className="w-8 h-8 filter brightness-0 invert" />
                      </div>
                      <p className="text-sm font-semibold text-gray-700">{dept.name}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-center text-gray-500 mt-6">Search to view records from all departments</p>
            </Card>
          </div>
        </div>
      </div>

      {/* ✅ Use the modal component here */}
      <DeepSearchModal open={isDeepOpen} onClose={() => setIsDeepOpen(false)} />
    </div>
  );
};

export default SearchPage;