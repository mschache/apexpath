import { useState, useCallback, useMemo } from 'react';
import { Calendar, momentLocalizer, Views, type View } from 'react-big-calendar';
import moment from 'moment';
import { format, addMonths, subMonths } from 'date-fns';
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Bike,
  Dumbbell,
  Coffee,
  Zap,
  Target,
} from 'lucide-react';
import { useFitnessStore } from '../store/fitnessStore';
import type { CalendarEvent, PlannedWorkout, Activity } from '../types';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const localizer = momentLocalizer(moment);

// Mock data for calendar
const mockWorkouts: PlannedWorkout[] = [
  {
    id: 1,
    plan_id: 1,
    name: 'Sweet Spot Intervals',
    description: '2x20 min at 88-93% FTP',
    workout_type: 'sweetspot',
    date: format(new Date(), 'yyyy-MM-dd'),
    duration_minutes: 90,
    target_tss: 75,
    completed: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    plan_id: 1,
    name: 'Endurance Ride',
    description: '2 hour Z2 ride',
    workout_type: 'endurance',
    date: format(new Date(new Date().setDate(new Date().getDate() + 1)), 'yyyy-MM-dd'),
    duration_minutes: 120,
    target_tss: 85,
    completed: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 3,
    plan_id: 1,
    name: 'VO2max Intervals',
    description: '5x4 min at 106-120% FTP',
    workout_type: 'vo2max',
    date: format(new Date(new Date().setDate(new Date().getDate() + 3)), 'yyyy-MM-dd'),
    duration_minutes: 80,
    target_tss: 95,
    completed: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 4,
    plan_id: 1,
    name: 'Recovery Spin',
    description: '45 min easy spin',
    workout_type: 'recovery',
    date: format(new Date(new Date().setDate(new Date().getDate() + 4)), 'yyyy-MM-dd'),
    duration_minutes: 45,
    target_tss: 25,
    completed: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 5,
    plan_id: 1,
    name: 'Threshold Intervals',
    description: '3x15 min at 95-105% FTP',
    workout_type: 'threshold',
    date: format(new Date(new Date().setDate(new Date().getDate() + 6)), 'yyyy-MM-dd'),
    duration_minutes: 90,
    target_tss: 88,
    completed: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockActivities: Activity[] = [
  {
    id: 101,
    strava_id: 101,
    user_id: 1,
    name: 'Morning Tempo Ride',
    activity_type: 'Ride',
    date: new Date(Date.now() - 86400000).toISOString(),
    distance_meters: 45200,
    duration_seconds: 5400,
    average_power: 185,
    tss: 72,
    created_at: new Date().toISOString(),
  },
  {
    id: 102,
    strava_id: 102,
    user_id: 1,
    name: 'Recovery Spin',
    activity_type: 'Ride',
    date: new Date(Date.now() - 172800000).toISOString(),
    distance_meters: 25000,
    duration_seconds: 3600,
    average_power: 120,
    tss: 35,
    created_at: new Date().toISOString(),
  },
];

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
  const { plannedWorkouts, activities } = useFitnessStore();

  // Convert workouts and activities to calendar events
  const events: CalendarEvent[] = useMemo(() => {
    const workoutEvents: CalendarEvent[] = mockWorkouts.map((workout) => ({
      id: `workout-${workout.id}`,
      title: workout.name,
      start: new Date(workout.date),
      end: new Date(workout.date),
      allDay: true,
      resource: workout,
      type: 'workout' as const,
      status: workout.completed ? 'completed' : 'planned',
      color: getWorkoutColor(workout.workout_type),
    }));

    const activityEvents: CalendarEvent[] = mockActivities.map((activity) => ({
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
  }, [plannedWorkouts, activities]);

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
                    <button className="btn-secondary flex-1">Edit</button>
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
    </div>
  );
}
