import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Activity,
  Clock,
  Zap,
  Target,
  ChevronRight,
  Calendar,
  Bike,
  Heart,
  Gauge,
  RefreshCw,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import {
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { useAuthStore } from '../store/authStore';
import { useFitnessStore } from '../store/fitnessStore';
import { apiGet, apiPost, endpoints } from '../utils/api';
import { format, formatDistanceToNow, subDays } from 'date-fns';
import type { Activity as ActivityType, FitnessMetric, PlannedWorkout, FitnessChartData, DashboardSummaryResponse } from '../types';

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

// Transform fitness metrics to chart data
function transformMetricsToChartData(metrics: FitnessMetric[]): FitnessChartData[] {
  return metrics.map((m) => ({
    date: m.date,
    fitness: Math.round(m.ctl),
    fatigue: Math.round(m.atl),
    form: Math.round(m.tsb),
    tss: m.daily_tss,
  })).reverse(); // Oldest first for chart
}

export default function Dashboard() {
  const { user } = useAuthStore();
  const {
    activities,
    metrics,
    plannedWorkouts,
    dashboardStats,
    setActivities,
    setMetrics,
    setPlannedWorkouts,
    setDashboardStats,
    isLoadingActivities,
    setLoadingActivities,
    isLoadingMetrics,
    setLoadingMetrics,
  } = useFitnessStore();

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch dashboard data from summary endpoint (single optimized request)
  const fetchDashboardData = useCallback(async () => {
    try {
      setLoadingActivities(true);
      setLoadingMetrics(true);
      setError(null);

      const response = await apiGet<DashboardSummaryResponse>(endpoints.dashboard.summary);
      const data = response.data;

      // Convert recent_activities to ActivityType format for display
      const recentActivities: ActivityType[] = data.recent_activities.map((a) => ({
        id: a.id,
        strava_id: 0,
        user_id: 0,
        name: a.name,
        activity_type: a.activity_type,
        date: a.date,
        duration_seconds: a.duration_seconds,
        distance_meters: a.distance_meters ?? undefined,
        tss: a.tss ?? undefined,
        average_power: a.average_power ?? undefined,
        average_hr: a.average_hr ?? undefined,
        created_at: a.date,
      }));
      setActivities(recentActivities);

      // Update dashboard stats from summary response
      setDashboardStats({
        weeklyDistance: data.weekly.distance_meters,
        weeklyTime: data.weekly.duration_seconds,
        weeklyTSS: data.weekly.tss,
        weeklyActivities: data.weekly.activity_count,
        currentFitness: Math.round(data.fitness.ctl),
        currentFatigue: Math.round(data.fitness.atl),
        currentForm: Math.round(data.fitness.tsb),
        formTrend: 'stable', // Trend calculation would need historical data
        ftpEstimate: data.ftp ?? user?.ftp,
        recentPRs: [],
      });

    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Failed to load dashboard');
    } finally {
      setLoadingActivities(false);
      setLoadingMetrics(false);
    }
  }, [setActivities, setLoadingActivities, setLoadingMetrics, setDashboardStats, user?.ftp]);

  // Fetch fitness metrics for chart (still needed separately for chart data)
  const fetchMetrics = useCallback(async () => {
    try {
      const response = await apiGet<FitnessMetric[]>(endpoints.fitness.history, {
        from_date: format(subDays(new Date(), 90), 'yyyy-MM-dd'),
        to_date: format(new Date(), 'yyyy-MM-dd'),
        limit: 90,
      });
      setMetrics(response.data);

      // Update trend from historical data if we have enough
      if (response.data.length > 7) {
        const latest = response.data[0];
        const previous = response.data[7];
        const trend = latest.tsb > previous.tsb ? 'improving' : latest.tsb < previous.tsb ? 'declining' : 'stable';

        // Use functional update to avoid dependency on dashboardStats
        setDashboardStats((prev) => prev ? { ...prev, formTrend: trend } : prev);
      }
    } catch (err) {
      console.error('Failed to fetch metrics for chart:', err);
      // Silent fail - chart data is secondary
    }
  }, [setMetrics, setDashboardStats]);

  // Fetch upcoming workouts
  const fetchWorkouts = useCallback(async () => {
    try {
      const response = await apiGet<PlannedWorkout[]>(endpoints.workouts.upcoming, { limit: 5 });
      setPlannedWorkouts(response.data);
    } catch (err) {
      console.error('Failed to fetch workouts:', err);
      // Silent fail - workouts might not exist yet
    }
  }, [setPlannedWorkouts]);

  // Sync activities from Strava
  const syncActivities = async () => {
    try {
      setIsSyncing(true);
      setSyncMessage(null);
      setError(null);

      const response = await apiPost<{ new_activities: number; updated_activities: number; total_synced: number }>(endpoints.activities.sync);

      setSyncMessage(`Synced ${response.data.total_synced} activities (${response.data.new_activities} new, ${response.data.updated_activities} updated)`);

      // Refresh dashboard data after sync
      await fetchDashboardData();
      await fetchMetrics(); // Refresh chart data
    } catch (err: unknown) {
      console.error('Failed to sync activities:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to sync with Strava';
      setError(errorMessage);
    } finally {
      setIsSyncing(false);
      // Clear success message after 5 seconds
      setTimeout(() => setSyncMessage(null), 5000);
    }
  };

  // Load data on mount
  useEffect(() => {
    fetchDashboardData();
    fetchMetrics(); // Separate call for chart data
    fetchWorkouts();
  }, [fetchDashboardData, fetchMetrics, fetchWorkouts]);

  // Get recent activities (top 3)
  const recentActivities = activities.slice(0, 3);

  // Get upcoming workouts (next 3) - API already filters by date and completed status
  const upcomingWorkouts = plannedWorkouts.slice(0, 3);

  // Transform metrics for chart
  const chartData = transformMetricsToChartData(metrics.slice(0, 60)); // Last 60 days

  const stats = dashboardStats || {
    weeklyDistance: 0,
    weeklyTime: 0,
    weeklyTSS: 0,
    weeklyActivities: 0,
    currentFitness: 0,
    currentFatigue: 0,
    currentForm: 0,
    formTrend: 'stable' as const,
    ftpEstimate: user?.ftp || 0,
    recentPRs: [],
  };

  const getFormIcon = () => {
    if (stats.formTrend === 'improving') {
      return <TrendingUp className="w-5 h-5 text-green-400" />;
    } else if (stats.formTrend === 'declining') {
      return <TrendingDown className="w-5 h-5 text-red-400" />;
    }
    return <Minus className="w-5 h-5 text-gray-400" />;
  };

  const getFormColor = () => {
    if (stats.currentForm > 5) return 'text-green-400';
    if (stats.currentForm < -5) return 'text-red-400';
    return 'text-yellow-400';
  };

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Welcome back, {user?.name?.split(' ')[0] || 'Athlete'}!
          </h1>
          <p className="text-gray-400 mt-1">
            Here's your training overview for this week
          </p>
        </div>
        <div className="flex gap-3">
          <Link to="/workouts/new" className="btn-secondary flex items-center gap-2">
            <Target className="w-4 h-4" />
            <span>New Workout</span>
          </Link>
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

      {/* Sync message or error */}
      {(syncMessage || error) && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${
          error ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'
        }`}>
          {error ? <AlertCircle className="w-5 h-5" /> : <Activity className="w-5 h-5" />}
          <span>{error || syncMessage}</span>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <Bike className="w-5 h-5 text-blue-400" />
            </div>
            <span className="text-sm text-gray-400">Weekly Distance</span>
          </div>
          <p className="stat-value">
            {isLoadingActivities ? '...' : formatDistance(stats.weeklyDistance)}
          </p>
          <p className="stat-label">{stats.weeklyActivities} activities</p>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-purple-500/10">
              <Clock className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-sm text-gray-400">Weekly Time</span>
          </div>
          <p className="stat-value">
            {isLoadingActivities ? '...' : formatDuration(stats.weeklyTime)}
          </p>
          <p className="stat-label">on the bike</p>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-strava-500/10">
              <Zap className="w-5 h-5 text-strava-500" />
            </div>
            <span className="text-sm text-gray-400">Weekly TSS</span>
          </div>
          <p className="stat-value">
            {isLoadingActivities ? '...' : stats.weeklyTSS}
          </p>
          <p className="stat-label">training stress</p>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-green-500/10">
              <Gauge className="w-5 h-5 text-green-400" />
            </div>
            <span className="text-sm text-gray-400">Est. FTP</span>
          </div>
          <p className="stat-value">{stats.ftpEstimate || user?.ftp || '--'}W</p>
          <p className="stat-label">functional threshold</p>
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Fitness chart - 2 cols */}
        <div className="lg:col-span-2 card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-white">Performance Chart</h3>
              <p className="text-sm text-gray-400">CTL, ATL, and TSB over time</p>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="text-gray-400">Fitness</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <span className="text-gray-400">Fatigue</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <span className="text-gray-400">Form</span>
              </div>
            </div>
          </div>

          <div className="h-64">
            {isLoadingMetrics ? (
              <div className="h-full flex items-center justify-center text-gray-400">
                <Loader2 className="w-8 h-8 animate-spin" />
              </div>
            ) : chartData.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-gray-400">
                <Activity className="w-12 h-12 mb-3 opacity-50" />
                <p>No fitness data yet</p>
                <p className="text-sm">Sync your activities to see your fitness trend</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorFitness" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    tickFormatter={(value) => format(new Date(value), 'MMM d')}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
                    }}
                    labelStyle={{ color: '#f1f5f9' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="fitness"
                    stroke="#3b82f6"
                    fill="url(#colorFitness)"
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="fatigue"
                    stroke="#f87171"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="form"
                    stroke="#4ade80"
                    strokeWidth={2}
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Current form - 1 col */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-6">Current Form</h3>

          <div className="space-y-6">
            {/* CTL */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400">Fitness (CTL)</span>
                <span className="text-white font-semibold">
                  {isLoadingMetrics ? '...' : stats.currentFitness}
                </span>
              </div>
              <div className="intensity-bar">
                <div
                  className="intensity-fill bg-blue-500"
                  style={{ width: `${Math.min(stats.currentFitness, 100)}%` }}
                />
              </div>
            </div>

            {/* ATL */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400">Fatigue (ATL)</span>
                <span className="text-white font-semibold">
                  {isLoadingMetrics ? '...' : stats.currentFatigue}
                </span>
              </div>
              <div className="intensity-bar">
                <div
                  className="intensity-fill bg-red-400"
                  style={{ width: `${Math.min(stats.currentFatigue, 100)}%` }}
                />
              </div>
            </div>

            {/* TSB */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400">Form (TSB)</span>
                <span className={`font-semibold ${getFormColor()}`}>
                  {isLoadingMetrics ? '...' : (
                    <>
                      {stats.currentForm > 0 ? '+' : ''}
                      {stats.currentForm}
                    </>
                  )}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {getFormIcon()}
                <span className="text-sm text-gray-400 capitalize">
                  {stats.formTrend}
                </span>
              </div>
            </div>

            {/* Form interpretation */}
            <div className="p-4 rounded-lg bg-dark-700/50">
              <p className="text-sm text-gray-300">
                {stats.currentForm > 15
                  ? "You're well-rested! Great time for a hard effort or race."
                  : stats.currentForm > 5
                  ? "Good form. You're fresh and ready to train."
                  : stats.currentForm > -5
                  ? 'Balanced form. Maintain current training load.'
                  : stats.currentForm > -15
                  ? 'Building fatigue. Consider recovery soon.'
                  : 'High fatigue! Rest recommended.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent activities */}
        <div className="card">
          <div className="flex items-center justify-between p-6 border-b border-dark-700">
            <h3 className="text-lg font-semibold text-white">Recent Activities</h3>
            <Link
              to="/activities"
              className="text-sm text-strava-500 hover:text-strava-400 flex items-center gap-1"
            >
              View all
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="divide-y divide-dark-700">
            {isLoadingActivities ? (
              <div className="p-8 flex items-center justify-center text-gray-400">
                <Loader2 className="w-6 h-6 animate-spin" />
              </div>
            ) : recentActivities.length === 0 ? (
              <div className="p-8 flex flex-col items-center justify-center text-gray-400">
                <Bike className="w-10 h-10 mb-3 opacity-50" />
                <p>No activities yet</p>
                <button
                  onClick={syncActivities}
                  disabled={isSyncing}
                  className="mt-3 text-sm text-strava-500 hover:text-strava-400"
                >
                  Sync from Strava
                </button>
              </div>
            ) : (
              recentActivities.map((activity) => (
                <Link
                  key={activity.id}
                  to={`/activities/${activity.id}`}
                  className="activity-item"
                >
                  <div className="p-2 rounded-lg bg-strava-500/10">
                    {activity.activity_type === 'VirtualRide' ? (
                      <Gauge className="w-5 h-5 text-strava-500" />
                    ) : (
                      <Bike className="w-5 h-5 text-strava-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate">{activity.name}</p>
                    <p className="text-sm text-gray-400">
                      {formatDistanceToNow(new Date(activity.date), {
                        addSuffix: true,
                      })}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-white font-medium">
                      {activity.distance_meters ? formatDistance(activity.distance_meters) : '--'}
                    </p>
                    <div className="flex items-center gap-3 text-sm text-gray-400">
                      {activity.average_power && (
                        <span className="flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          {Math.round(activity.average_power)}W
                        </span>
                      )}
                      {activity.average_hr && (
                        <span className="flex items-center gap-1">
                          <Heart className="w-3 h-3" />
                          {Math.round(activity.average_hr)}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Upcoming workouts */}
        <div className="card">
          <div className="flex items-center justify-between p-6 border-b border-dark-700">
            <h3 className="text-lg font-semibold text-white">Upcoming Workouts</h3>
            <Link
              to="/calendar"
              className="text-sm text-strava-500 hover:text-strava-400 flex items-center gap-1"
            >
              View calendar
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="divide-y divide-dark-700">
            {upcomingWorkouts.length === 0 ? (
              <div className="p-8 flex flex-col items-center justify-center text-gray-400">
                <Calendar className="w-10 h-10 mb-3 opacity-50" />
                <p>No upcoming workouts</p>
                <Link
                  to="/plans/new"
                  className="mt-3 text-sm text-strava-500 hover:text-strava-400"
                >
                  Create a training plan
                </Link>
              </div>
            ) : (
              upcomingWorkouts.map((workout) => (
                <Link
                  key={workout.id}
                  to={`/workouts/${workout.id}`}
                  className="activity-item"
                >
                  <div className="p-2 rounded-lg bg-strava-500/10">
                    <Calendar className="w-5 h-5 text-strava-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate">{workout.name}</p>
                    <p className="text-sm text-gray-400">
                      {format(new Date(workout.date), 'EEEE, MMM d')}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-white font-medium">
                      {formatDuration(workout.duration_minutes * 60)}
                    </p>
                    <p className="text-sm text-gray-400">TSS: {workout.target_tss || '--'}</p>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
