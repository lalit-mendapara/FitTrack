import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { adminAuth } from '../../utils/adminAuth';
import { ChartBar, ChartLineUp, Users, ForkKnife, Barbell, Confetti, Gear, CaretLeft, CaretRight } from '@phosphor-icons/react';

const AdminLayout = ({ children }) => {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const admin = adminAuth.getUser();

  const handleLogout = () => {
    adminAuth.logout();
    window.location.replace('/admin/login');
  };

  const navItems = [
    { path: '/admin/dashboard', icon: <ChartBar size={22} weight="duotone" />, label: 'Dashboard' },
    { path: '/admin/analytics', icon: <ChartLineUp size={22} weight="duotone" />, label: 'Analytics' },
    { path: '/admin/users', icon: <Users size={22} weight="duotone" />, label: 'Users' },
    { path: '/admin/foods', icon: <ForkKnife size={22} weight="duotone" />, label: 'Foods' },
    { path: '/admin/exercises', icon: <Barbell size={22} weight="duotone" />, label: 'Exercises' },
    { path: '/admin/feasts', icon: <Confetti size={22} weight="duotone" />, label: 'Feast Mode' },
    { path: '/admin/settings', icon: <Gear size={22} weight="duotone" />, label: 'Settings' },
  ];

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* Sidebar */}
      <aside className={`fixed left-0 top-0 h-full bg-slate-800 text-white transition-all duration-300 z-40 ${sidebarOpen ? 'w-64' : 'w-20'}`}>
        <div className="p-4 flex items-center justify-between border-b border-slate-700">
          {sidebarOpen && <h1 className="text-xl font-bold">FitTrack Admin</h1>}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-slate-700 rounded"
          >
            {sidebarOpen ? <CaretLeft size={18} weight="bold" /> : <CaretRight size={18} weight="bold" />}
          </button>
        </div>

        <nav className="p-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                location.pathname === item.path
                  ? 'bg-purple-600 text-white'
                  : 'hover:bg-slate-700'
              }`}
            >
              <span className="shrink-0">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-700">
          <div className={`flex items-center gap-3 ${!sidebarOpen && 'justify-center'}`}>
            <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center shrink-0">
              {admin?.email?.[0]?.toUpperCase() || 'A'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{admin?.email}</p>
                <button
                  onClick={handleLogout}
                  className="text-xs text-purple-300 hover:text-purple-200"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AdminLayout;
