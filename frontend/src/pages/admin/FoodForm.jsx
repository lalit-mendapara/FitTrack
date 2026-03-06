import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';
import { ArrowLeft, Save, Trash2 } from 'lucide-react';

const FoodForm = () => {
  const navigate = useNavigate();
  const { fdc_id } = useParams();
  const isEdit = !!fdc_id;

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const [formData, setFormData] = useState({
    fdc_id: '',
    name: '',
    diet_type: 'veg',
    meal_type: 'breakfast',
    serving_size_g: '',
    protein_g: '',
    fat_g: '',
    carb_g: '',
    calories_kcal: '',
    region: '',
    vector_text: '',
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (isEdit) {
      fetchFood();
    }
  }, [fdc_id]);

  const fetchFood = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/admin/foods/${fdc_id}`,
        {
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setFormData({
          fdc_id: data.fdc_id,
          name: data.name,
          diet_type: data.diet_type,
          meal_type: data.meal_type,
          serving_size_g: data.serving_size_g || '',
          protein_g: data.protein_g,
          fat_g: data.fat_g,
          carb_g: data.carb_g,
          calories_kcal: data.calories_kcal,
          region: data.region || '',
          vector_text: data.vector_text || '',
        });
      } else {
        alert('Failed to load food item');
        navigate('/admin/foods');
      }
    } catch (error) {
      console.error('Error fetching food:', error);
      alert('Failed to load food item');
      navigate('/admin/foods');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.fdc_id.trim()) newErrors.fdc_id = 'FDC ID is required';
    if (!formData.name.trim()) newErrors.name = 'Name is required';
    if (!formData.diet_type) newErrors.diet_type = 'Diet type is required';
    if (!formData.meal_type) newErrors.meal_type = 'Meal type is required';
    if (!formData.protein_g || parseFloat(formData.protein_g) < 0)
      newErrors.protein_g = 'Valid protein value is required';
    if (!formData.fat_g || parseFloat(formData.fat_g) < 0)
      newErrors.fat_g = 'Valid fat value is required';
    if (!formData.carb_g || parseFloat(formData.carb_g) < 0)
      newErrors.carb_g = 'Valid carb value is required';
    if (!formData.calories_kcal || parseFloat(formData.calories_kcal) < 0)
      newErrors.calories_kcal = 'Valid calories value is required';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    try {
      setSaving(true);

      const payload = {
        ...formData,
        serving_size_g: formData.serving_size_g ? parseFloat(formData.serving_size_g) : null,
        protein_g: parseFloat(formData.protein_g),
        fat_g: parseFloat(formData.fat_g),
        carb_g: parseFloat(formData.carb_g),
        calories_kcal: parseFloat(formData.calories_kcal),
        region: formData.region || null,
        vector_text: formData.vector_text || null,
      };

      const url = isEdit
        ? `http://localhost:8000/api/admin/foods/${fdc_id}`
        : 'http://localhost:8000/api/admin/foods';

      const method = isEdit ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          ...adminAuth.getAuthHeader(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        alert(isEdit ? 'Food item updated successfully!' : 'Food item created successfully!');
        navigate('/admin/foods');
      } else {
        const error = await response.json();
        alert(`Failed to save food item: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error saving food:', error);
      alert('Failed to save food item');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      const response = await fetch(
        `http://localhost:8000/api/admin/foods/${fdc_id}`,
        {
          method: 'DELETE',
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        alert('Food item deleted successfully!');
        navigate('/admin/foods');
      } else {
        alert('Failed to delete food item');
      }
    } catch (error) {
      console.error('Error deleting food:', error);
      alert('Failed to delete food item');
    } finally {
      setDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="p-6">
          <div className="text-center text-gray-500">Loading...</div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="p-6">
        <div className="mb-6">
          <button
            onClick={() => navigate('/admin/foods')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800 mb-4"
          >
            <ArrowLeft size={20} />
            Back to Food List
          </button>
          <h1 className="text-2xl font-bold text-gray-800">
            {isEdit ? 'Edit Food Item' : 'Add New Food Item'}
          </h1>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  FDC ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="fdc_id"
                  value={formData.fdc_id}
                  onChange={handleChange}
                  disabled={isEdit}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.fdc_id ? 'border-red-500' : 'border-gray-300'
                  } ${isEdit ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                  placeholder="e.g., FOOD_001"
                />
                {errors.fdc_id && (
                  <p className="text-red-500 text-sm mt-1">{errors.fdc_id}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.name ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="e.g., Grilled Chicken Breast"
                />
                {errors.name && (
                  <p className="text-red-500 text-sm mt-1">{errors.name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Diet Type <span className="text-red-500">*</span>
                </label>
                <select
                  name="diet_type"
                  value={formData.diet_type}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.diet_type ? 'border-red-500' : 'border-gray-300'
                  }`}
                >
                  <option value="veg">Vegetarian</option>
                  <option value="non-veg">Non-Vegetarian</option>
                </select>
                {errors.diet_type && (
                  <p className="text-red-500 text-sm mt-1">{errors.diet_type}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Meal Type <span className="text-red-500">*</span>
                </label>
                <select
                  name="meal_type"
                  value={formData.meal_type}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.meal_type ? 'border-red-500' : 'border-gray-300'
                  }`}
                >
                  <option value="breakfast">Breakfast</option>
                  <option value="lunch">Lunch</option>
                  <option value="dinner">Dinner</option>
                  <option value="snacks">Snacks</option>
                </select>
                {errors.meal_type && (
                  <p className="text-red-500 text-sm mt-1">{errors.meal_type}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Serving Size (100g)
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="serving_size_g"
                  value={formData.serving_size_g}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., 100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Protein (g) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="protein_g"
                  value={formData.protein_g}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.protein_g ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="e.g., 25.5"
                />
                {errors.protein_g && (
                  <p className="text-red-500 text-sm mt-1">{errors.protein_g}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fat (g) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="fat_g"
                  value={formData.fat_g}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.fat_g ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="e.g., 5.2"
                />
                {errors.fat_g && (
                  <p className="text-red-500 text-sm mt-1">{errors.fat_g}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Carbs (g) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="carb_g"
                  value={formData.carb_g}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.carb_g ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="e.g., 0"
                />
                {errors.carb_g && (
                  <p className="text-red-500 text-sm mt-1">{errors.carb_g}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Calories (kcal) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="calories_kcal"
                  value={formData.calories_kcal}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.calories_kcal ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="e.g., 165"
                />
                {errors.calories_kcal && (
                  <p className="text-red-500 text-sm mt-1">{errors.calories_kcal}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Region
                </label>
                <input
                  type="text"
                  name="region"
                  value={formData.region}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Indian, American, Italian"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Vector Text (for AI search)
                </label>
                <textarea
                  name="vector_text"
                  value={formData.vector_text}
                  onChange={handleChange}
                  rows="3"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Descriptive text for AI-based search..."
                />
              </div>
            </div>

            <div className="mt-6 flex justify-between items-center">
              <div>
                {isEdit && (
                  <button
                    type="button"
                    onClick={() => setShowDeleteModal(true)}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
                  >
                    <Trash2 size={20} />
                    Delete
                  </button>
                )}
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => navigate('/admin/foods')}
                  className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 flex items-center gap-2"
                >
                  <Save size={20} />
                  {saving ? 'Saving...' : isEdit ? 'Update' : 'Create'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Delete Food Item</h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete this food item? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  );
};

export default FoodForm;
