// Experience level for training plans
export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced' | 'elite';

// Primary cycling discipline
export type CyclingDiscipline = 'road' | 'mtb' | 'gravel' | 'track' | 'indoor';

// User types
export interface User {
  id: number;
  strava_id: number;
  name?: string;
  email?: string;
  ftp?: number;
  profile_image?: string;

  // Physical attributes
  weight_kg?: number;
  age?: number;
  max_hr?: number;
  resting_hr?: number;

  // Training profile
  experience_level?: ExperienceLevel;
  primary_discipline?: CyclingDiscipline;
  default_weekly_hours?: number;

  // Equipment
  has_power_meter?: boolean;
  has_indoor_trainer?: boolean;

  // Timestamps
  created_at?: string;
  updated_at?: string;
}

// User update payload (for PATCH /auth/me)
export interface UserUpdate {
  ftp?: number;
  name?: string;
  weight_kg?: number;
  age?: number;
  max_hr?: number;
  resting_hr?: number;
  experience_level?: ExperienceLevel;
  primary_discipline?: CyclingDiscipline;
  default_weekly_hours?: number;
  has_power_meter?: boolean;
  has_indoor_trainer?: boolean;
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

// --- AI Training Planner Types ---

// Fitness Signature (3-parameter model)
export interface FitnessSignature {
  id?: number;
  userId?: number;
  date?: string;
  thresholdPower: number;      // TP - watts
  highIntensityEnergy: number; // HIE - kJ
  peakPower: number;           // PP - watts
  weightKg?: number;
  source?: 'estimated' | 'breakthrough' | 'manual';
}

// 3D Training Load
export interface TrainingLoad3D {
  low: number;   // Low (aerobic) system
  high: number;  // High (anaerobic) system
  peak: number;  // Peak (neuromuscular) system
}

// XSS Breakdown
export interface XSSBreakdown {
  total: number;
  low: number;
  high: number;
  peak: number;
}

// Training Status
export type TrainingStatus = 'fresh' | 'tired' | 'very_tired' | 'very_fresh' | 'detraining';

// Day Availability for scheduling
export interface DayAvailability {
  available: boolean;
  startTime?: string;  // HH:MM format
  duration: number;    // minutes
}

// Athlete Context for AI
export interface AthleteContext {
  userId: number;
  ftp: number;
  signature: FitnessSignature;
  trainingLoad: TrainingLoad3D;
  recoveryLoad: TrainingLoad3D;
  form: TrainingLoad3D;
  status: TrainingStatus;
  weeklyXssAverage: number;
}

// Forecast Configuration
export interface ForecastConfig {
  programType: 'goal' | 'event' | 'race';
  targetDate: string;
  maxWeeklyHours: number;
  eventReadiness: number;      // 1-5
  periodizationLevel: number;  // 0-100 (0=early base, 100=race peak)
  polarizationRatio: string;   // e.g., "80/20"
  recoveryDemands: number;     // 0-100 (0=aggressive, 100=conservative)
  availableDays: Record<string, DayAvailability>;
}

// Default availability for all days
export const DEFAULT_AVAILABILITY: Record<string, DayAvailability> = {
  Monday: { available: true, duration: 60 },
  Tuesday: { available: true, duration: 60 },
  Wednesday: { available: true, duration: 60 },
  Thursday: { available: true, duration: 60 },
  Friday: { available: true, duration: 60 },
  Saturday: { available: true, duration: 90 },
  Sunday: { available: true, duration: 90 },
};

// Planned Workout Summary from AI
export interface AIPlannedWorkout {
  date: string;
  name: string;
  workoutType: WorkoutType | string;
  durationMinutes: number;
  targetTss?: number;
  targetXss?: XSSBreakdown;
}

// Plan Phase Info
export interface PlanPhaseInfo {
  name: string;
  weeks: number;
}

// Plan Summary
export interface PlanSummary {
  totalWeeks: number;
  totalXss: number;
  avgWeeklyHours: number;
  phases: PlanPhaseInfo[];
}

// Predicted Fitness at target date
export interface PredictedFitness {
  thresholdPower: number;
  highIntensityEnergy: number;
  peakPower: number;
  trainingLoad: TrainingLoad3D;
  form: TrainingLoad3D;
}

// Generated Plan Response
export interface GeneratedPlanResponse {
  planId: number;
  workouts: AIPlannedWorkout[];
  summary: PlanSummary;
  predictedFitness: PredictedFitness;
}

// Training Load Record
export interface TrainingLoadRecord {
  id: number;
  userId: number;
  date: string;
  tlLow: number;
  tlHigh: number;
  tlPeak: number;
  rlLow: number;
  rlHigh: number;
  rlPeak: number;
  formLow: number;
  formHigh: number;
  formPeak: number;
  xssTotal: number;
  xssLow: number;
  xssHigh: number;
  xssPeak: number;
  status: TrainingStatus;
}

// Training Load History Response
export interface TrainingLoadHistoryResponse {
  records: TrainingLoadRecord[];
  summary: {
    avgWeeklyXss?: number;
    peakTl?: TrainingLoad3D;
    currentForm?: TrainingLoad3D;
  };
}

// Adapt Plan Request
export interface AdaptPlanRequest {
  reason?: string;
  maintainTargetDate?: boolean;
}

// Adapt Plan Response
export interface AdaptPlanResponse {
  message: string;
  workoutsModified: number;
  workoutsAdded: number;
  workoutsRemoved: number;
}

// --- Workout Export Types ---

// Export format for workout files
export type ExportFormat = 'zwo' | 'mrc' | 'erg';

// Cycling platform for export
export interface CyclingPlatform {
  id: string;
  name: string;
  format: ExportFormat;
  icon: string;
  description: string;
}

// Available cycling platforms for workout export
export const CYCLING_PLATFORMS: CyclingPlatform[] = [
  {
    id: 'zwift',
    name: 'Zwift',
    format: 'zwo',
    icon: '🚴',
    description: 'Indoor cycling and running',
  },
  {
    id: 'rouvy',
    name: 'Rouvy',
    format: 'mrc',
    icon: '🏔️',
    description: 'Virtual cycling with real video',
  },
  {
    id: 'mywhoosh',
    name: 'MyWhoosh',
    format: 'mrc',
    icon: '🌍',
    description: 'Free indoor cycling platform',
  },
  {
    id: 'wahoo',
    name: 'Wahoo',
    format: 'erg',
    icon: '⚡',
    description: 'Wahoo SYSTM / KICKR',
  },
  {
    id: 'garmin',
    name: 'Garmin',
    format: 'erg',
    icon: '📊',
    description: 'Garmin Connect / Edge devices',
  },
];

// Export response metadata
export interface ExportMetadata {
  filename: string;
  format: ExportFormat;
  content_type: string;
  size_bytes: number;
}
