import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import axios from 'axios';

// Restore auth header on page refresh — token was stored at login time.
const _storedToken = localStorage.getItem('token');
if (_storedToken) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${_storedToken}`;
}
// Global 401 handler — invalid/expired token → back to login.
axios.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('isAuthenticated');
      localStorage.removeItem('user');
      window.location.href = '/';
    }
    return Promise.reject(err);
  }
);
import Header from './components/Header';
import LoginPage from './pages/LoginPage';
import WelcomePage from './pages/WelcomePage';
import SearchPage from './pages/SearchPage';
import ResultsPage from './pages/ResultsPageDepartments';
import AnalyticsPage from './pages/AnalyticsPageWithCharts';
import DepartmentView from './pages/DepartmentView';
import ProtectedRoute from './components/ProtectedRoute';
import { Toaster } from './components/ui/sonner';
import './App.css';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Header />
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/welcome" element={
            <ProtectedRoute>
              <WelcomePage />
            </ProtectedRoute>
          } />
          <Route path="/search" element={
            <ProtectedRoute>
              <SearchPage />
            </ProtectedRoute>
          } />
          <Route path="/results" element={
            <ProtectedRoute>
              <ResultsPage />
            </ProtectedRoute>
          } />
          <Route path="/analytics" element={
            <ProtectedRoute>
              <AnalyticsPage />
            </ProtectedRoute>
          } />
          <Route path="/department/:departmentName" element={
            <ProtectedRoute>
              <DepartmentView />
            </ProtectedRoute>
          } />
        </Routes>
        <Toaster />
      </BrowserRouter>
    </div>
  );
}

export default App;
