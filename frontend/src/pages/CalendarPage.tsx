import { useState, useCallback, useMemo, useEffect } from 'react';
import { Calendar, momentLocalizer, Views, type View } from 'react-big-calendar';
import moment from 'moment';
import {
  format,
  addMonths,
  subMonths,
  startOfMonth,
  endOfMonth,
  parseISO,
} from 'date-fns';
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Bike,
  Dumbbell,
  Coffee,
  Zap,
  Target,
  Download,
  Loader2,
} from 'lucide-react';
import { useFitnessStore } from '../store/fitnessStore';
import type { CalendarEvent, PlannedWorkout, Activity } from '../types';
import api, { endpoints } from '../utils/api';
import WorkoutExportModal from '../components/WorkoutExportModal';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const localizer = momentLocalizer(moment);

function getWorkoutColor(workoutType: string): string {
  switch (workoutType) {
    case 'endurance':
      return '#3b82f6'; // blue
    case 'tempo':
      return '#22c55e'; // green
    case 'sweetspot':
      return '#f97316'; // orange
    case 'threshold':
      return '#eab308'; // yellow
    case 'vo2max':
      return '#ef4444'; // red
    case 'recovery':
      return '#9ca3af'; // gray
    case 'sprint':
      return '#7c3aed'; // purple
    default:
      return '#fc4c02'; // strava orange
  }
}

