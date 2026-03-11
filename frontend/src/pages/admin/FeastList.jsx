import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';
import { Search, Filter, Calendar, TrendingUp } from 'lucide-react';
import { CheckCircle, XCircle } from '@phosphor-icons/react';

const FeastList = () => {
  const navigate = useNavigate();
  const [feasts, setFeasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isActiveFilter, setIsActiveFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [stats, setStats] = useState(null);

  const pageSize = 20;

  useEffect(() => {
    fetchFeasts();
    fetchStats();
  }, [page, searchTerm, statusFilter, isActiveFilter]);

  const fetchFeasts = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      
      if (searchTerm) params.append('search', searchTerm);
      if (statusFilter) params.append('status_filter', statusFilter);
      if (isActiveFilter !== '') params.append('is_active', isActiveFilter);

      const response = await fetch(
        `http://localhost:8000/api/admin/feasts?${params}`,
        {
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setFeasts(data.feasts);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      }
    } catch (error) {
      console.error('Error fetching feasts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/admin/feasts/stats/summary', {
        headers: adminAuth.getAuthHeader(),
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
    setPage(1);
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      BANKING: 'bg-blue-100 text-blue-800',
      FEAST_DAY: 'bg-purple-100 text-purple-800',
      COMPLETED: 'bg-green-100 text-green-800',
      CANCELLED: 'bg-gray-100 text-gray-800',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <AdminLayout>
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {/* Sticky Header Section */}
        <div className="shrink-0 space-y-4 pb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Feast Mode Oversight</h1>
            <p className="text-gray-600 mt-1">Monitor and manage user feast configurations</p>
          </div>

        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-sm text-gray-600">Total Feasts</div>
              <div className="text-2xl font-bold text-gray-900">{stats.total_feasts}</div>
            </div>
            <div className="bg-blue-50 p-4 rounded-lg shadow">
              <div className="text-sm text-blue-600">Active</div>
              <div className="text-2xl font-bold text-blue-900">{stats.active_feasts}</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg shadow">
              <div className="text-sm text-green-600">Banking</div>
              <div className="text-2xl font-bold text-green-900">{stats.banking_feasts}</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg shadow">
              <div className="text-sm text-purple-600">Completed</div>
              <div className="text-2xl font-bold text-purple-900">{stats.completed_feasts}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg shadow">
              <div className="text-sm text-gray-600">Cancelled</div>
              <div className="text-2xl font-bold text-gray-900">{stats.cancelled_feasts}</div>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg shadow">
              <div className="text-sm text-orange-600">Avg Deduction</div>
              <div className="text-2xl font-bold text-orange-900">{stats.average_daily_deduction} kcal</div>
            </div>
          </div>
        )}
        </div>

        {/* Scrollable Table Section */}
        <div className="flex-1 bg-white rounded-lg shadow overflow-hidden flex flex-col min-h-0">
          <div className="shrink-0 p-4 border-b border-gray-200">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  placeholder="Search by event name, user name, or email..."
                  value={searchTerm}
                  onChange={handleSearch}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <Filter className="w-4 h-4" />
                Filters
              </button>
            </div>

            {showFilters && (
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => {
                      setStatusFilter(e.target.value);
                      setPage(1);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Statuses</option>
                    <option value="BANKING">Banking</option>
                    <option value="FEAST_DAY">Feast Day</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="CANCELLED">Cancelled</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Active Status</label>
                  <select
                    value={isActiveFilter}
                    onChange={(e) => {
                      setIsActiveFilter(e.target.value);
                      setPage(1);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All</option>
                    <option value="true">Active Only</option>
                    <option value="false">Inactive Only</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {loading ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading feasts...</p>
            </div>
          ) : feasts.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Calendar className="w-12 h-12 mx-auto mb-2 text-gray-400" />
              <p>No feast configurations found</p>
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 sticky top-0 z-10">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">ID</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">User</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">Event</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">Event Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">Daily Deduction</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">Target Bank</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">Workout Boost</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {feasts.map((feast) => (
                      <tr key={feast.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">#{feast.id}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{feast.user_name}</div>
                          <div className="text-sm text-gray-500">{feast.user_email}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{feast.event_name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatDate(feast.event_date)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {getStatusBadge(feast.status)}
                          {!feast.is_active && (
                            <span className="ml-2 text-xs text-gray-500">(Inactive)</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{feast.daily_deduction} kcal</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{feast.target_bank_calories} kcal</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {feast.workout_boost_enabled ? (
                            <span className="inline-flex items-center gap-1 text-green-600 text-sm"><CheckCircle size={16} weight="fill" /> Enabled</span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-gray-400 text-sm"><XCircle size={16} weight="fill" /> Disabled</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button
                            onClick={() => navigate(`/admin/feasts/${feast.id}`)}
                            className="text-blue-600 hover:text-blue-900 font-medium"
                          >
                            View Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="shrink-0 px-6 py-4 border-t border-gray-200 flex items-center justify-between bg-white">
                <div className="text-sm text-gray-700">
                  Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total} feasts
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 text-gray-700">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AdminLayout>
  );
};

export default FeastList;
