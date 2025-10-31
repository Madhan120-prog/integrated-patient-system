import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
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
