import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import axios from 'axios';
import { toast } from 'sonner';
import { BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#14B8A6', '#06B6D4', '#3B82F6', '#EF4444', '#A855F7', '#10B981'];

const AnalyticsPageWithCharts = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const patientId = searchParams.get('patient_id');

  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [patientInfo, setPatientInfo] = useState(null);

  useEffect(() => {
    if (patientId) {
      fetchAnalytics();
      fetchPatientInfo();
    }
  }, [patientId]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/analytics/${patientId}`);
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast.error('Error fetching analytics data');
    } finally {
      setLoading(false);
    }
  };

  const fetchPatientInfo = async () => {
    try {
      const response = await axios.get(`${API}/search?term=${patientId}`);
      setPatientInfo(response.data.profile);
    } catch (error) {
      console.error('Error fetching patient info:', error);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{
        background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
      }}>
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{
        background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
      }}>
        <div className="text-center">
          <p className="text-gray-600">No analytics data available</p>
          <Button onClick={() => navigate('/search')} className="mt-4">Back to Search</Button>
        </div>
      </div>
    );
  }

  // Prepare data for charts
  const departmentData = Object.entries(analytics.departments_visited).map(([name, value]) => ({
    name,
    tests: value
  }));

  const treatmentData = [
    { name: 'Completed', value: analytics.treatment_summary.completed, color: '#10B981' },
    { name: 'In Progress', value: analytics.treatment_summary.in_progress, color: '#3B82F6' },
    { name: 'Scheduled', value: analytics.treatment_summary.scheduled, color: '#6B7280' }
  ];

  const timelineData = analytics.visit_timeline.slice(-10).map(visit => ({
    date: formatDate(visit.date),
    visit: 1
  }));

  return (
    <div className="min-h-screen p-4 py-8" style={{
      background: 'linear-gradient(135deg, #e8f4f8 0%, #f0f9fc 100%)'
    }}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate(`/results?term=${patientId}`)}
            className="flex items-center text-gray-600 hover:text-teal-600 transition-colors"
            data-testid="back-to-results-link"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Patient Records
          </button>
        </div>

        {/* Patient Info Header */}
        {patientInfo && (
          <Card className="p-6 mb-8 bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-xl border-0">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold mb-1" data-testid="analytics-patient-name">{patientInfo.name}</h1>
                <p className="text-purple-100">Patient ID: {patientInfo.patient_id}</p>
              </div>
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <svg className="w-9 h-9 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
          </Card>
        )}

        {/* Key Metrics */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <Card className="p-6 bg-white shadow-lg hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-600">Total Visits</h3>
              <div className="w-10 h-10 bg-teal-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            </div>
            <p className="text-3xl font-bold text-gray-800" data-testid="total-visits">{analytics.total_visits}</p>
          </Card>

          <Card className="p-6 bg-white shadow-lg hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-600">Total Tests</h3>
              <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
            </div>
            <p className="text-3xl font-bold text-gray-800" data-testid="total-tests">{analytics.total_tests}</p>
          </Card>

          <Card className="p-6 bg-white shadow-lg hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-600">Health Trend</h3>
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
            <p className={`text-2xl font-bold ${
              analytics.health_trend === 'Excellent' ? 'text-green-600' :
              analytics.health_trend === 'Good' ? 'text-blue-600' :
              analytics.health_trend === 'Stable' ? 'text-yellow-600' :
              'text-red-600'
            }`} data-testid="health-trend">{analytics.health_trend}</p>
          </Card>

          <Card className="p-6 bg-white shadow-lg hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-600">Treatments</h3>
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
            <p className="text-3xl font-bold text-gray-800" data-testid="total-treatments">{analytics.treatment_summary.total}</p>
          </Card>
        </div>

        <div className="grid lg:grid-cols-2 gap-8 mb-8">
          {/* Department Breakdown Chart */}
          <Card className="p-6 bg-white shadow-lg">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Department Breakdown</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={departmentData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="tests" fill="#14B8A6" />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {/* Treatment Progress Pie Chart */}
          <Card className="p-6 bg-white shadow-lg">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Treatment Progress</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={treatmentData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {treatmentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-3 gap-4 mt-6">
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{analytics.treatment_summary.completed}</p>
                <p className="text-sm text-gray-600 mt-1">Completed</p>
              </div>
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">{analytics.treatment_summary.in_progress}</p>
                <p className="text-sm text-gray-600 mt-1">In Progress</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-600">{analytics.treatment_summary.scheduled}</p>
                <p className="text-sm text-gray-600 mt-1">Scheduled</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Visit Timeline Chart */}
        <Card className="p-6 bg-white shadow-lg mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Recent Visit Timeline</h2>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={timelineData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="visit" stroke="#8B5CF6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Visit Timeline List */}
        <Card className="p-6 bg-white shadow-lg">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Complete Visit History</h2>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {analytics.visit_timeline.map((visit, index) => (
              <div key={index} className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div className="w-2 h-2 bg-teal-600 rounded-full mt-2"></div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-gray-800">{visit.test}</span>
                    <span className="text-sm text-gray-500">{formatDate(visit.date)}</span>
                  </div>
                  <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                    visit.type === 'MRI' ? 'bg-teal-100 text-teal-700' :
                    visit.type === 'X-Ray' ? 'bg-cyan-100 text-cyan-700' :
                    visit.type === 'ECG' ? 'bg-blue-100 text-blue-700' :
                    visit.type === 'Blood Profile' ? 'bg-red-100 text-red-700' :
                    visit.type === 'CT Scan' ? 'bg-purple-100 text-purple-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {visit.type}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default AnalyticsPageWithCharts;
