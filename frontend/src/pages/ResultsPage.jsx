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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
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
  const [reportImage, setReportImage] = useState(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [allRecordsChronological, setAllRecordsChronological] = useState([]);

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
      } else {
        // Combine all records into chronological order
        const allRecords = [];
        
        response.data.mri_records?.forEach(record => {
          allRecords.push({...record, type: 'MRI', date: record.test_date, department: 'MRI'});
        });
        
        response.data.xray_records?.forEach(record => {
          allRecords.push({...record, type: 'X-Ray', date: record.test_date, department: 'X-Ray'});
        });
        
        response.data.ecg_records?.forEach(record => {
          allRecords.push({...record, type: 'ECG', date: record.test_date, department: 'ECG'});
        });
        
        response.data.blood_profile_records?.forEach(record => {
          allRecords.push({...record, type: 'Blood Profile', date: record.test_date, department: 'Blood Profile'});
        });
        
        response.data.ct_scan_records?.forEach(record => {
          allRecords.push({...record, type: 'CT Scan', date: record.test_date, department: 'CT Scan'});
        });
        
        response.data.treatment_records?.forEach(record => {
          allRecords.push({...record, type: 'Treatment', date: record.treatment_date, department: 'Treatment'});
        });
        
        // Sort by date (ascending - oldest first)
        allRecords.sort((a, b) => new Date(a.date) - new Date(b.date));
        setAllRecordsChronological(allRecords);
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

  const handleViewReport = (imageUrl) => {
    setReportImage(imageUrl);
    setReportOpen(true);
  };

  const handleViewAnalytics = () => {
    if (data?.profile) {
      navigate(`/analytics?patient_id=${data.profile.patient_id}`);
    }
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
          <Button
            onClick={handleViewAnalytics}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white"
            data-testid="view-analytics-button"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            View Patient Analytics
          </Button>
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

        {/* All Records in Chronological Order */}
        <Card className="p-6 mb-6 bg-white shadow-lg border-0" data-testid="chronological-records">
          <div className="flex items-center mb-4">
            <div className="w-10 h-10 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-lg flex items-center justify-center mr-3">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800">Complete Medical History (Chronological)</h2>
          </div>
          <p className="text-sm text-gray-600 mb-4">All tests and treatments sorted by date</p>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Test/Treatment</TableHead>
                  <TableHead>Result</TableHead>
                  <TableHead>Doctor</TableHead>
                  <TableHead>Medicines</TableHead>
                  <TableHead>Report</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {allRecordsChronological.map((record, index) => (
                  <TableRow key={index} data-testid={`chronological-record-${index}`}>
                    <TableCell className="font-medium">{formatDate(record.date)}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-md text-xs font-semibold ${
                        record.department === 'MRI' ? 'bg-teal-100 text-teal-700' :
                        record.department === 'X-Ray' ? 'bg-cyan-100 text-cyan-700' :
                        record.department === 'ECG' ? 'bg-blue-100 text-blue-700' :
                        record.department === 'Blood Profile' ? 'bg-red-100 text-red-700' :
                        record.department === 'CT Scan' ? 'bg-purple-100 text-purple-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {record.department}
                      </span>
                    </TableCell>
                    <TableCell>{record.test_name || record.treatment_name}</TableCell>
                    <TableCell>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        record.result?.includes('Normal') || record.result?.includes('Clear') || 
                        record.result?.includes('Within Range') || record.result?.includes('Completed') || 
                        record.result?.includes('Successful') ? 'bg-green-100 text-green-700' :
                        record.result?.includes('Critical') ? 'bg-red-100 text-red-700' :
                        record.result?.includes('Progress') ? 'bg-blue-100 text-blue-700' :
                        'bg-yellow-100 text-yellow-700'
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
                    <TableCell>
                      {record.report_image ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleViewReport(record.report_image)}
                          className="text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                          data-testid={`view-report-${index}`}
                        >
                          View Report
                        </Button>
                      ) : (
                        <span className="text-xs text-gray-400">N/A</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>

        {/* No Records Message */}
        {allRecordsChronological.length === 0 && (
          <Card className="p-8 bg-white shadow-lg text-center">
            <p className="text-gray-600">No medical records found for this patient.</p>
          </Card>
        )}
      </div>

      {/* Report Image Modal */}
      <Dialog open={reportOpen} onOpenChange={setReportOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Medical Report</DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {reportImage && (
              <img 
                src={reportImage} 
                alt="Medical Report" 
                className="w-full h-auto rounded-lg shadow-lg"
                data-testid="report-image"
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ResultsPage;
