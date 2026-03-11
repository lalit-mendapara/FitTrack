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
import AdminLogin from './pages/admin/AdminLogin';
import AdminDashboard from './pages/admin/AdminDashboard';
import UserList from './pages/admin/UserList';
import UserDetail from './pages/admin/UserDetail';
import FoodList from './pages/admin/FoodList';
import FoodForm from './pages/admin/FoodForm';
import ExerciseList from './pages/admin/ExerciseList';
import ExerciseForm from './pages/admin/ExerciseForm';
import FeastList from './pages/admin/FeastList';
import FeastDetail from './pages/admin/FeastDetail';
import Analytics from './pages/admin/Analytics';
import SystemSettings from './pages/admin/SystemSettings';
import AdminProtectedRoute from './components/admin/AdminProtectedRoute';
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
        
        {/* Admin Routes */}
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route 
          path="/admin/dashboard" 
          element={
            <AdminProtectedRoute>
              <AdminDashboard />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/users" 
          element={
            <AdminProtectedRoute>
              <UserList />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/users/:userId" 
          element={
            <AdminProtectedRoute>
              <UserDetail />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/foods" 
          element={
            <AdminProtectedRoute>
              <FoodList />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/foods/new" 
          element={
            <AdminProtectedRoute>
              <FoodForm />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/foods/:fdc_id" 
          element={
            <AdminProtectedRoute>
              <FoodForm />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/exercises" 
          element={
            <AdminProtectedRoute>
              <ExerciseList />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/exercises/new" 
          element={
            <AdminProtectedRoute>
              <ExerciseForm />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/exercises/:id" 
          element={
            <AdminProtectedRoute>
              <ExerciseForm />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/feasts" 
          element={
            <AdminProtectedRoute>
              <FeastList />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/feasts/:id" 
          element={
            <AdminProtectedRoute>
              <FeastDetail />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/analytics" 
          element={
            <AdminProtectedRoute>
              <Analytics />
            </AdminProtectedRoute>
          } 
        />
        <Route 
          path="/admin/settings" 
          element={
            <AdminProtectedRoute>
              <SystemSettings />
            </AdminProtectedRoute>
          } 
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;