function getWorkoutIcon(workoutType: string) {
  switch (workoutType) {
    case 'recovery':
      return <Coffee className="w-3 h-3" />;
    case 'endurance':
      return <Bike className="w-3 h-3" />;
    case 'strength':
      return <Dumbbell className="w-3 h-3" />;
    case 'vo2max':
    case 'sprint':
      return <Zap className="w-3 h-3" />;
    default:
      return <Target className="w-3 h-3" />;
  }
}

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [view, setView] = useState<View>(Views.MONTH);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [showExportModal, setShowExportModal] = useState(false);
  const [workouts, setWorkouts] = useState<PlannedWorkout[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { activities } = useFitnessStore();

  // Fetch workouts for the current month
  const fetchWorkouts = useCallback(async (date: Date) => {
    setIsLoading(true);
    setError(null);

    try {
      // Get start and end of the visible month range (with some buffer)
      const startDate = format(
        subMonths(startOfMonth(date), 1),
        'yyyy-MM-dd'
      );
      const endDate = format(
        addMonths(endOfMonth(date), 1),
        'yyyy-MM-dd'
      );

      const response = await api.get<PlannedWorkout[]>(endpoints.workouts.calendar, {
        params: { start_date: startDate, end_date: endDate },
      });

      setWorkouts(response.data);
    } catch (err) {
      console.error('Failed to fetch workouts:', err);
      setError('Failed to load workouts');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch workouts when month changes
  useEffect(() => {
    fetchWorkouts(currentDate);
  }, [currentDate, fetchWorkouts]);

  // Convert workouts and activities to calendar events
  const events: CalendarEvent[] = useMemo(() => {
    const workoutEvents: CalendarEvent[] = workouts.map((workout) => ({
      id: `workout-${workout.id}`,
      title: workout.name,
      start: parseISO(workout.date),
      end: parseISO(workout.date),
      allDay: true,
      resource: workout,
      type: 'workout' as const,
      status: workout.completed ? 'completed' : 'planned',
      color: getWorkoutColor(workout.workout_type),
    }));

    const activityEvents: CalendarEvent[] = (activities || []).map((activity) => ({
      id: `activity-${activity.id}`,
      title: activity.name,
      start: new Date(activity.date),
      end: new Date(activity.date),
      allDay: true,
      resource: activity,
      type: 'activity' as const,
      color: '#4ade80', // green for completed
    }));

    return [...workoutEvents, ...activityEvents];
  }, [workouts, activities]);

  // Custom event component
  const EventComponent = ({ event }: { event: CalendarEvent }) => {
    const isWorkout = event.type === 'workout';
    const workout = isWorkout ? (event.resource as PlannedWorkout) : null;

    return (
      <div
        className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium truncate"
        style={{ backgroundColor: event.color, color: 'white' }}
      >
        {isWorkout && workout && getWorkoutIcon(workout.workout_type)}
        <span className="truncate">{event.title}</span>
      </div>
    );
  };

  // Navigation handlers
  const handleNavigate = useCallback((action: 'PREV' | 'NEXT' | 'TODAY') => {
    if (action === 'PREV') {
      setCurrentDate((prev) => subMonths(prev, 1));
    } else if (action === 'NEXT') {
      setCurrentDate((prev) => addMonths(prev, 1));
    } else {
      setCurrentDate(new Date());
    }
  }, []);

  const handleSelectEvent = useCallback((event: CalendarEvent) => {
    setSelectedEvent(event);
  }, []);

  const handleCloseModal = () => {
    setSelectedEvent(null);
  };

  const handleOpenExport = () => {
    setShowExportModal(true);
  };

  const handleCloseExport = () => {
    setShowExportModal(false);
  };

  // Custom toolbar
  const CustomToolbar = () => (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-4">
        <h2 className="text-xl font-semibold text-white">
          {format(currentDate, 'MMMM yyyy')}
        </h2>
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleNavigate('PREV')}
            className="p-2 hover:bg-dark-700 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-gray-400" />
          </button>
          <button
            onClick={() => handleNavigate('TODAY')}
            className="px-3 py-1 text-sm text-gray-300 hover:bg-dark-700 rounded-lg transition-colors"
          >
            Today
          </button>
          <button
            onClick={() => handleNavigate('NEXT')}
            className="p-2 hover:bg-dark-700 rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        {isLoading && (
          <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex rounded-lg border border-dark-600 overflow-hidden">
          <button
            onClick={() => setView(Views.MONTH)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              view === Views.MONTH
                ? 'bg-strava-500 text-white'
                : 'bg-dark-700 text-gray-300 hover:bg-dark-600'
            }`}
          >
            Month
          </button>
          <button
            onClick={() => setView(Views.WEEK)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              view === Views.WEEK
                ? 'bg-strava-500 text-white'
                : 'bg-dark-700 text-gray-300 hover:bg-dark-600'
            }`}
          >
            Week
          </button>
        </div>

        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          <span>Add Workout</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Training Calendar</h1>
        <p className="text-gray-400 mt-1">
          Plan and track your workouts
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="card p-4 border-red-500/30 bg-red-500/10">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Legend */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-6">
          <span className="text-sm text-gray-400">Workout Types:</span>
          {[
            { type: 'endurance', label: 'Endurance' },
            { type: 'tempo', label: 'Tempo' },
            { type: 'sweetspot', label: 'Sweet Spot' },
            { type: 'threshold', label: 'Threshold' },
            { type: 'vo2max', label: 'VO2max' },
            { type: 'recovery', label: 'Recovery' },
          ].map(({ type, label }) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded"
                style={{ backgroundColor: getWorkoutColor(type) }}
              />
              <span className="text-sm text-gray-300">{label}</span>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-green-400" />
            <span className="text-sm text-gray-300">Completed</span>
          </div>
        </div>
      </div>

      {/* Calendar */}
      <div className="card p-6">
        <CustomToolbar />
        <div className="calendar-wrapper" style={{ height: 600 }}>
          <Calendar
            localizer={localizer}
            events={events}
            startAccessor="start"
            endAccessor="end"
            date={currentDate}
            onNavigate={(date) => setCurrentDate(date)}
            view={view}
            onView={(newView) => setView(newView)}
            onSelectEvent={handleSelectEvent}
            components={{
              event: EventComponent,
            }}
            toolbar={false}
            style={{ height: '100%' }}
          />
        </div>
      </div>

      {/* Event detail modal */}
      {selectedEvent && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={handleCloseModal}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="card p-6 max-w-lg w-full">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-semibold text-white">
                    {selectedEvent.title}
                  </h3>
                  <p className="text-sm text-gray-400 mt-1">
                    {format(selectedEvent.start, 'EEEE, MMMM d, yyyy')}
                  </p>
                </div>
                <button
                  onClick={handleCloseModal}
                  className="text-gray-400 hover:text-white"
                >
                  &times;
                </button>
              </div>

              {selectedEvent.type === 'workout' && selectedEvent.resource && (
                <div className="space-y-4">
                  <div
                    className="inline-block px-3 py-1 rounded-full text-sm font-medium"
                    style={{
                      backgroundColor: `${selectedEvent.color}20`,
                      color: selectedEvent.color,
                    }}
                  >
                    {(selectedEvent.resource as PlannedWorkout).workout_type}
                  </div>

                  {(selectedEvent.resource as PlannedWorkout).description && (
                    <p className="text-gray-300">
                      {(selectedEvent.resource as PlannedWorkout).description}
                    </p>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-dark-700">
                      <p className="text-sm text-gray-400">Duration</p>
                      <p className="text-lg font-semibold text-white">
                        {(selectedEvent.resource as PlannedWorkout).duration_minutes || 0}{' '}
                        min
                      </p>
                    </div>
                    <div className="p-3 rounded-lg bg-dark-700">
                      <p className="text-sm text-gray-400">Target TSS</p>
                      <p className="text-lg font-semibold text-white">
                        {(selectedEvent.resource as PlannedWorkout).target_tss || '--'}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 mt-6">
                    <button className="btn-primary flex-1">Start Workout</button>
                    <button
                      onClick={handleOpenExport}
                      className="btn-secondary flex-1 flex items-center justify-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      Export
                    </button>
                  </div>
                </div>
              )}

              {selectedEvent.type === 'activity' && selectedEvent.resource && (
                <div className="space-y-4">
                  <div className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-green-500/20 text-green-400">
                    Completed
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-dark-700">
                      <p className="text-sm text-gray-400">Distance</p>
                      <p className="text-lg font-semibold text-white">
                        {(
                          ((selectedEvent.resource as Activity).distance_meters || 0) / 1000
                        ).toFixed(1)}{' '}
                        km
                      </p>
                    </div>
                    <div className="p-3 rounded-lg bg-dark-700">
                      <p className="text-sm text-gray-400">Duration</p>
                      <p className="text-lg font-semibold text-white">
                        {Math.round(
                          (selectedEvent.resource as Activity).duration_seconds / 60
                        )}{' '}
                        min
                      </p>
                    </div>
                    {(selectedEvent.resource as Activity).average_power && (
                      <div className="p-3 rounded-lg bg-dark-700">
                        <p className="text-sm text-gray-400">Avg Power</p>
                        <p className="text-lg font-semibold text-white">
                          {(selectedEvent.resource as Activity).average_power}W
                        </p>
                      </div>
                    )}
                  </div>

                  <button className="btn-primary w-full mt-6">View Activity</button>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Export Modal */}
      {showExportModal && selectedEvent?.type === 'workout' && selectedEvent.resource && (
        <WorkoutExportModal
          workout={selectedEvent.resource as PlannedWorkout}
          onClose={handleCloseExport}
        />
      )}
    </div>
  );
}
