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

  const getDepartmentIcon = () => {
    const icons = {
      'mri': { icon: '🔬', color: 'from-teal-500 to-teal-600', name: 'MRI Scan' },
      'xray': { icon: '📷', color: 'from-cyan-500 to-cyan-600', name: 'X-Ray' },
      'ecg': { icon: '💓', color: 'from-blue-500 to-blue-600', name: 'ECG' },
      'blood-test': { icon: '🩸', color: 'from-red-500 to-red-600', name: 'Blood Profile' },
      'ct-scan': { icon: '🖥️', color: 'from-purple-500 to-purple-600', name: 'CT Scan' },
      'treatment': { icon: '💊', color: 'from-green-500 to-green-600', name: 'Treatment' }
    };
    return icons[departmentName] || { icon: '🏥', color: 'from-gray-500 to-gray-600', name: departmentName };
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{
        background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
      }}>
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading department records...</p>
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
          <p className="text-gray-600 mb-6">No records available for this department</p>
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

  const deptInfo = getDepartmentIcon();
  const isTreatment = departmentName === 'treatment';

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
              <div className={`w-20 h-20 bg-gradient-to-br ${deptInfo.color} rounded-2xl flex items-center justify-center shadow-lg text-4xl`}>
                {deptInfo.icon}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-800 mb-2" data-testid="department-heading">
                  {deptInfo.name} Department
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
                  <TableHead>Date</TableHead>
                  <TableHead>Patient ID</TableHead>
                  <TableHead>Patient Name</TableHead>
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
                {data.records.map((record, index) => (
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
