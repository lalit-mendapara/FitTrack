import React from 'react';
import { Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import About from './pages/About';
import Signup from './pages/Signup';
import Login from './pages/Login';
import Profile from './pages/Profile';
import DietPlan from './pages/DietPlan';
import Dashboard from './pages/Dashboard';
import ProtectedRoute from './components/auth/ProtectedRoute';
import RedirectIfAuthenticated from './components/auth/RedirectIfAuthenticated';
import { AuthProvider } from './context/AuthContext';
import './index.css';

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route 
          path="/" 
          element={
            <RedirectIfAuthenticated>
              <LandingPage />
            </RedirectIfAuthenticated>
          } 
        />
        <Route path="/about" element={<About />} />
        <Route 
          path="/signup" 
          element={
            <RedirectIfAuthenticated>
              <Signup />
            </RedirectIfAuthenticated>
          } 
        />
        <Route 
          path="/login" 
          element={
            <RedirectIfAuthenticated>
              <Login />
            </RedirectIfAuthenticated>
          } 
        />
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/profile" 
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/diet-plan" 
          element={
            <ProtectedRoute>
              <DietPlan />
            </ProtectedRoute>
          } 
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;
