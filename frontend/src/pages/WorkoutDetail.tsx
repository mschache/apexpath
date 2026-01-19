import { useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Edit,
  Trash2,
  Calendar,
  Clock,
  Zap,
  Target,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { format } from 'date-fns';
import { useAuthStore } from '../store/authStore';
import type { PlannedWorkout } from '../types';

// Mock workout data with extended intervals for visualization
interface ExtendedInterval {
  name?: string;
  duration: number;
  power_low?: number;
  power_high?: number;
  zone?: number;
  notes?: string;
}

const mockIntervals: ExtendedInterval[] = [
  {
    name: 'Warm Up',
    duration: 600,
    power_low: 50,
    power_high: 65,
    zone: 2,
    notes: 'Gradually increase power',
  },
  {
    name: 'Sweet Spot 1',
    duration: 1200,
    power_low: 88,
    power_high: 93,
    zone: 4,
    notes: 'Maintain steady cadence 85-95 rpm',
  },
  {
    name: 'Recovery',
    duration: 300,
    power_low: 40,
    power_high: 55,
    zone: 1,
    notes: 'Easy spinning',
  },
  {
    name: 'Sweet Spot 2',
    duration: 1200,
    power_low: 88,
    power_high: 93,
    zone: 4,
    notes: 'Focus on form',
  },
  {
    name: 'Recovery',
    duration: 300,
    power_low: 40,
    power_high: 55,
    zone: 1,
  },
  {
    name: 'Sweet Spot 3',
    duration: 1200,
    power_low: 88,
    power_high: 93,
    zone: 4,
  },
  {
    name: 'Cool Down',
    duration: 600,
    power_low: 40,
    power_high: 55,
    zone: 1,
    notes: 'Gradually decrease effort',
  },
];

const mockWorkout: PlannedWorkout = {
  id: 1,
  plan_id: 1,
  name: 'Sweet Spot Intervals',
  description:
    'Build sustainable power at your sweet spot intensity. Focus on maintaining steady power throughout each interval with smooth pedaling technique.',
  workout_type: 'sweetspot',
  date: format(new Date(), 'yyyy-MM-dd'),
  duration_minutes: 90,
  target_tss: 75,
  target_if: 0.88,
  completed: false,
  intervals_json: mockIntervals,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

function getZoneColor(zone: number): string {
  const colors: Record<number, string> = {
    1: '#9ca3af',
    2: '#3b82f6',
    3: '#22c55e',
    4: '#eab308',
    5: '#f97316',
    6: '#ef4444',
    7: '#7c3aed',
  };
  return colors[zone] || '#fc4c02';
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (secs === 0) return `${minutes}:00`;
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

export default function WorkoutDetail() {
  const { id: _id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const workout = mockWorkout; // In real app, fetch by id using _id
  const ftp = user?.ftp || 250; // Default FTP for power calculations

  // Calculate chart data from intervals
  const intervals = (workout.intervals_json || []) as ExtendedInterval[];
  const chartData = useMemo(() => {
    if (!intervals.length) return [];

    let cumulativeTime = 0;
    return intervals.map((interval) => {
      const data = {
        name: interval.name || 'Interval',
        startTime: cumulativeTime,
        duration: interval.duration,
        lowPower: interval.power_low
          ? Math.round((interval.power_low / 100) * ftp)
          : 0,
        highPower: interval.power_high
          ? Math.round((interval.power_high / 100) * ftp)
          : 0,
        zone: interval.zone || 1,
        color: getZoneColor(interval.zone || 1),
      };
      cumulativeTime += interval.duration;
      return data;
    });
  }, [intervals, ftp]);

  const handleDelete = () => {
    // In real app, call API to delete
    setShowDeleteModal(false);
    navigate('/calendar');
  };

  const handleMarkComplete = (status: 'completed' | 'skipped') => {
    // In real app, call API to update status
    console.log('Mark as:', status);
  };

  if (!workout) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button and actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back</span>
        </button>

        <div className="flex items-center gap-2">
          <button className="btn-ghost flex items-center gap-2">
            <Edit className="w-4 h-4" />
            <span className="hidden sm:inline">Edit</span>
          </button>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="btn-ghost text-red-400 hover:text-red-300 flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">Delete</span>
          </button>
        </div>
      </div>

      {/* Workout header */}
      <div className="card p-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span
                className="px-3 py-1 rounded-full text-sm font-medium capitalize"
                style={{
                  backgroundColor: `${getZoneColor(4)}20`,
                  color: getZoneColor(4),
                }}
              >
                {workout.workout_type}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  workout.completed
                    ? 'bg-green-500/10 text-green-400'
                    : 'bg-blue-500/10 text-blue-400'
                }`}
              >
                {workout.completed ? 'completed' : 'planned'}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white">{workout.name}</h1>
            <p className="text-gray-400 mt-2 max-w-2xl">{workout.description}</p>
          </div>

          {!workout.completed && (
            <div className="flex gap-2">
              <button
                onClick={() => handleMarkComplete('completed')}
                className="btn-primary flex items-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Mark Complete</span>
              </button>
              <button
                onClick={() => handleMarkComplete('skipped')}
                className="btn-secondary flex items-center gap-2"
              >
                <XCircle className="w-4 h-4" />
                <span>Skip</span>
              </button>
            </div>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="p-4 rounded-lg bg-dark-700/50">
            <div className="flex items-center gap-2 text-gray-400 mb-1">
              <Calendar className="w-4 h-4" />
              <span className="text-sm">Scheduled</span>
            </div>
            <p className="text-white font-semibold">
              {format(new Date(workout.date), 'EEEE, MMM d')}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-dark-700/50">
            <div className="flex items-center gap-2 text-gray-400 mb-1">
              <Clock className="w-4 h-4" />
              <span className="text-sm">Duration</span>
            </div>
            <p className="text-white font-semibold">
              {workout.duration_minutes} min
            </p>
          </div>
          <div className="p-4 rounded-lg bg-dark-700/50">
            <div className="flex items-center gap-2 text-gray-400 mb-1">
              <Zap className="w-4 h-4" />
              <span className="text-sm">TSS</span>
            </div>
            <p className="text-white font-semibold">{workout.target_tss || '--'}</p>
          </div>
          <div className="p-4 rounded-lg bg-dark-700/50">
            <div className="flex items-center gap-2 text-gray-400 mb-1">
              <Target className="w-4 h-4" />
              <span className="text-sm">IF</span>
            </div>
            <p className="text-white font-semibold">
              {workout.target_if ? workout.target_if.toFixed(2) : '--'}
            </p>
          </div>
        </div>
      </div>

      {/* Workout visualization */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Workout Profile</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} barGap={0}>
              <XAxis
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                interval={0}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                domain={[0, 'auto']}
                label={{
                  value: 'Watts',
                  angle: -90,
                  position: 'insideLeft',
                  fill: '#94a3b8',
                }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                }}
                labelStyle={{ color: '#f1f5f9', fontWeight: 600 }}
                formatter={(value) => [`${value}W`, 'Power']}
              />
              <Bar
                dataKey="highPower"
                fill="#fc4c02"
                radius={[4, 4, 0, 0]}
                name="highPower"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Intervals list */}
      <div className="card">
        <div className="p-6 border-b border-dark-700">
          <h3 className="text-lg font-semibold text-white">Intervals</h3>
          <p className="text-sm text-gray-400 mt-1">
            {intervals.length} intervals
          </p>
        </div>
        <div className="divide-y divide-dark-700">
          {intervals.map((interval, index) => (
            <div
              key={index}
              className="p-4 hover:bg-dark-700/30 transition-colors"
            >
              <div className="flex items-start gap-4">
                {/* Order indicator */}
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 font-semibold"
                  style={{
                    backgroundColor: `${getZoneColor(interval.zone || 1)}20`,
                    color: getZoneColor(interval.zone || 1),
                  }}
                >
                  {index + 1}
                </div>

                {/* Interval details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold text-white">{interval.name || 'Interval'}</h4>
                    <span
                      className="px-2 py-0.5 rounded text-xs font-medium"
                      style={{
                        backgroundColor: `${getZoneColor(interval.zone || 1)}20`,
                        color: getZoneColor(interval.zone || 1),
                      }}
                    >
                      Z{interval.zone || 1}
                    </span>
                  </div>
                  {interval.notes && (
                    <p className="text-sm text-gray-400">{interval.notes}</p>
                  )}
                </div>

                {/* Duration and power */}
                <div className="text-right flex-shrink-0">
                  <p className="text-white font-medium">
                    {formatDuration(interval.duration)}
                  </p>
                  <p className="text-sm text-gray-400">
                    {interval.power_low && interval.power_high
                      ? `${interval.power_low}-${interval.power_high}% FTP`
                      : '--'}
                  </p>
                  {ftp && interval.power_low && (
                    <p className="text-xs text-gray-500">
                      {Math.round((interval.power_low / 100) * ftp)}-
                      {Math.round(((interval.power_high || 100) / 100) * ftp)}W
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Related workouts */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Similar Workouts</h3>
          <Link
            to="/workouts"
            className="text-sm text-strava-500 hover:text-strava-400 flex items-center gap-1"
          >
            View all
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        <p className="text-gray-400">
          More sweet spot workouts will appear here once you have activity data.
        </p>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteModal && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setShowDeleteModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="card p-6 max-w-md w-full">
              <h3 className="text-xl font-semibold text-white mb-2">
                Delete Workout?
              </h3>
              <p className="text-gray-400 mb-6">
                Are you sure you want to delete "{workout.name}"? This action cannot
                be undone.
              </p>
              <div className="flex gap-3">
                <button onClick={handleDelete} className="btn-primary flex-1 bg-red-500 hover:bg-red-600">
                  Delete
                </button>
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
