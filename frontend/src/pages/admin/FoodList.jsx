import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';
import { Download, Upload, Plus, Search, Filter } from 'lucide-react';

const FoodList = () => {
  const navigate = useNavigate();
  const [foods, setFoods] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [dietTypeFilter, setDietTypeFilter] = useState('');
  const [mealTypeFilter, setMealTypeFilter] = useState('');
  const [regionFilter, setRegionFilter] = useState('');
  const [regions, setRegions] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const pageSize = 20;

  useEffect(() => {
    fetchFoods();
    fetchRegions();
  }, [page, searchTerm, dietTypeFilter, mealTypeFilter, regionFilter]);

  const fetchFoods = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      
      if (searchTerm) params.append('search', searchTerm);
      if (dietTypeFilter) params.append('diet_type', dietTypeFilter);
      if (mealTypeFilter) params.append('meal_type', mealTypeFilter);
      if (regionFilter) params.append('region', regionFilter);

      const response = await fetch(
        `http://localhost:8000/api/admin/foods?${params}`,
        {
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setFoods(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
      }
    } catch (error) {
      console.error('Error fetching foods:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRegions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/admin/foods/regions', {
        headers: adminAuth.getAuthHeader(),
      });
      if (response.ok) {
        const data = await response.json();
        setRegions(data.regions);
      }
    } catch (error) {
      console.error('Error fetching regions:', error);
    }
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
    setPage(1);
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (dietTypeFilter) params.append('diet_type', dietTypeFilter);
      if (mealTypeFilter) params.append('meal_type', mealTypeFilter);
      if (regionFilter) params.append('region', regionFilter);

      const response = await fetch(
        `http://localhost:8000/api/admin/foods/export/csv?${params}`,
        {
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'food_items.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error exporting foods:', error);
      alert('Failed to export foods');
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

      const response = await fetch('http://localhost:8000/api/admin/foods/import/csv', {
        method: 'POST',
        headers: {
          'Authorization': adminAuth.getAuthHeader().Authorization,
        },
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        alert(
          `Import completed!\nCreated: ${result.created}\nUpdated: ${result.updated}\nErrors: ${result.errors.length}`
        );
        setUploadFile(null);
        fetchFoods();
      } else {
        alert('Failed to import foods');
      }
    } catch (error) {
      console.error('Error importing foods:', error);
      alert('Failed to import foods');
    } finally {
      setUploading(false);
    }
  };

  const clearFilters = () => {
    setDietTypeFilter('');
    setMealTypeFilter('');
    setRegionFilter('');
    setSearchTerm('');
    setPage(1);
  };

  return (
    <AdminLayout>
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {/* Sticky Header Section */}
        <div className="shrink-0 space-y-4 pb-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Food Items</h1>
              <p className="text-gray-600 mt-1">Manage food database</p>
            </div>
            <button
              onClick={() => navigate('/admin/foods/new')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <Plus size={20} />
              Add Food Item
            </button>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex-1 min-w-200px">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type="text"
                    placeholder="Search by name or ID..."
                    value={searchTerm}
                    onChange={handleSearch}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <button
                onClick={() => setShowFilters(!showFilters)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
              >
                <Filter size={20} />
                Filters
              </button>

              <button
                onClick={handleExport}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
              >
                <Download size={20} />
                Export CSV
              </button>

              <div className="flex items-center gap-2">
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  className="hidden"
                  id="csv-upload"
                />
                <label
                  htmlFor="csv-upload"
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2 cursor-pointer"
                >
                  <Upload size={20} />
                  {uploadFile ? uploadFile.name : 'Choose CSV'}
                </label>
                {uploadFile && (
                  <button
                    onClick={handleImport}
                    disabled={uploading}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400"
                  >
                    {uploading ? 'Importing...' : 'Import'}
                  </button>
                )}
              </div>
            </div>

            {showFilters && (
              <div className="pt-4 border-t border-gray-200">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Diet Type
                    </label>
                    <select
                      value={dietTypeFilter}
                      onChange={(e) => {
                        setDietTypeFilter(e.target.value);
                        setPage(1);
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">All</option>
                      <option value="veg">Vegetarian</option>
                      <option value="non-veg">Non-Vegetarian</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Meal Type
                    </label>
                    <select
                      value={mealTypeFilter}
                      onChange={(e) => {
                        setMealTypeFilter(e.target.value);
                        setPage(1);
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">All</option>
                      <option value="breakfast">Breakfast</option>
                      <option value="lunch">Lunch</option>
                      <option value="dinner">Dinner</option>
                      <option value="snacks">Snacks</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Region
                    </label>
                    <select
                      value={regionFilter}
                      onChange={(e) => {
                        setRegionFilter(e.target.value);
                        setPage(1);
                      }}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">All</option>
                      {regions
                        .filter((region) => region !== 'USDA-API' && region !== 'Continental')
                        .map((region) => (
                          <option key={region} value={region}>
                            {region}
                          </option>
                        ))}
                    </select>
                  </div>
                </div>

                <button
                  onClick={clearFilters}
                  className="mt-3 text-sm text-blue-600 hover:text-blue-700"
                >
                  Clear all filters
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Scrollable Table Section */}
        <div className="flex-1 bg-white rounded-lg shadow-md overflow-hidden flex flex-col min-h-0">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : foods.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No food items found</div>
          ) : (
            <>
              <div className="flex-1 overflow-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Diet Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Meal Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Calories
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Protein
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Region
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {foods.map((food) => (
                      <tr key={food.fdc_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {food.fdc_id}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {food.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span
                            className={`px-2 py-1 rounded-full text-xs ${
                              food.diet_type === 'veg'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {food.diet_type}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 capitalize">
                          {food.meal_type}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {parseFloat(food.calories_kcal).toFixed(1)} kcal
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {parseFloat(food.protein_g).toFixed(1)}g
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {food.region || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button
                            onClick={() => navigate(`/admin/foods/${food.fdc_id}`)}
                            className="text-blue-600 hover:text-blue-800 font-medium"
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
              <div className="shrink-0 bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                <div className="text-sm text-gray-700">
                  Showing {(page - 1) * pageSize + 1} to{' '}
                  {Math.min(page * pageSize, total)} of {total} results
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(page - 1)}
                    disabled={page === 1}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 text-gray-700">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={page === totalPages}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
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

export default FoodList;
