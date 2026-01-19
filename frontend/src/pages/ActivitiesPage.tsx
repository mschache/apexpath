import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Bike,
  Gauge,
  Zap,
  Heart,
  Clock,
  Mountain,
  Calendar,
  Filter,
  RefreshCw,
  Loader2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { format } from 'date-fns';
import { apiGet, apiPost, endpoints } from '../utils/api';
import type { Activity } from '../types';

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function formatDistance(meters: number): string {
  const km = meters / 1000;
  return `${km.toFixed(1)} km`;
}

function formatSpeed(mps: number): string {
  const kph = mps * 3.6;
  return `${kph.toFixed(1)} km/h`;
}

export default function ActivitiesPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [activityType, setActivityType] = useState<string>('all');
  const perPage = 20;

  const fetchActivities = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const params: Record<string, unknown> = {
        skip: (page - 1) * perPage,
        limit: perPage,
      };
      if (activityType !== 'all') {
        params.activity_type = activityType;
      }
      const response = await apiGet<Activity[]>(endpoints.activities.list, params);
      setActivities(response.data);
    } catch (err) {
      console.error('Failed to fetch activities:', err);
      setError('Failed to load activities');
    } finally {
      setIsLoading(false);
    }
  }, [page, activityType]);

  const syncActivities = async () => {
    try {
      setIsSyncing(true);
      setError(null);
      await apiPost(endpoints.activities.sync);
      await fetchActivities();
    } catch (err) {
      console.error('Failed to sync activities:', err);
      setError('Failed to sync with Strava');
    } finally {
      setIsSyncing(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Activities</h1>
          <p className="text-gray-400 mt-1">Your training history from Strava</p>
        </div>
        <div className="flex gap-3">
          {/* Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <select
              value={activityType}
              onChange={(e) => {
                setActivityType(e.target.value);
                setPage(1);
              }}
              className="pl-9 pr-4 py-2 bg-dark-800 border border-dark-700 rounded-lg text-white appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-strava-500"
            >
              <option value="all">All Types</option>
              <option value="Ride">Outdoor Ride</option>
              <option value="VirtualRide">Virtual Ride</option>
              <option value="Run">Run</option>
            </select>
          </div>
          <button
            onClick={syncActivities}
            disabled={isSyncing}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {isSyncing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            <span>{isSyncing ? 'Syncing...' : 'Sync Strava'}</span>
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 text-red-400">
          {error}
        </div>
      )}

      {/* Activities list */}
      <div className="card">
        {isLoading ? (
          <div className="p-12 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-strava-500" />
          </div>
        ) : activities.length === 0 ? (
          <div className="p-12 flex flex-col items-center justify-center text-gray-400">
            <Bike className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg">No activities found</p>
            <button
              onClick={syncActivities}
              disabled={isSyncing}
              className="mt-4 text-strava-500 hover:text-strava-400"
            >
              Sync from Strava
            </button>
          </div>
        ) : (
          <div className="divide-y divide-dark-700">
            {activities.map((activity) => (
              <Link
                key={activity.id}
                to={`/activities/${activity.id}`}
                className="block p-4 hover:bg-dark-700/50 transition-colors"
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div className="p-3 rounded-lg bg-strava-500/10 shrink-0">
                    {activity.activity_type === 'VirtualRide' ? (
                      <Gauge className="w-6 h-6 text-strava-500" />
                    ) : (
                      <Bike className="w-6 h-6 text-strava-500" />
                    )}
                  </div>

                  {/* Main content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="font-semibold text-white truncate">
                          {activity.name}
                        </h3>
                        <div className="flex items-center gap-2 mt-1 text-sm text-gray-400">
                          <Calendar className="w-4 h-4" />
                          <span>{format(new Date(activity.date), 'EEEE, MMM d, yyyy')}</span>
                          <span>•</span>
                          <span className="capitalize">{activity.activity_type}</span>
                        </div>
                      </div>
                      {activity.tss && (
                        <div className="text-right shrink-0">
                          <span className="text-lg font-semibold text-strava-500">
                            {Math.round(activity.tss)}
                          </span>
                          <span className="text-sm text-gray-400 ml-1">TSS</span>
                        </div>
                      )}
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4 mt-4">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-gray-500" />
                        <span className="text-sm text-gray-300">
                          {formatDuration(activity.duration_seconds)}
                        </span>
                      </div>
                      {activity.distance_meters && (
                        <div className="flex items-center gap-2">
                          <Bike className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-300">
                            {formatDistance(activity.distance_meters)}
                          </span>
                        </div>
                      )}
                      {activity.elevation_gain && (
                        <div className="flex items-center gap-2">
                          <Mountain className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-300">
                            {Math.round(activity.elevation_gain)}m
                          </span>
                        </div>
                      )}
                      {activity.average_power && (
                        <div className="flex items-center gap-2">
                          <Zap className="w-4 h-4 text-yellow-500" />
                          <span className="text-sm text-gray-300">
                            {Math.round(activity.average_power)}W avg
                          </span>
                        </div>
                      )}
                      {activity.average_hr && (
                        <div className="flex items-center gap-2">
                          <Heart className="w-4 h-4 text-red-500" />
                          <span className="text-sm text-gray-300">
                            {Math.round(activity.average_hr)} bpm
                          </span>
                        </div>
                      )}
                      {activity.average_speed && (
                        <div className="flex items-center gap-2">
                          <Gauge className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-300">
                            {formatSpeed(activity.average_speed)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {activities.length > 0 && (
          <div className="flex items-center justify-between p-4 border-t border-dark-700">
            <p className="text-sm text-gray-400">
              Showing {(page - 1) * perPage + 1} - {(page - 1) * perPage + activities.length}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg bg-dark-700 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-sm text-gray-400 px-2">
                Page {page}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={activities.length < perPage}
                className="p-2 rounded-lg bg-dark-700 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
