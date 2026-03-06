import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';
import { Download, Upload, Plus, Search, Filter, ImageOff } from 'lucide-react';

const ExerciseList = () => {
  const navigate = useNavigate();
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [muscleFilter, setMuscleFilter] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [categories, setCategories] = useState([]);
  const [muscles, setMuscles] = useState([]);
  const [difficulties, setDifficulties] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [imageErrors, setImageErrors] = useState({});

  const pageSize = 20;

  useEffect(() => {
    fetchExercises();
    fetchFilterOptions();
    setImageErrors({});
  }, [page, searchTerm, categoryFilter, muscleFilter, difficultyFilter]);

  const fetchExercises = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      
      if (searchTerm) params.append('search', searchTerm);
      if (categoryFilter) params.append('category', categoryFilter);
      if (muscleFilter) params.append('primary_muscle', muscleFilter);
      if (difficultyFilter) params.append('difficulty', difficultyFilter);

      const response = await fetch(
        `http://localhost:8000/api/admin/exercises?${params}`,
        {
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setExercises(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      }
    } catch (error) {
      console.error('Error fetching exercises:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchFilterOptions = async () => {
    try {
      const [categoriesRes, musclesRes, difficultiesRes] = await Promise.all([
        fetch('http://localhost:8000/api/admin/exercises/categories', {
          headers: adminAuth.getAuthHeader(),
        }),
        fetch('http://localhost:8000/api/admin/exercises/muscles', {
          headers: adminAuth.getAuthHeader(),
        }),
        fetch('http://localhost:8000/api/admin/exercises/difficulties', {
          headers: adminAuth.getAuthHeader(),
        }),
      ]);

      if (categoriesRes.ok) {
        const data = await categoriesRes.json();
        setCategories(data.categories);
      }
      if (musclesRes.ok) {
        const data = await musclesRes.json();
        setMuscles(data.muscles);
      }
      if (difficultiesRes.ok) {
        const data = await difficultiesRes.json();
        setDifficulties(data.difficulties);
      }
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
    setPage(1);
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (categoryFilter) params.append('category', categoryFilter);
      if (muscleFilter) params.append('primary_muscle', muscleFilter);
      if (difficultyFilter) params.append('difficulty', difficultyFilter);

      const response = await fetch(
        `http://localhost:8000/api/admin/exercises/export/csv?${params}`,
        {
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'exercises.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error exporting exercises:', error);
      alert('Failed to export exercises');
    }
  };

  const handleImport = async () => {
    if (!uploadFile) {
      alert('Please select a CSV file');
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', uploadFile);

      const response = await fetch('http://localhost:8000/api/admin/exercises/import/csv', {
        method: 'POST',
        headers: {
          'Authorization': adminAuth.getAuthHeader().Authorization,
        },
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        alert(
          `Import completed!\nCreated: ${result.created}\nErrors: ${result.errors.length}`
        );
        setUploadFile(null);
        fetchExercises();
      } else {
        alert('Failed to import exercises');
      }
    } catch (error) {
      console.error('Error importing exercises:', error);
      alert('Failed to import exercises');
    } finally {
      setUploading(false);
    }
  };

  const clearFilters = () => {
    setCategoryFilter('');
    setMuscleFilter('');
    setDifficultyFilter('');
    setSearchTerm('');
    setPage(1);
  };

  const getDifficultyBadge = (difficulty) => {
    const colors = {
      'Beginner': 'bg-green-100 text-green-800',
      'Intermediate': 'bg-yellow-100 text-yellow-800',
      'Advanced': 'bg-red-100 text-red-800',
    };
    return colors[difficulty] || 'bg-gray-100 text-gray-800';
  };

  const renderExerciseThumbnail = (exercise) => {
    if (!exercise.image_url) {
      return (
        <div className="h-16 w-16 rounded border border-gray-200 bg-gray-50 flex items-center justify-center">
          <span className="text-xs text-gray-400">No image</span>
        </div>
      );
    }

    if (imageErrors[exercise.id]) {
      return (
        <a
          href={exercise.image_url}
          target="_blank"
          rel="noreferrer"
          title={exercise.image_url}
          className="inline-flex h-16 w-16 rounded border border-gray-200 bg-gray-50 items-center justify-center"
        >
          <ImageOff size={22} className="text-gray-400" />
        </a>
      );
    }

    return (
      <a href={exercise.image_url} target="_blank" rel="noreferrer" title={exercise.image_url}>
        <img
          src={exercise.image_url}
          alt={exercise.name}
          className="h-16 w-16 object-cover rounded border border-gray-300 bg-gray-50"
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setImageErrors(prev => ({ ...prev, [exercise.id]: true }))}
        />
      </a>
    );
  };

  return (
    <AdminLayout>
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {/* Sticky Header Section */}
        <div className="shrink-0 space-y-4 pb-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Exercise Database</h1>
              <p className="text-gray-600 mt-1">Manage exercise library</p>
            </div>
            <button
              onClick={() => navigate('/admin/exercises/new')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus size={20} />
              Add Exercise
            </button>
          </div>

          <div className="bg-white rounded-lg shadow p-6 space-y-4">
            <div className="flex gap-4 items-center">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search by name, category, or muscle..."
                  value={searchTerm}
                  onChange={handleSearch}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <Filter size={20} />
                Filters
              </button>
            </div>

            {showFilters && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={categoryFilter}
                    onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Categories</option>
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Primary Muscle</label>
                  <select
                    value={muscleFilter}
                    onChange={(e) => { setMuscleFilter(e.target.value); setPage(1); }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Muscles</option>
                    {muscles.map(muscle => (
                      <option key={muscle} value={muscle}>{muscle}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty</label>
                  <select
                    value={difficultyFilter}
                    onChange={(e) => { setDifficultyFilter(e.target.value); setPage(1); }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Levels</option>
                    {difficulties.map(diff => (
                      <option key={diff} value={diff}>{diff}</option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-3">
                  <button
                    onClick={clearFilters}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear all filters
                  </button>
                </div>
              </div>
            )}

            <div className="flex gap-4">
              <div className="flex items-center gap-2">
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  className="text-sm"
                />
                <button
                  onClick={handleImport}
                  disabled={uploading || !uploadFile}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  <Upload size={20} />
                  {uploading ? 'Importing...' : 'Import CSV'}
                </button>
              </div>
              <button
                onClick={handleExport}
                className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                <Download size={20} />
                Export CSV
              </button>
            </div>
          </div>
        </div>

        {/* Scrollable Table Section */}
        <div className="flex-1 bg-white rounded-lg shadow overflow-hidden flex flex-col min-h-0">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading exercises...</div>
          ) : exercises.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No exercises found</div>
          ) : (
            <>
              <div className="flex-1 overflow-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0 z-10">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Primary Muscle</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Difficulty</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Image</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {exercises.map((exercise) => (
                      <tr key={exercise.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{exercise.id}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{exercise.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{exercise.category}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{exercise.primary_muscle}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getDifficultyBadge(exercise.difficulty)}`}>
                            {exercise.difficulty}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {renderExerciseThumbnail(exercise)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button
                            onClick={() => navigate(`/admin/exercises/${exercise.id}`)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Sticky Footer with Pagination */}
              <div className="shrink-0 bg-gray-50 px-6 py-4 flex items-center justify-between border-t border-gray-200">
                <div className="text-sm text-gray-700">
                  Showing {exercises.length} of {total} exercises
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 text-gray-700">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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

export default ExerciseList;
