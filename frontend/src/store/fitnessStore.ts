import { create } from 'zustand';
import type {
  Activity,
  FitnessMetric,
  TrainingPlan,
  PlannedWorkout,
  DashboardStats,
} from '../types';

interface FitnessState {
  // Data
  activities: Activity[];
  metrics: FitnessMetric[];
  currentPlan: TrainingPlan | null;
  plannedWorkouts: PlannedWorkout[];
  dashboardStats: DashboardStats | null;

  // Loading states
  isLoadingActivities: boolean;
  isLoadingMetrics: boolean;
  isLoadingPlan: boolean;
  isLoadingWorkouts: boolean;

  // Filters and pagination
  activitiesPage: number;
  activitiesPerPage: number;
  totalActivities: number;
  selectedActivityType: string | null;
  dateRange: { start: Date | null; end: Date | null };

  // Actions - Activities
  setActivities: (activities: Activity[]) => void;
  addActivity: (activity: Activity) => void;
  updateActivity: (id: number, updates: Partial<Activity>) => void;
  removeActivity: (id: number) => void;
  setLoadingActivities: (loading: boolean) => void;
  setActivitiesPage: (page: number) => void;
  setTotalActivities: (total: number) => void;
  setSelectedActivityType: (type: string | null) => void;
  setDateRange: (range: { start: Date | null; end: Date | null }) => void;

  // Actions - Metrics
  setMetrics: (metrics: FitnessMetric[]) => void;
  addMetric: (metric: FitnessMetric) => void;
  setLoadingMetrics: (loading: boolean) => void;

  // Actions - Training Plan
  setCurrentPlan: (plan: TrainingPlan | null) => void;
  updateCurrentPlan: (updates: Partial<TrainingPlan>) => void;
  setLoadingPlan: (loading: boolean) => void;

  // Actions - Planned Workouts
  setPlannedWorkouts: (workouts: PlannedWorkout[]) => void;
  addPlannedWorkout: (workout: PlannedWorkout) => void;
  updatePlannedWorkout: (id: number, updates: Partial<PlannedWorkout>) => void;
  removePlannedWorkout: (id: number) => void;
  setLoadingWorkouts: (loading: boolean) => void;

  // Actions - Dashboard
  setDashboardStats: (stats: DashboardStats | null) => void;

  // Actions - Reset
  resetState: () => void;
}

const initialState = {
  activities: [],
  metrics: [],
  currentPlan: null,
  plannedWorkouts: [],
  dashboardStats: null,
  isLoadingActivities: false,
  isLoadingMetrics: false,
  isLoadingPlan: false,
  isLoadingWorkouts: false,
  activitiesPage: 1,
  activitiesPerPage: 20,
  totalActivities: 0,
  selectedActivityType: null,
  dateRange: { start: null, end: null },
};

export const useFitnessStore = create<FitnessState>()((set) => ({
  ...initialState,

  // Activities
  setActivities: (activities) => set({ activities }),

  addActivity: (activity) =>
    set((state) => ({
      activities: [activity, ...state.activities],
      totalActivities: state.totalActivities + 1,
    })),

  updateActivity: (id, updates) =>
    set((state) => ({
      activities: state.activities.map((a) =>
        a.id === id ? { ...a, ...updates } : a
      ),
    })),

  removeActivity: (id) =>
    set((state) => ({
      activities: state.activities.filter((a) => a.id !== id),
      totalActivities: Math.max(0, state.totalActivities - 1),
    })),

  setLoadingActivities: (isLoadingActivities) => set({ isLoadingActivities }),

  setActivitiesPage: (activitiesPage) => set({ activitiesPage }),

  setTotalActivities: (totalActivities) => set({ totalActivities }),

  setSelectedActivityType: (selectedActivityType) =>
    set({ selectedActivityType, activitiesPage: 1 }),

  setDateRange: (dateRange) => set({ dateRange, activitiesPage: 1 }),

  // Metrics
  setMetrics: (metrics) => set({ metrics }),

  addMetric: (metric) =>
    set((state) => ({
      metrics: [...state.metrics, metric].sort(
        (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
      ),
    })),

  setLoadingMetrics: (isLoadingMetrics) => set({ isLoadingMetrics }),

  // Training Plan
  setCurrentPlan: (currentPlan) => set({ currentPlan }),

  updateCurrentPlan: (updates) =>
    set((state) => ({
      currentPlan: state.currentPlan
        ? { ...state.currentPlan, ...updates }
        : null,
    })),

  setLoadingPlan: (isLoadingPlan) => set({ isLoadingPlan }),

  // Planned Workouts
  setPlannedWorkouts: (plannedWorkouts) => set({ plannedWorkouts }),

  addPlannedWorkout: (workout) =>
    set((state) => ({
      plannedWorkouts: [...state.plannedWorkouts, workout].sort(
        (a, b) =>
          new Date(a.date).getTime() -
          new Date(b.date).getTime()
      ),
    })),

  updatePlannedWorkout: (id, updates) =>
    set((state) => ({
      plannedWorkouts: state.plannedWorkouts.map((w) =>
        w.id === id ? { ...w, ...updates } : w
      ),
    })),

  removePlannedWorkout: (id) =>
    set((state) => ({
      plannedWorkouts: state.plannedWorkouts.filter((w) => w.id !== id),
    })),

  setLoadingWorkouts: (isLoadingWorkouts) => set({ isLoadingWorkouts }),

  // Dashboard
  setDashboardStats: (dashboardStats) => set({ dashboardStats }),

  // Reset
  resetState: () => set(initialState),
}));

// Selector hooks
export const useActivities = () => useFitnessStore((state) => state.activities);
export const useMetrics = () => useFitnessStore((state) => state.metrics);
export const useCurrentPlan = () => useFitnessStore((state) => state.currentPlan);
export const usePlannedWorkouts = () =>
  useFitnessStore((state) => state.plannedWorkouts);
export const useDashboardStats = () =>
  useFitnessStore((state) => state.dashboardStats);

// Computed selectors
export const useUpcomingWorkouts = () =>
  useFitnessStore((state) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return state.plannedWorkouts
      .filter((w) => new Date(w.date) >= today && !w.completed)
      .slice(0, 5);
  });

export const useRecentActivities = (limit = 5) =>
  useFitnessStore((state) => state.activities.slice(0, limit));

export const useLatestMetrics = () =>
  useFitnessStore((state) => (state.metrics.length > 0 ? state.metrics[0] : null));

export const useWeekActivities = () =>
  useFitnessStore((state) => {
    const now = new Date();
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - now.getDay());
    weekStart.setHours(0, 0, 0, 0);

    return state.activities.filter(
      (a) => new Date(a.date) >= weekStart
    );
  });
