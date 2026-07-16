import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DepartmentView = () => {
  const navigate = useNavigate();
  const { departmentName } = useParams();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  useEffect(() => {
    if (departmentName) {
      fetchDepartmentData();
    }
  }, [departmentName]);

  const fetchDepartmentData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/department/${departmentName}`);
      setData(response.data);
    } catch (error) {
      console.error('Error fetching department data:', error);
      toast.error('Error fetching department records');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const getDepartmentInfo = () => {
    const icons = {
      'mri': { 
        icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774299.png',
        color: 'from-teal-500 to-teal-600', 
        name: 'MRI Scan' 
      },
      'xray': { 
        icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774337.png',
        color: 'from-cyan-500 to-cyan-600', 
        name: 'X-Ray' 
      },
      'ecg': { 
        icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774278.png',
        color: 'from-blue-500 to-blue-600', 
        name: 'ECG' 
      },
      'blood-test': { 
        icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774220.png',
        color: 'from-red-500 to-red-600', 
        name: 'Blood Profile' 
      },
      'ct-scan': { 
        icon: 'https://cdn-icons-png.flaticon.com/512/2966/2966334.png',
        color: 'from-purple-500 to-purple-600', 
        name: 'CT Scan' 
      },
      'treatment': { 
        icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774286.png',
        color: 'from-green-500 to-green-600', 
        name: 'Treatment' 
      }
    };
    return icons[departmentName] || { 
      icon: 'https://cdn-icons-png.flaticon.com/512/3774/3774220.png',
      color: 'from-gray-500 to-gray-600', 
      name: departmentName 
    };
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortedRecords = () => {
    if (!data || !data.records) return [];
    
    const sortedRecords = [...data.records];
    
    if (sortConfig.key) {
      sortedRecords.sort((a, b) => {
        let aValue, bValue;
        
        if (sortConfig.key === 'date') {
          aValue = new Date(a.treatment_date || a.test_date);
          bValue = new Date(b.treatment_date || b.test_date);
        } else if (sortConfig.key === 'patient_id') {
          aValue = a.patient_id;
          bValue = b.patient_id;
        } else if (sortConfig.key === 'name') {
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
        }
        
        if (aValue < bValue) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    
    return sortedRecords;
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return (
        <svg className="w-4 h-4 ml-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    
    if (sortConfig.direction === 'asc') {
      return (
        <svg className="w-4 h-4 ml-1 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      );
    }
    
    return (
      <svg className="w-4 h-4 ml-1 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{
        background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
      }}>
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading profile records...</p>
        </div>
      </div>
    );
  }

  if (!data || !data.records || data.records.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{
        background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
      }}>
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3">No Records Found</h2>
          <p className="text-gray-600 mb-6">No records available for this profile</p>
          <Button
            onClick={() => navigate('/search')}
            className="bg-teal-600 hover:bg-teal-700"
          >
            Back to Search
          </Button>
        </div>
      </div>
    );
  }

  const deptInfo = getDepartmentInfo();
  const isTreatment = departmentName === 'treatment';
  const sortedRecords = getSortedRecords();

  return (
    <div className="min-h-screen p-4 py-8" style={{
      background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
    }}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate('/search')}
            className="flex items-center text-gray-600 hover:text-teal-600 transition-colors"
            data-testid="back-to-search-link"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Search
          </button>
        </div>

        {/* Department Header */}
        <Card className="p-8 mb-8 bg-white shadow-xl border-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className={`w-24 h-24 bg-gradient-to-br ${deptInfo.color} rounded-2xl flex items-center justify-center shadow-lg p-4`}>
                {deptInfo.name === 'MRI Scan' && (
                  <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                    <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="3" opacity="0.3"/>
                    <circle cx="32" cy="32" r="20" stroke="currentColor" strokeWidth="2.5"/>
                    <circle cx="32" cy="32" r="12" stroke="currentColor" strokeWidth="2"/>
                    <path d="M32 20 L32 12 M32 44 L32 52 M20 32 L12 32 M44 32 L52 32" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                    <circle cx="32" cy="32" r="4" fill="currentColor"/>
                  </svg>
                )}
                {deptInfo.name === 'X-Ray' && (
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
                {deptInfo.name === 'ECG' && (
                  <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                    <rect x="8" y="20" width="48" height="24" stroke="currentColor" strokeWidth="2" rx="3" opacity="0.3"/>
                    <polyline points="8,32 16,32 20,24 24,40 28,28 32,32 36,32 40,24 44,40 48,28 52,32 56,32" 
                      stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                    <circle cx="32" cy="32" r="2" fill="currentColor"/>
                  </svg>
                )}
                {deptInfo.name === 'Blood Profile' && (
                  <svg className="w-full h-full text-white" viewBox="0 0 64 64" fill="none">
                    <path d="M32 12 C28 18, 24 24, 24 32 C24 40, 28 44, 32 44 C36 44, 40 40, 40 32 C40 24, 36 18, 32 12 Z" 
                      fill="currentColor" opacity="0.8"/>
                    <path d="M28 32 C28 36, 29 38, 32 38 C35 38, 36 36, 36 32 C36 28, 34 24, 32 20 C30 24, 28 28, 28 32 Z" 
                      fill="currentColor" opacity="0.5"/>
                    <rect x="26" y="44" width="12" height="8" rx="1" stroke="currentColor" strokeWidth="2" fill="none"/>
                    <line x1="26" y1="48" x2="38" y2="48" stroke="currentColor" strokeWidth="1"/>
                  </svg>
                )}
                {deptInfo.name === 'CT Scan' && (
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
                {deptInfo.name === 'Treatment' && (
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
              <div>
                <h1 className="text-3xl font-bold text-gray-800 mb-2" data-testid="department-heading">
                  {deptInfo.name} Profile
                </h1>
                <p className="text-lg text-teal-600 font-semibold">Total Records: {data.total}</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Records Table */}
        <Card className="p-6 bg-white shadow-lg border-0">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">All Patient Records</h2>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead 
                    className="cursor-pointer hover:bg-gray-50 select-none"
                    onClick={() => handleSort('date')}
                  >
                    <div className="flex items-center">
                      Date
                      <SortIcon columnKey="date" />
                    </div>
                  </TableHead>
                  <TableHead 
                    className="cursor-pointer hover:bg-gray-50 select-none"
                    onClick={() => handleSort('patient_id')}
                  >
                    <div className="flex items-center">
                      Patient ID
                      <SortIcon columnKey="patient_id" />
                    </div>
                  </TableHead>
                  <TableHead 
                    className="cursor-pointer hover:bg-gray-50 select-none"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center">
                      Patient Name
                      <SortIcon columnKey="name" />
                    </div>
                  </TableHead>
                  {isTreatment ? (
                    <>
                      <TableHead>Treatment</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Doctor</TableHead>
                      <TableHead>Medicines</TableHead>
                    </>
                  ) : (
                    <>
                      <TableHead>Test Name</TableHead>
                      <TableHead>Result</TableHead>
                      <TableHead>Doctor</TableHead>
                    </>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedRecords.map((record, index) => (
                  <TableRow key={index} data-testid={`record-${index}`} className="hover:bg-gray-50">
                    <TableCell className="font-medium">
                      {formatDate(isTreatment ? record.treatment_date : record.test_date)}
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-teal-600 font-semibold">{record.patient_id}</span>
                    </TableCell>
                    <TableCell>{record.name}</TableCell>
                    {isTreatment ? (
                      <>
                        <TableCell>{record.treatment_name}</TableCell>
                        <TableCell>
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            record.result?.includes('Completed') || record.result?.includes('Successful') ? 'bg-green-100 text-green-700' :
                            record.result?.includes('Progress') ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {record.result}
                          </span>
                        </TableCell>
                        <TableCell>{record.doctor}</TableCell>
                        <TableCell>
                          {record.medicines ? (
                            <span className="text-sm text-gray-700">{record.medicines}</span>
                          ) : (
                            <span className="text-xs text-gray-400">N/A</span>
                          )}
                        </TableCell>
                      </>
                    ) : (
                      <>
                        <TableCell>{record.test_name}</TableCell>
                        <TableCell>
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            record.result?.includes('Normal') || record.result?.includes('Clear') || 
                            record.result?.includes('Within Range') ? 'bg-green-100 text-green-700' :
                            record.result?.includes('Critical') ? 'bg-red-100 text-red-700' :
                            'bg-yellow-100 text-yellow-700'
                          }`}>
                            {record.result}
                          </span>
                        </TableCell>
                        <TableCell>{record.doctor}</TableCell>
                      </>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default DepartmentView;