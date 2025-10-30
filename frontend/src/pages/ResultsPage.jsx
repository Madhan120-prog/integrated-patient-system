import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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

const ResultsPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const searchTerm = searchParams.get('term');

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    if (searchTerm) {
      fetchPatientData();
    }
  }, [searchTerm]);

  const fetchPatientData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/search?term=${encodeURIComponent(searchTerm)}`);
      setData(response.data);
      
      if (!response.data.profile) {
        toast.error('No patient found with that ID or Name');
      }
    } catch (error) {
      console.error('Error fetching patient data:', error);
      toast.error('Error fetching patient data');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{
        background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
      }}>
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading patient records...</p>
        </div>
      </div>
    );
  }

  if (!data || !data.profile) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{
        background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
      }}>
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3" data-testid="no-results-message">No Patient Found</h2>
          <p className="text-gray-600 mb-6">No records found for "{searchTerm}"</p>
          <Button
            onClick={() => navigate('/search')}
            className="bg-teal-600 hover:bg-teal-700"
            data-testid="back-to-search-button"
          >
            Back to Search
          </Button>
        </div>
      </div>
    );
  }

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
            New Search
          </button>
        </div>

        {/* Patient Profile */}
        <Card className="p-8 mb-8 bg-white shadow-xl border-0" data-testid="patient-profile">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2" data-testid="patient-name">{data.profile.name}</h1>
              <p className="text-lg text-teal-600 font-semibold" data-testid="patient-id">ID: {data.profile.patient_id}</p>
            </div>
            <div className="w-16 h-16 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-xl flex items-center justify-center shadow-lg">
              <svg className="w-9 h-9 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <div className="space-y-1">
              <p className="text-sm text-gray-500 font-medium">Age</p>
              <p className="text-lg text-gray-800" data-testid="patient-age">{data.profile.age} years</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-gray-500 font-medium">Gender</p>
              <p className="text-lg text-gray-800" data-testid="patient-gender">{data.profile.gender}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-gray-500 font-medium">Blood Group</p>
              <p className="text-lg text-gray-800" data-testid="patient-blood-group">{data.profile.blood_group}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-gray-500 font-medium">Phone</p>
              <p className="text-lg text-gray-800" data-testid="patient-phone">{data.profile.phone}</p>
            </div>
            <div className="space-y-1 md:col-span-2">
              <p className="text-sm text-gray-500 font-medium">Address</p>
              <p className="text-lg text-gray-800" data-testid="patient-address">{data.profile.address}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-gray-500 font-medium">Registration Date</p>
              <p className="text-lg text-gray-800" data-testid="patient-registration-date">{formatDate(data.profile.registration_date)}</p>
            </div>
          </div>
        </Card>

        {/* MRI Records */}
        {data.mri_records && data.mri_records.length > 0 && (
          <Card className="p-6 mb-6 bg-white shadow-lg border-0" data-testid="mri-section">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-teal-100 rounded-lg flex items-center justify-center mr-3">
                <svg className="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-800">MRI Records</h2>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Test Name</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Doctor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.mri_records.map((record, index) => (
                    <TableRow key={index} data-testid={`mri-record-${index}`}>
                      <TableCell className="font-medium">{record.test_name}</TableCell>
                      <TableCell>{formatDate(record.test_date)}</TableCell>
                      <TableCell>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          record.result.includes('Normal') ? 'bg-green-100 text-green-700' :
                          record.result.includes('Critical') ? 'bg-red-100 text-red-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {record.result}
                        </span>
                      </TableCell>
                      <TableCell>{record.doctor}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        )}

        {/* X-Ray Records */}
        {data.xray_records && data.xray_records.length > 0 && (
          <Card className="p-6 mb-6 bg-white shadow-lg border-0" data-testid="xray-section">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center mr-3">
                <svg className="w-6 h-6 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-800">X-Ray Records</h2>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Test Name</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Doctor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.xray_records.map((record, index) => (
                    <TableRow key={index} data-testid={`xray-record-${index}`}>
                      <TableCell className="font-medium">{record.test_name}</TableCell>
                      <TableCell>{formatDate(record.test_date)}</TableCell>
                      <TableCell>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          record.result.includes('Clear') || record.result.includes('Normal') ? 'bg-green-100 text-green-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {record.result}
                        </span>
                      </TableCell>
                      <TableCell>{record.doctor}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        )}

        {/* ECG Records */}
        {data.ecg_records && data.ecg_records.length > 0 && (
          <Card className="p-6 mb-6 bg-white shadow-lg border-0" data-testid="ecg-section">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-teal-100 rounded-lg flex items-center justify-center mr-3">
                <svg className="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-800">ECG Records</h2>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Test Name</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Doctor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.ecg_records.map((record, index) => (
                    <TableRow key={index} data-testid={`ecg-record-${index}`}>
                      <TableCell className="font-medium">{record.test_name}</TableCell>
                      <TableCell>{formatDate(record.test_date)}</TableCell>
                      <TableCell>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          record.result.includes('Normal') ? 'bg-green-100 text-green-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {record.result}
                        </span>
                      </TableCell>
                      <TableCell>{record.doctor}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        )}

        {/* Treatment Records */}
        {data.treatment_records && data.treatment_records.length > 0 && (
          <Card className="p-6 mb-6 bg-white shadow-lg border-0" data-testid="treatment-section">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center mr-3">
                <svg className="w-6 h-6 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-800">Treatment Records</h2>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Treatment Name</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Doctor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.treatment_records.map((record, index) => (
                    <TableRow key={index} data-testid={`treatment-record-${index}`}>
                      <TableCell className="font-medium">{record.treatment_name}</TableCell>
                      <TableCell>{formatDate(record.treatment_date)}</TableCell>
                      <TableCell>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          record.result.includes('Completed') || record.result.includes('Successful') ? 'bg-green-100 text-green-700' :
                          record.result.includes('Progress') ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {record.result}
                        </span>
                      </TableCell>
                      <TableCell>{record.doctor}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        )}

        {/* No Records Message */}
        {(!data.mri_records || data.mri_records.length === 0) &&
         (!data.xray_records || data.xray_records.length === 0) &&
         (!data.ecg_records || data.ecg_records.length === 0) &&
         (!data.treatment_records || data.treatment_records.length === 0) && (
          <Card className="p-8 bg-white shadow-lg text-center">
            <p className="text-gray-600">No medical records found for this patient.</p>
          </Card>
        )}
      </div>
    </div>
  );
};

export default ResultsPage;
