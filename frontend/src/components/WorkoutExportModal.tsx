import { useState } from 'react';
import { Download, X, Loader2, Check } from 'lucide-react';
import type { PlannedWorkout, CyclingPlatform } from '../types';
import { CYCLING_PLATFORMS } from '../types';
import { useAuthStore } from '../store/authStore';
import api, { endpoints } from '../utils/api';

interface WorkoutExportModalProps {
  workout: PlannedWorkout;
  onClose: () => void;
}

export default function WorkoutExportModal({
  workout,
  onClose,
}: WorkoutExportModalProps) {
  const [selectedPlatform, setSelectedPlatform] = useState<CyclingPlatform | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuthStore();

  const ftp = user?.ftp || 200;

  const handleExport = async () => {
    if (!selectedPlatform) return;

    setIsExporting(true);
    setError(null);
    setExportSuccess(false);

    try {
      // Get the export file from API
      const response = await api.get(
        endpoints.workouts.export(workout.id),
        {
          params: { format: selectedPlatform.format, ftp },
          responseType: 'blob',
        }
      );

      // Extract filename from Content-Disposition header or generate one
      const contentDisposition = response.headers['content-disposition'];
      let filename = `${workout.name.replace(/[^a-zA-Z0-9]/g, '_')}.${selectedPlatform.format}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Create blob URL and trigger download
      const blob = new Blob([response.data], { type: response.headers['content-type'] });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      setExportSuccess(true);

      // Auto-close after successful download
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      console.error('Export failed:', err);
      setError('Failed to export workout. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="card p-6 max-w-md w-full">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-xl font-semibold text-white">
                Export Workout
              </h3>
              <p className="text-sm text-gray-400 mt-1">
                {workout.name}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* FTP Notice */}
          <div className="mb-6 p-3 rounded-lg bg-dark-700 border border-dark-600">
            <p className="text-sm text-gray-300">
              Exporting with FTP: <span className="font-semibold text-white">{ftp}W</span>
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Update your FTP in Profile settings if needed.
            </p>
          </div>

          {/* Platform Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Select Platform
            </label>
            <div className="grid grid-cols-1 gap-2">
              {CYCLING_PLATFORMS.map((platform) => (
                <button
                  key={platform.id}
                  onClick={() => setSelectedPlatform(platform)}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-colors text-left ${
                    selectedPlatform?.id === platform.id
                      ? 'border-strava-500 bg-strava-500/10'
                      : 'border-dark-600 bg-dark-700 hover:border-dark-500'
                  }`}
                >
                  <span className="text-2xl">{platform.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{platform.name}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-dark-600 text-gray-400 uppercase">
                        .{platform.format}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">{platform.description}</p>
                  </div>
                  {selectedPlatform?.id === platform.id && (
                    <Check className="w-5 h-5 text-strava-500" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Success Message */}
          {exportSuccess && (
            <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/30">
              <p className="text-sm text-green-400 flex items-center gap-2">
                <Check className="w-4 h-4" />
                Workout exported successfully!
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="btn-secondary flex-1"
              disabled={isExporting}
            >
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={!selectedPlatform || isExporting}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {isExporting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Download
                </>
              )}
            </button>
          </div>

          {/* Format Info */}
          <div className="mt-4 pt-4 border-t border-dark-600">
            <p className="text-xs text-gray-500 text-center">
              {selectedPlatform ? (
                <>
                  {selectedPlatform.format === 'zwo' && 'ZWO files can be imported directly into Zwift.'}
                  {selectedPlatform.format === 'mrc' && 'MRC files work with Rouvy, MyWhoosh, and most training apps.'}
                  {selectedPlatform.format === 'erg' && 'ERG files use absolute watts, compatible with Wahoo and Garmin devices.'}
                </>
              ) : (
                'Select a platform to download your workout.'
              )}
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
