import React, { useState, useEffect } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const Analytics = () => {
  const [loading, setLoading] = useState(true);
  const [userGrowth, setUserGrowth] = useState({ labels: [], data: [] });
  const [planStats, setPlanStats] = useState({
    total_meal_plans: 0,
    total_workout_plans: 0,
    meal_plans_last_30_days: 0,
    workout_plans_last_30_days: 0
  });
  const [aiCoachStats, setAiCoachStats] = useState({
    total_sessions: 0,
    total_messages: 0,
    active_sessions_last_7_days: 0,
    avg_messages_per_session: 0
  });
  const [feastStats, setFeastStats] = useState({
    total_feasts: 0,
    active_feasts: 0,
    completed_feasts: 0,
    cancelled_feasts: 0,
    avg_banking_days: 0
  });
  const [demographics, setDemographics] = useState({
    gender_distribution: {},
    age_distribution: {}
  });

  useEffect(() => {
    fetchAllAnalytics();
  }, []);

  const fetchAllAnalytics = async () => {
    try {
      const headers = adminAuth.getAuthHeader();

      const [
        userGrowthRes,
        planStatsRes,
        aiCoachRes,
        feastStatsRes,
        demographicsRes
      ] = await Promise.all([
        fetch('http://localhost:8000/api/admin/analytics/user-growth', { headers }),
        fetch('http://localhost:8000/api/admin/analytics/plan-generation-stats', { headers }),
        fetch('http://localhost:8000/api/admin/analytics/ai-coach-usage', { headers }),
        fetch('http://localhost:8000/api/admin/analytics/feast-mode-stats', { headers }),
        fetch('http://localhost:8000/api/admin/analytics/user-demographics', { headers })
      ]);

      if (userGrowthRes.ok) {
        const data = await userGrowthRes.json();
        setUserGrowth(data);
      }

      if (planStatsRes.ok) {
        const data = await planStatsRes.json();
        setPlanStats(data);
      }

      if (aiCoachRes.ok) {
        const data = await aiCoachRes.json();
        setAiCoachStats(data);
      }

      if (feastStatsRes.ok) {
        const data = await feastStatsRes.json();
        setFeastStats(data);
      }

      if (demographicsRes.ok) {
        const data = await demographicsRes.json();
        setDemographics(data);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const userGrowthChartData = userGrowth.labels.map((label, index) => ({
    month: label,
    users: userGrowth.data[index]
  }));

  const planGenerationData = [
    { name: 'Meal Plans', total: planStats.total_meal_plans, last30Days: planStats.meal_plans_last_30_days },
    { name: 'Workout Plans', total: planStats.total_workout_plans, last30Days: planStats.workout_plans_last_30_days }
  ];

  const feastModeData = [
    { name: 'Active', value: feastStats.active_feasts, color: '#10b981' },
    { name: 'Completed', value: feastStats.completed_feasts, color: '#3b82f6' },
    { name: 'Cancelled', value: feastStats.cancelled_feasts, color: '#ef4444' }
  ];

  const genderData = Object.entries(demographics.gender_distribution).map(([gender, count]) => ({
    name: gender || 'Unknown',
    value: count,
    color: gender === 'male' ? '#3b82f6' : gender === 'female' ? '#ec4899' : '#6b7280'
  }));

  const ageData = Object.entries(demographics.age_distribution).map(([range, count]) => ({
    range,
    count
  }));

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-xl text-gray-600">Loading analytics...</div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-gray-600 mt-2">Comprehensive insights and statistics</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 text-sm">Total Chat Sessions</p>
                <p className="text-3xl font-bold mt-2">{aiCoachStats.total_sessions}</p>
              </div>
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                <span className="text-2xl">💬</span>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-100 text-sm">Total Messages</p>
                <p className="text-3xl font-bold mt-2">{aiCoachStats.total_messages}</p>
              </div>
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                <span className="text-2xl">📨</span>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-purple-100 text-sm">Avg Messages/Session</p>
                <p className="text-3xl font-bold mt-2">{aiCoachStats.avg_messages_per_session.toFixed(1)}</p>
              </div>
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                <span className="text-2xl">📊</span>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-orange-100 text-sm">Active Sessions (7d)</p>
                <p className="text-3xl font-bold mt-2">{aiCoachStats.active_sessions_last_7_days}</p>
              </div>
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                <span className="text-2xl">🔥</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">User Growth (12 Months)</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={userGrowthChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="month" 
                />
                <YAxis 
                  domain={[0, 100]}
                  ticks={[0, 20, 40, 60, 80, 100]}
                />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="users" stroke="#8b5cf6" strokeWidth={2} name="Total Users" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Plan Generation Statistics</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={planGenerationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="total" fill="#3b82f6" name="Total Plans" />
                <Bar dataKey="last30Days" fill="#10b981" name="Last 30 Days" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Feast Mode Status</h2>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={feastModeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {feastModeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">Avg Banking Days</p>
              <p className="text-2xl font-bold text-gray-900">{feastStats.avg_banking_days.toFixed(1)}</p>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Gender Distribution</h2>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={genderData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {genderData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Age Distribution</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={ageData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Plan Generation Summary</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Total Meal Plans</p>
                  <p className="text-2xl font-bold text-blue-600">{planStats.total_meal_plans}</p>
                </div>
                <span className="text-3xl">🍽️</span>
              </div>
              <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Total Workout Plans</p>
                  <p className="text-2xl font-bold text-purple-600">{planStats.total_workout_plans}</p>
                </div>
                <span className="text-3xl">💪</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Feast Mode Summary</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Total Feasts</p>
                  <p className="text-2xl font-bold text-green-600">{feastStats.total_feasts}</p>
                </div>
                <span className="text-3xl">🎉</span>
              </div>
              <div className="flex items-center justify-between p-4 bg-orange-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Currently Active</p>
                  <p className="text-2xl font-bold text-orange-600">{feastStats.active_feasts}</p>
                </div>
                <span className="text-3xl">🔥</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default Analytics;
