// User types
export interface User {
  id: number;
  strava_id: number;
  name?: string;
  email?: string;
  ftp?: number;
  profile_image?: string;
  // Optional additional fields
  max_hr?: number;
  weight_kg?: number;
  created_at?: string;
  updated_at?: string;
}

// Activity types
export type ActivityType = 'Ride' | 'VirtualRide' | 'Run' | 'Swim' | 'Walk' | 'Hike' | 'Other';

export interface Activity {
  id: number;
  strava_id: number;
  user_id: number;
  name: string;
  activity_type: ActivityType | string;
  date: string;
  duration_seconds: number;
  distance_meters?: number;
  average_power?: number;
  normalized_power?: number;
  average_hr?: number;
  max_hr?: number;
  tss?: number;
  elevation_gain?: number;
  average_speed?: number;
  max_speed?: number;
  calories?: number;
  created_at: string;
}

// Training Plan types
export type PlanGoal = 'endurance' | 'ftp_improvement' | 'weight_loss' | 'race_preparation' | 'general_fitness';
export type PlanStatus = 'active' | 'completed' | 'paused' | 'cancelled';
export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced' | 'elite';

export interface TrainingPlan {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  goal: PlanGoal;
  start_date: string;
  end_date: string;
  status: PlanStatus;
  difficulty_level: DifficultyLevel;
  weekly_hours_target?: number;
  tss_target_weekly?: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

// Planned Workout types
export type WorkoutType =
  | 'endurance'
  | 'tempo'
  | 'threshold'
  | 'vo2max'
  | 'sprint'
  | 'recovery'
  | 'race'
  | 'strength'
  | 'sweetspot'
  | 'intervals';

export type WorkoutStatus = 'planned' | 'completed' | 'skipped' | 'partial';

export interface WorkoutInterval {
  id: string;
  order: number;
  name: string;
  duration_seconds: number;
  target_power_low?: number;
  target_power_high?: number;
  target_power_percent_ftp_low?: number;
  target_power_percent_ftp_high?: number;
  target_hr_low?: number;
  target_hr_high?: number;
  target_cadence_low?: number;
  target_cadence_high?: number;
  zone?: number;
  notes?: string;
}

export interface PlannedWorkout {
  id: number;
  plan_id: number;
  name: string;
  description?: string;
  workout_type: WorkoutType;
  date: string;  // ISO datetime string
  duration_minutes: number;
  intervals_json?: Array<{
    name?: string;
    type?: string;
    duration: number;
    power_target?: number;
    power_low?: number;
    power_high?: number;
    cadence?: number;
    repeats?: number;
  }>;
  target_tss?: number;
  target_if?: number;
  completed: boolean;
  completed_activity_id?: number;
  created_at: string;
  updated_at: string;
}

// Fitness Metric types
export interface FitnessMetric {
  id: number;
  user_id: number;
  date: string;
  ctl: number; // Chronic Training Load (Fitness)
  atl: number; // Acute Training Load (Fatigue)
  tsb: number; // Training Stress Balance (Form)
  daily_tss?: number;
  rolling_7_day_tss?: number;
  rolling_28_day_tss?: number;
  rolling_42_day_tss?: number;
  ramp_rate?: number;
  created_at: string;
}

// Chart data types
export interface FitnessChartData {
  date: string;
  fitness: number;
  fatigue: number;
  form: number;
  tss?: number;
}

export interface PowerZoneData {
  zone: number;
  name: string;
  minPower: number;
  maxPower: number;
  color: string;
  timeInZone?: number;
  percentTime?: number;
}

// API response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Auth types
export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in?: number;
  refresh_token?: string;
}

export interface LoginResponse {
  user: User;
  tokens: AuthTokens;
}

// Calendar event type for react-big-calendar
export interface CalendarEvent {
  id: number | string;
  title: string;
  start: Date;
  end: Date;
  allDay?: boolean;
  resource?: PlannedWorkout | Activity;
  type: 'workout' | 'activity';
  status?: WorkoutStatus;
  color?: string;
}

// Dashboard stats
export interface DashboardStats {
  weeklyDistance: number;
  weeklyTime: number;
  weeklyTSS: number;
  weeklyActivities: number;
  currentFitness: number;
  currentFatigue: number;
  currentForm: number;
  formTrend: 'improving' | 'declining' | 'stable';
  ftpEstimate?: number;
  recentPRs: PersonalRecord[];
}

// Dashboard summary API response
export interface DashboardSummaryResponse {
  weekly: {
    distance_meters: number;
    duration_seconds: number;
    tss: number;
    activity_count: number;
  };
  fitness: {
    ctl: number;
    atl: number;
    tsb: number;
  };
  recent_activities: Array<{
    id: number;
    name: string;
    date: string;
    duration_seconds: number;
    distance_meters: number | null;
    tss: number | null;
    average_power: number | null;
    average_hr: number | null;
    activity_type: string;
  }>;
  ftp: number | null;
}

export interface PersonalRecord {
  id: number;
  type: 'power' | 'speed' | 'distance' | 'duration';
  duration?: string;
  value: number;
  unit: string;
  activity_id: number;
  activity_name: string;
  achieved_at: string;
}

// Notification types
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  read: boolean;
  created_at: string;
}

// Settings types
export interface UserSettings {
  notifications_enabled: boolean;
  email_notifications: boolean;
  auto_sync_activities: boolean;
  privacy_mode: boolean;
  units: 'metric' | 'imperial';
  timezone: string;
  week_starts_on: 'sunday' | 'monday';
  power_zones_model: 'coggan' | 'custom';
  hr_zones_model: 'max_hr' | 'lthr' | 'custom';
}

// Zone definitions
export const POWER_ZONES_COGGAN: PowerZoneData[] = [
  { zone: 1, name: 'Active Recovery', minPower: 0, maxPower: 55, color: '#9ca3af' },
  { zone: 2, name: 'Endurance', minPower: 56, maxPower: 75, color: '#3b82f6' },
  { zone: 3, name: 'Tempo', minPower: 76, maxPower: 90, color: '#22c55e' },
  { zone: 4, name: 'Threshold', minPower: 91, maxPower: 105, color: '#eab308' },
  { zone: 5, name: 'VO2Max', minPower: 106, maxPower: 120, color: '#f97316' },
  { zone: 6, name: 'Anaerobic', minPower: 121, maxPower: 150, color: '#ef4444' },
  { zone: 7, name: 'Neuromuscular', minPower: 151, maxPower: 999, color: '#7c3aed' },
];

// Utility type for form handling
export type FormErrors<T> = Partial<Record<keyof T, string>>;
