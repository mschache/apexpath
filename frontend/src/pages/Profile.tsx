import { useState, useEffect } from 'react';
import {
  User as UserIcon,
  Save,
  Weight,
  Heart,
  Activity,
  Zap,
  Bike,
  Timer,
  Gauge,
  CheckCircle,
  AlertCircle,
  Loader2,
  Info,
  RefreshCw,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { apiPatch, apiPost, endpoints } from '../utils/api';
import type { User, UserUpdate, ExperienceLevel, CyclingDiscipline } from '../types';

// Form validation errors type
interface FormErrors {
  ftp?: string;
  weight_kg?: string;
  age?: string;
  max_hr?: string;
  resting_hr?: string;
  default_weekly_hours?: string;
}

// Experience level options
const EXPERIENCE_LEVELS: { value: ExperienceLevel; label: string; description: string }[] = [
  { value: 'beginner', label: 'Beginner', description: 'New to structured training (< 1 year)' },
  { value: 'intermediate', label: 'Intermediate', description: '1-3 years of consistent training' },
  { value: 'advanced', label: 'Advanced', description: '3+ years, competitive racing' },
  { value: 'elite', label: 'Elite', description: 'Professional or semi-pro level' },
];

// Discipline options
const DISCIPLINES: { value: CyclingDiscipline; label: string }[] = [
  { value: 'road', label: 'Road' },
  { value: 'mtb', label: 'Mountain Bike' },
  { value: 'gravel', label: 'Gravel' },
  { value: 'track', label: 'Track' },
  { value: 'indoor', label: 'Indoor Only' },
];

export default function Profile() {
  const { user, updateUser } = useAuthStore();
  const [isSaving, setIsSaving] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [errors, setErrors] = useState<FormErrors>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Form state
  const [formData, setFormData] = useState<UserUpdate>({
    ftp: user?.ftp ?? undefined,
    name: user?.name ?? undefined,
    weight_kg: user?.weight_kg ?? undefined,
    age: user?.age ?? undefined,
    max_hr: user?.max_hr ?? undefined,
    resting_hr: user?.resting_hr ?? undefined,
    experience_level: user?.experience_level ?? undefined,
    primary_discipline: user?.primary_discipline ?? undefined,
    default_weekly_hours: user?.default_weekly_hours ?? undefined,
    has_power_meter: user?.has_power_meter ?? undefined,
    has_indoor_trainer: user?.has_indoor_trainer ?? undefined,
  });

  // Update form data when user changes
  useEffect(() => {
    if (user) {
      setFormData({
        ftp: user.ftp ?? undefined,
        name: user.name ?? undefined,
        weight_kg: user.weight_kg ?? undefined,
        age: user.age ?? undefined,
        max_hr: user.max_hr ?? undefined,
        resting_hr: user.resting_hr ?? undefined,
        experience_level: user.experience_level ?? undefined,
        primary_discipline: user.primary_discipline ?? undefined,
        default_weekly_hours: user.default_weekly_hours ?? undefined,
        has_power_meter: user.has_power_meter ?? undefined,
        has_indoor_trainer: user.has_indoor_trainer ?? undefined,
      });
      setHasChanges(false);
    }
  }, [user]);

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (formData.ftp !== undefined) {
      if (formData.ftp < 50 || formData.ftp > 500) {
        newErrors.ftp = 'FTP must be between 50 and 500 watts';
      }
    }

    if (formData.weight_kg !== undefined) {
      if (formData.weight_kg < 30 || formData.weight_kg > 200) {
        newErrors.weight_kg = 'Weight must be between 30 and 200 kg';
      }
    }

    if (formData.age !== undefined) {
      if (formData.age < 13 || formData.age > 99) {
        newErrors.age = 'Age must be between 13 and 99 years';
      }
    }

    if (formData.max_hr !== undefined) {
      if (formData.max_hr < 100 || formData.max_hr > 220) {
        newErrors.max_hr = 'Max HR must be between 100 and 220 bpm';
      }
    }

    if (formData.resting_hr !== undefined) {
      if (formData.resting_hr < 30 || formData.resting_hr > 100) {
        newErrors.resting_hr = 'Resting HR must be between 30 and 100 bpm';
      }
    }

    if (formData.default_weekly_hours !== undefined) {
      if (formData.default_weekly_hours < 3 || formData.default_weekly_hours > 30) {
        newErrors.default_weekly_hours = 'Weekly hours must be between 3 and 30';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle input change
  const handleInputChange = (field: keyof UserUpdate, value: string | number | boolean | undefined) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasChanges(true);
    // Clear error for this field
    setErrors((prev) => ({ ...prev, [field]: undefined }));
    setSaveError(null);
    setSaveSuccess(false);
  };

  // Handle number input
  const handleNumberChange = (field: keyof UserUpdate, value: string) => {
    const numValue = value === '' ? undefined : parseFloat(value);
    handleInputChange(field, numValue);
  };

  // Handle integer input
  const handleIntChange = (field: keyof UserUpdate, value: string) => {
    const intValue = value === '' ? undefined : parseInt(value, 10);
    handleInputChange(field, intValue);
  };

  // Sync from Strava
  const handleSyncFromStrava = async () => {
    setIsSyncing(true);
    setSyncError(null);
    setSyncSuccess(false);

    try {
      const response = await apiPost<User>(endpoints.strava.syncProfile);
      updateUser(response.data);
      setSyncSuccess(true);
      setHasChanges(false);
      setTimeout(() => setSyncSuccess(false), 3000);
    } catch (error: unknown) {
      console.error('Failed to sync from Strava:', error);
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      setSyncError(err.response?.data?.detail || err.message || 'Failed to sync from Strava');
    } finally {
      setIsSyncing(false);
    }
  };

  // Save profile
  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      // Filter out undefined values and only send changed fields
      const updates: UserUpdate = {};
      const fields: (keyof UserUpdate)[] = [
        'ftp', 'name', 'weight_kg', 'age', 'max_hr', 'resting_hr',
        'experience_level', 'primary_discipline', 'default_weekly_hours',
        'has_power_meter', 'has_indoor_trainer'
      ];

      for (const field of fields) {
        if (formData[field] !== undefined) {
          (updates as Record<string, unknown>)[field] = formData[field];
        }
      }

      const response = await apiPatch<User>(endpoints.auth.me, updates);

      // Update local state
      updateUser(response.data);

      setSaveSuccess(true);
      setHasChanges(false);

      // Clear success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error: unknown) {
      console.error('Failed to update profile:', error);
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      setSaveError(err.response?.data?.detail || err.message || 'Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-strava-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Profile</h1>
          <p className="text-gray-400 mt-1">Manage your athlete profile and training preferences</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSyncFromStrava}
            className="px-4 py-2 rounded-lg bg-dark-700 text-gray-300 hover:bg-dark-600 transition-colors flex items-center gap-2 disabled:opacity-50"
            disabled={isSyncing || isSaving}
          >
            {isSyncing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Sync from Strava
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded-lg bg-strava-500 text-white hover:bg-strava-600 transition-colors flex items-center gap-2 disabled:opacity-50"
            disabled={isSaving || isSyncing || !hasChanges}
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </div>
      </div>

      {/* Success/Error Messages */}
      {saveSuccess && (
        <div className="mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/30 flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-500" />
          <p className="text-green-400">Profile updated successfully!</p>
        </div>
      )}
      {syncSuccess && (
        <div className="mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/30 flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-500" />
          <p className="text-green-400">Profile synced from Strava!</p>
        </div>
      )}
      {saveError && (
        <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <p className="text-red-400">{saveError}</p>
        </div>
      )}
      {syncError && (
        <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <p className="text-red-400">{syncError}</p>
        </div>
      )}

      {/* Unsaved changes indicator */}
      {hasChanges && (
        <div className="mb-6 p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30 flex items-center gap-3">
          <Info className="w-5 h-5 text-yellow-500" />
          <p className="text-yellow-400">You have unsaved changes</p>
        </div>
      )}

      {/* Profile Header Card */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-6">
          {user.profile_image ? (
            <img
              src={user.profile_image}
              alt={user.name || 'Profile'}
              className="w-20 h-20 rounded-full border-2 border-dark-600"
            />
          ) : (
            <div className="w-20 h-20 rounded-full bg-dark-700 border-2 border-dark-600 flex items-center justify-center">
              <UserIcon className="w-10 h-10 text-gray-500" />
            </div>
          )}
          <div className="flex-1">
            <h2 className="text-xl font-bold text-white">{user.name || 'Unnamed Athlete'}</h2>
            <p className="text-gray-400">{user.email || 'No email'}</p>
            <div className="flex items-center gap-2 mt-2">
              <div className="px-3 py-1 rounded-full bg-strava-500/10 text-strava-500 text-sm flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                Connected via Strava
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Physical Attributes */}
      <div className="card p-6 mb-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Weight className="w-5 h-5 text-strava-500" />
          Physical Attributes
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Weight */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Weight
            </label>
            <div className="relative">
              <input
                type="number"
                value={formData.weight_kg ?? ''}
                onChange={(e) => handleNumberChange('weight_kg', e.target.value)}
                placeholder="75"
                className="input-field w-full pr-12"
                step="0.1"
                min="30"
                max="200"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">kg</span>
            </div>
            {errors.weight_kg && (
              <p className="text-red-400 text-sm mt-1">{errors.weight_kg}</p>
            )}
          </div>

          {/* Age */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Age
            </label>
            <div className="relative">
              <input
                type="number"
                value={formData.age ?? ''}
                onChange={(e) => handleIntChange('age', e.target.value)}
                placeholder="35"
                className="input-field w-full pr-14"
                min="13"
                max="99"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">years</span>
            </div>
            {errors.age && (
              <p className="text-red-400 text-sm mt-1">{errors.age}</p>
            )}
          </div>

          {/* Max HR */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Max Heart Rate
            </label>
            <div className="relative">
              <input
                type="number"
                value={formData.max_hr ?? ''}
                onChange={(e) => handleIntChange('max_hr', e.target.value)}
                placeholder="185"
                className="input-field w-full pr-14"
                min="100"
                max="220"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">bpm</span>
            </div>
            {errors.max_hr && (
              <p className="text-red-400 text-sm mt-1">{errors.max_hr}</p>
            )}
          </div>

          {/* Resting HR */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Resting Heart Rate
            </label>
            <div className="relative">
              <input
                type="number"
                value={formData.resting_hr ?? ''}
                onChange={(e) => handleIntChange('resting_hr', e.target.value)}
                placeholder="52"
                className="input-field w-full pr-14"
                min="30"
                max="100"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">bpm</span>
            </div>
            {errors.resting_hr && (
              <p className="text-red-400 text-sm mt-1">{errors.resting_hr}</p>
            )}
          </div>
        </div>
        <div className="mt-4 flex items-start gap-2 text-sm text-gray-500">
          <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p>Resting HR is used for more accurate HR zone calculation (Karvonen method).</p>
        </div>
      </div>

      {/* Training Profile */}
      <div className="card p-6 mb-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-strava-500" />
          Training Profile
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* FTP */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Functional Threshold Power (FTP)
              </div>
            </label>
            <div className="relative">
              <input
                type="number"
                value={formData.ftp ?? ''}
                onChange={(e) => handleIntChange('ftp', e.target.value)}
                placeholder="250"
                className="input-field w-full pr-12"
                min="50"
                max="500"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">W</span>
            </div>
            {errors.ftp && (
              <p className="text-red-400 text-sm mt-1">{errors.ftp}</p>
            )}
          </div>

          {/* Weekly Hours */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              <div className="flex items-center gap-2">
                <Timer className="w-4 h-4" />
                Typical Weekly Training Hours
              </div>
            </label>
            <div className="relative">
              <input
                type="number"
                value={formData.default_weekly_hours ?? ''}
                onChange={(e) => handleIntChange('default_weekly_hours', e.target.value)}
                placeholder="8"
                className="input-field w-full pr-20"
                min="3"
                max="30"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">hrs/week</span>
            </div>
            {errors.default_weekly_hours && (
              <p className="text-red-400 text-sm mt-1">{errors.default_weekly_hours}</p>
            )}
          </div>
        </div>

        {/* Experience Level */}
        <div className="mt-6">
          <label className="block text-sm font-medium text-gray-400 mb-3">
            Experience Level
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {EXPERIENCE_LEVELS.map((level) => (
              <button
                key={level.value}
                type="button"
                onClick={() => handleInputChange('experience_level', level.value)}
                className={`p-4 rounded-lg border-2 text-left transition-all cursor-pointer ${
                  formData.experience_level === level.value
                    ? 'border-strava-500 bg-strava-500/10'
                    : 'border-dark-600 bg-dark-800 hover:border-dark-500'
                }`}
              >
                <div className="font-medium text-white mb-1">{level.label}</div>
                <div className="text-xs text-gray-500">{level.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Primary Discipline */}
        <div className="mt-6">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            <div className="flex items-center gap-2">
              <Bike className="w-4 h-4" />
              Primary Discipline
            </div>
          </label>
          <select
            value={formData.primary_discipline ?? ''}
            onChange={(e) => handleInputChange('primary_discipline', e.target.value as CyclingDiscipline || undefined)}
            className="input-field w-full md:w-64"
          >
            <option value="">Select discipline</option>
            {DISCIPLINES.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Equipment */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Gauge className="w-5 h-5 text-strava-500" />
          Equipment
        </h3>

        <div className="space-y-4">
          {/* Power Meter */}
          <label className={`flex items-center gap-4 p-4 rounded-lg border-2 transition-all cursor-pointer ${
            formData.has_power_meter
              ? 'border-strava-500/50 bg-strava-500/5'
              : 'border-dark-600 bg-dark-800 hover:border-dark-500'
          }`}>
            <input
              type="checkbox"
              checked={formData.has_power_meter ?? false}
              onChange={(e) => handleInputChange('has_power_meter', e.target.checked)}
              className="w-5 h-5 rounded border-dark-600 bg-dark-700 text-strava-500 focus:ring-strava-500 focus:ring-offset-0 focus:ring-offset-dark-900"
            />
            <div className="flex-1">
              <div className="font-medium text-white">I have a power meter</div>
              <div className="text-sm text-gray-500">Training plans will include power-based workouts</div>
            </div>
            <Zap className={`w-5 h-5 ${formData.has_power_meter ? 'text-strava-500' : 'text-gray-600'}`} />
          </label>

          {/* Indoor Trainer */}
          <label className={`flex items-center gap-4 p-4 rounded-lg border-2 transition-all cursor-pointer ${
            formData.has_indoor_trainer
              ? 'border-strava-500/50 bg-strava-500/5'
              : 'border-dark-600 bg-dark-800 hover:border-dark-500'
          }`}>
            <input
              type="checkbox"
              checked={formData.has_indoor_trainer ?? false}
              onChange={(e) => handleInputChange('has_indoor_trainer', e.target.checked)}
              className="w-5 h-5 rounded border-dark-600 bg-dark-700 text-strava-500 focus:ring-strava-500 focus:ring-offset-0 focus:ring-offset-dark-900"
            />
            <div className="flex-1">
              <div className="font-medium text-white">I have an indoor trainer</div>
              <div className="text-sm text-gray-500">Indoor workouts will be included in training plans</div>
            </div>
            <Heart className={`w-5 h-5 ${formData.has_indoor_trainer ? 'text-strava-500' : 'text-gray-600'}`} />
          </label>
        </div>
      </div>
    </div>
  );
}
