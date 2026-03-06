import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { adminAuth } from '../../utils/adminAuth';
import { ArrowLeft, Save, Trash2, Image as ImageIcon } from 'lucide-react';

const ExerciseForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    category: 'Strength',
    primary_muscle: 'Chest',
    difficulty: 'Beginner',
    image_url: '',
  });

  const [errors, setErrors] = useState({});

  const categoryOptions = ['Strength', 'Cardio', 'Flexibility', 'Sports', 'Functional'];
  const muscleOptions = ['Chest', 'Back', 'Legs', 'Arms', 'Shoulders', 'Core', 'Full Body', 'Glutes', 'Calves'];
  const difficultyOptions = ['Beginner', 'Intermediate', 'Advanced'];

  useEffect(() => {
    if (isEdit) {
      fetchExercise();
    }
  }, [id]);

  const fetchExercise = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/admin/exercises/${id}`,
        {
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setFormData({
          name: data.name,
          category: data.category,
          primary_muscle: data.primary_muscle,
          difficulty: data.difficulty,
          image_url: data.image_url || '',
        });
      } else {
        alert('Failed to load exercise');
        navigate('/admin/exercises');
      }
    } catch (error) {
      console.error('Error fetching exercise:', error);
      alert('Failed to load exercise');
      navigate('/admin/exercises');
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

    if (!formData.name.trim()) newErrors.name = 'Exercise name is required';
    if (!formData.category) newErrors.category = 'Category is required';
    if (!formData.primary_muscle) newErrors.primary_muscle = 'Primary muscle is required';
    if (!formData.difficulty) newErrors.difficulty = 'Difficulty is required';
    
    // Validate image URL if provided
    if (formData.image_url && formData.image_url.trim()) {
      try {
        new URL(formData.image_url);
      } catch {
        newErrors.image_url = 'Please enter a valid URL';
      }
    }

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
        name: formData.name.trim(),
        category: formData.category,
        primary_muscle: formData.primary_muscle,
        difficulty: formData.difficulty,
        image_url: formData.image_url.trim() || null,
      };

      const url = isEdit
        ? `http://localhost:8000/api/admin/exercises/${id}`
        : 'http://localhost:8000/api/admin/exercises';

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
        alert(isEdit ? 'Exercise updated successfully!' : 'Exercise created successfully!');
        navigate('/admin/exercises');
      } else {
        const error = await response.json();
        alert(`Failed to save exercise: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error saving exercise:', error);
      alert('Failed to save exercise');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      const response = await fetch(
        `http://localhost:8000/api/admin/exercises/${id}`,
        {
          method: 'DELETE',
          headers: adminAuth.getAuthHeader(),
        }
      );

      if (response.ok) {
        alert('Exercise deleted successfully!');
        navigate('/admin/exercises');
      } else {
        alert('Failed to delete exercise');
      }
    } catch (error) {
      console.error('Error deleting exercise:', error);
      alert('Failed to delete exercise');
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
            onClick={() => navigate('/admin/exercises')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft size={20} />
            Back to Exercises
          </button>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900">
              {isEdit ? 'Edit Exercise' : 'Add New Exercise'}
            </h1>
            {isEdit && (
              <button
                onClick={() => setShowDeleteModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                <Trash2 size={20} />
                Delete
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Exercise Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.name ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="e.g., Bench Press, Squats, Running"
                />
                {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category *
                </label>
                <select
                  name="category"
                  value={formData.category}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.category ? 'border-red-500' : 'border-gray-300'
                  }`}
                >
                  {categoryOptions.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
                {errors.category && <p className="mt-1 text-sm text-red-600">{errors.category}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Primary Muscle *
                </label>
                <select
                  name="primary_muscle"
                  value={formData.primary_muscle}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.primary_muscle ? 'border-red-500' : 'border-gray-300'
                  }`}
                >
                  {muscleOptions.map((muscle) => (
                    <option key={muscle} value={muscle}>
                      {muscle}
                    </option>
                  ))}
                </select>
                {errors.primary_muscle && (
                  <p className="mt-1 text-sm text-red-600">{errors.primary_muscle}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Difficulty *
                </label>
                <select
                  name="difficulty"
                  value={formData.difficulty}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                    errors.difficulty ? 'border-red-500' : 'border-gray-300'
                  }`}
                >
                  {difficultyOptions.map((diff) => (
                    <option key={diff} value={diff}>
                      {diff}
                    </option>
                  ))}
                </select>
                {errors.difficulty && (
                  <p className="mt-1 text-sm text-red-600">{errors.difficulty}</p>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Image URL (Optional)
                </label>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <input
                      type="url"
                      name="image_url"
                      value={formData.image_url}
                      onChange={handleChange}
                      className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                        errors.image_url ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="https://example.com/exercise-image.jpg"
                    />
                    {errors.image_url && (
                      <p className="mt-1 text-sm text-red-600">{errors.image_url}</p>
                    )}
                    <p className="mt-1 text-sm text-gray-500">
                      Enter a URL to an image demonstrating the exercise
                    </p>
                  </div>
                  {formData.image_url && (
                    <div className="flex items-center">
                      <ImageIcon className="text-green-600" size={24} />
                    </div>
                  )}
                </div>
                {formData.image_url && !errors.image_url && (
                  <div className="mt-3">
                    <p className="text-sm font-medium text-gray-700 mb-2">Image Preview:</p>
                    <img
                      src={formData.image_url}
                      alt="Exercise preview"
                      className="max-w-md h-48 object-cover rounded-lg border border-gray-300"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        setErrors((prev) => ({
                          ...prev,
                          image_url: 'Failed to load image from URL',
                        }));
                      }}
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-4 pt-4 border-t">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <Save size={20} />
                {saving ? 'Saving...' : isEdit ? 'Update Exercise' : 'Create Exercise'}
              </button>
              <button
                type="button"
                onClick={() => navigate('/admin/exercises')}
                className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>

      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Confirm Delete</h2>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete this exercise? This action cannot be undone.
            </p>
            <div className="flex gap-4">
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  );
};

export default ExerciseForm;
