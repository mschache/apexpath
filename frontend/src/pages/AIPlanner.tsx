import { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  Calendar,
  Clock,
  TrendingUp,
  Activity,
  ChevronRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Settings,
  Play,
  RotateCcw,
} from 'lucide-react';
// Chart imports available for future use:
// import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { format, addDays, differenceInWeeks } from 'date-fns';
import { apiGet, apiPost, endpoints } from '../utils/api';
import type {
  AthleteContext,
  ForecastConfig,
  GeneratedPlanResponse,
  DayAvailability,
  TrainingStatus,
} from '../types';

// Status colors and labels
const STATUS_CONFIG: Record<TrainingStatus, { color: string; bgColor: string; label: string }> = {
  fresh: { color: 'text-green-400', bgColor: 'bg-green-500/10', label: 'Fresh' },
  tired: { color: 'text-yellow-400', bgColor: 'bg-yellow-500/10', label: 'Tired' },
  very_tired: { color: 'text-red-400', bgColor: 'bg-red-500/10', label: 'Very Tired' },
  very_fresh: { color: 'text-blue-400', bgColor: 'bg-blue-500/10', label: 'Very Fresh' },
  detraining: { color: 'text-gray-400', bgColor: 'bg-gray-500/10', label: 'Detraining' },
};

// Day names for availability
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

// Default availability
const defaultAvailability: Record<string, DayAvailability> = {
  Monday: { available: true, duration: 60 },
  Tuesday: { available: true, duration: 60 },
  Wednesday: { available: true, duration: 60 },
  Thursday: { available: true, duration: 60 },
  Friday: { available: true, duration: 60 },
  Saturday: { available: true, duration: 90 },
  Sunday: { available: true, duration: 90 },
};

export default function AIPlanner() {
  // State
  const [context, setContext] = useState<AthleteContext | null>(null);
  const [isLoadingContext, setIsLoadingContext] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<GeneratedPlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Configuration state
  const [config, setConfig] = useState<ForecastConfig>({
    programType: 'goal',
    targetDate: format(addDays(new Date(), 84), 'yyyy-MM-dd'), // 12 weeks
    maxWeeklyHours: 10,
    eventReadiness: 3,
    periodizationLevel: 50,
    polarizationRatio: '80/20',
    recoveryDemands: 50,
    availableDays: defaultAvailability,
  });

  // Fetch athlete context
  const fetchContext = useCallback(async () => {
    try {
      setIsLoadingContext(true);
      setError(null);
      const response = await apiGet<AthleteContext>(endpoints.ai.context);
      setContext(response.data);
    } catch (err) {
      console.error('Failed to fetch athlete context:', err);
      setError('Failed to load athlete profile. Please make sure you have synced your activities.');
    } finally {
      setIsLoadingContext(false);
    }
  }, []);

  // Generate plan
  const generatePlan = async () => {
    try {
      setIsGenerating(true);
      setError(null);
      setSuccess(null);

      // Transform config for API (convert camelCase to snake_case)
      // Convert nested availableDays to snake_case keys
      const availableDaysSnakeCase: Record<string, { available: boolean; start_time?: string; duration: number }> = {};
      for (const [day, dayConfig] of Object.entries(config.availableDays)) {
        availableDaysSnakeCase[day] = {
          available: dayConfig.available,
          start_time: dayConfig.startTime,
          duration: dayConfig.duration,
        };
      }

      const apiConfig = {
        program_type: config.programType,
        target_date: config.targetDate,
        max_weekly_hours: config.maxWeeklyHours,
        event_readiness: config.eventReadiness,
        periodization_level: config.periodizationLevel,
        polarization_ratio: config.polarizationRatio,
        recovery_demands: config.recoveryDemands,
        available_days: availableDaysSnakeCase,
      };

      const response = await apiPost<GeneratedPlanResponse>(endpoints.ai.generatePlan, apiConfig);
      setGeneratedPlan(response.data);
      setSuccess(`Successfully generated a ${response.data.summary.totalWeeks}-week training plan!`);
    } catch (err: unknown) {
      console.error('Failed to generate plan:', err);
      // Extract detailed error message from API response
      let errorMessage = 'Failed to generate training plan';
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string | { msg: string; loc: string[] }[]; message?: string } } };
        if (axiosErr.response?.data?.detail) {
          const detail = axiosErr.response.data.detail;
          if (typeof detail === 'string') {
            errorMessage = detail;
          } else if (Array.isArray(detail)) {
            // Pydantic validation errors
            errorMessage = detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
          }
        } else if (axiosErr.response?.data?.message) {
          errorMessage = axiosErr.response.data.message;
        }
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  };

  // Load context on mount
  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  // Calculate weeks to target
  const weeksToTarget = differenceInWeeks(new Date(config.targetDate), new Date());

  // Get workout type color
  const getWorkoutColor = (type: string) => {
    const colors: Record<string, string> = {
      endurance: 'bg-blue-500',
      tempo: 'bg-green-500',
      threshold: 'bg-yellow-500',
      sweetspot: 'bg-orange-500',
      vo2max: 'bg-red-500',
      recovery: 'bg-gray-500',
      sprint: 'bg-purple-500',
      intervals: 'bg-pink-500',
    };
    return colors[type.toLowerCase()] || 'bg-strava-500';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20">
              <Sparkles className="w-6 h-6 text-purple-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">AI Training Planner</h1>
          </div>
          <p className="text-gray-400 mt-2">
            Generate a personalized training plan using AI-powered periodization
          </p>
        </div>
        <button
          onClick={fetchContext}
          disabled={isLoadingContext}
          className="btn-secondary flex items-center gap-2"
        >
          <RotateCcw className={`w-4 h-4 ${isLoadingContext ? 'animate-spin' : ''}`} />
          Refresh Data
        </button>
      </div>

      {/* Error/Success messages */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 text-red-400 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-lg bg-green-500/10 text-green-400 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column - Athlete Context */}
        <div className="space-y-6">
          {/* Fitness Signature Card */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-strava-500" />
              Fitness Signature
            </h3>
            {isLoadingContext ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : context?.signature ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Threshold Power</p>
                    <p className="text-2xl font-bold text-white">
                      {Math.round(context.signature.thresholdPower || 0)}
                      <span className="text-sm text-gray-400 ml-1">W</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Peak Power</p>
                    <p className="text-2xl font-bold text-white">
                      {Math.round(context.signature.peakPower || 0)}
                      <span className="text-sm text-gray-400 ml-1">W</span>
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wider">High Intensity Energy</p>
                  <p className="text-xl font-bold text-white">
                    {(context.signature.highIntensityEnergy || 0).toFixed(1)}
                    <span className="text-sm text-gray-400 ml-1">kJ</span>
                  </p>
                </div>
                <div className="pt-3 border-t border-dark-700">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Weekly XSS Average</p>
                  <p className="text-lg font-semibold text-strava-500">
                    {Math.round(context.weeklyXssAverage || 0)} XSS
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-gray-400 text-sm">No fitness data available</p>
            )}
          </div>

          {/* Current Form Card */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              Current Form
            </h3>
            {isLoadingContext ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : context?.form && context?.status ? (
              <div className="space-y-4">
                {/* Status badge */}
                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${STATUS_CONFIG[context.status]?.bgColor || 'bg-gray-500/10'}`}>
                  <div className={`w-2 h-2 rounded-full ${(STATUS_CONFIG[context.status]?.color || 'text-gray-400').replace('text-', 'bg-')}`} />
                  <span className={`text-sm font-medium ${STATUS_CONFIG[context.status]?.color || 'text-gray-400'}`}>
                    {STATUS_CONFIG[context.status]?.label || 'Unknown'}
                  </span>
                </div>

                {/* 3D Training Load */}
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">Low System (Aerobic)</span>
                      <span className="text-white">{(context.form.low || 0).toFixed(1)}</span>
                    </div>
                    <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full transition-all"
                        style={{ width: `${Math.min(Math.max(((context.form.low || 0) + 20) / 40 * 100, 5), 100)}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">High System (Anaerobic)</span>
                      <span className="text-white">{(context.form.high || 0).toFixed(1)}</span>
                    </div>
                    <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-yellow-500 rounded-full transition-all"
                        style={{ width: `${Math.min(Math.max(((context.form.high || 0) + 20) / 40 * 100, 5), 100)}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">Peak System (Neuromuscular)</span>
                      <span className="text-white">{(context.form.peak || 0).toFixed(1)}</span>
                    </div>
                    <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full transition-all"
                        style={{ width: `${Math.min(Math.max(((context.form.peak || 0) + 20) / 40 * 100, 5), 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-400 text-sm">No form data available</p>
            )}
          </div>
        </div>

        {/* Middle Column - Configuration */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Settings className="w-5 h-5 text-gray-400" />
            Plan Configuration
          </h3>

          <div className="space-y-6">
            {/* Program Type */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Program Type
              </label>
              <div className="grid grid-cols-3 gap-2">
                {['goal', 'event', 'race'].map((type) => (
                  <button
                    key={type}
                    onClick={() => setConfig({ ...config, programType: type as 'goal' | 'event' | 'race' })}
                    className={`px-3 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                      config.programType === type
                        ? 'bg-strava-500 text-white'
                        : 'bg-dark-700 text-gray-400 hover:text-white'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {/* Target Date */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Target Date
                <span className="text-gray-500 ml-2">({weeksToTarget} weeks)</span>
              </label>
              <input
                type="date"
                value={config.targetDate}
                onChange={(e) => setConfig({ ...config, targetDate: e.target.value })}
                min={format(addDays(new Date(), 28), 'yyyy-MM-dd')}
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white focus:border-strava-500 focus:outline-none"
              />
            </div>

            {/* Max Weekly Hours */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Weekly Hours: <span className="text-white">{config.maxWeeklyHours}h</span>
              </label>
              <input
                type="range"
                min="3"
                max="25"
                step="0.5"
                value={config.maxWeeklyHours}
                onChange={(e) => setConfig({ ...config, maxWeeklyHours: parseFloat(e.target.value) })}
                className="w-full accent-strava-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>3h</span>
                <span>25h</span>
              </div>
            </div>

            {/* Event Readiness */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Target Readiness
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((level) => (
                  <button
                    key={level}
                    onClick={() => setConfig({ ...config, eventReadiness: level })}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                      config.eventReadiness === level
                        ? 'bg-strava-500 text-white'
                        : 'bg-dark-700 text-gray-400 hover:text-white'
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Maintenance</span>
                <span>Peak Form</span>
              </div>
            </div>

            {/* Periodization Level */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Periodization Phase: <span className="text-white">{config.periodizationLevel}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={config.periodizationLevel}
                onChange={(e) => setConfig({ ...config, periodizationLevel: parseInt(e.target.value) })}
                className="w-full accent-strava-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Early Base</span>
                <span>Race Peak</span>
              </div>
            </div>

            {/* Polarization */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Training Polarization
              </label>
              <div className="grid grid-cols-3 gap-2">
                {['75/25', '80/20', '90/10'].map((ratio) => (
                  <button
                    key={ratio}
                    onClick={() => setConfig({ ...config, polarizationRatio: ratio })}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      config.polarizationRatio === ratio
                        ? 'bg-strava-500 text-white'
                        : 'bg-dark-700 text-gray-400 hover:text-white'
                    }`}
                  >
                    {ratio}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">Easy / Hard intensity split</p>
            </div>

            {/* Recovery Demands */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Recovery Needs: <span className="text-white">{config.recoveryDemands}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={config.recoveryDemands}
                onChange={(e) => setConfig({ ...config, recoveryDemands: parseInt(e.target.value) })}
                className="w-full accent-strava-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Aggressive</span>
                <span>Conservative</span>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={generatePlan}
              disabled={isGenerating || isLoadingContext || !context}
              className="w-full btn-primary flex items-center justify-center gap-2 py-3 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating Plan...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Generate Training Plan
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column - Day Availability */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-400" />
            Weekly Availability
          </h3>

          <div className="space-y-3">
            {DAYS.map((day) => (
              <div key={day} className="flex items-center gap-3">
                <button
                  onClick={() => setConfig({
                    ...config,
                    availableDays: {
                      ...config.availableDays,
                      [day]: {
                        ...config.availableDays[day],
                        available: !config.availableDays[day]?.available,
                      },
                    },
                  })}
                  className={`w-24 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    config.availableDays[day]?.available
                      ? 'bg-strava-500/20 text-strava-500 border border-strava-500/30'
                      : 'bg-dark-700 text-gray-500'
                  }`}
                >
                  {day.slice(0, 3)}
                </button>
                {config.availableDays[day]?.available && (
                  <div className="flex-1 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <input
                      type="number"
                      min="15"
                      max="300"
                      step="15"
                      value={config.availableDays[day]?.duration || 60}
                      onChange={(e) => setConfig({
                        ...config,
                        availableDays: {
                          ...config.availableDays,
                          [day]: {
                            ...config.availableDays[day],
                            duration: parseInt(e.target.value) || 60,
                          },
                        },
                      })}
                      className="w-20 bg-dark-700 border border-dark-600 rounded px-2 py-1 text-white text-sm focus:border-strava-500 focus:outline-none"
                    />
                    <span className="text-xs text-gray-500">min</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Total weekly hours */}
          <div className="mt-6 pt-4 border-t border-dark-700">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Total available:</span>
              <span className="text-white font-medium">
                {Math.round(
                  Object.values(config.availableDays)
                    .filter((d) => d.available)
                    .reduce((sum, d) => sum + d.duration, 0) / 60 * 10
                ) / 10}h / week
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Generated Plan Preview */}
      {generatedPlan && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-400" />
              Generated Plan Preview
            </h3>
            <Link to={`/plans/${generatedPlan.planId}`} className="btn-secondary flex items-center gap-2">
              View Full Plan
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Plan Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="p-4 rounded-lg bg-dark-700/50">
              <p className="text-xs text-gray-400 uppercase tracking-wider">Duration</p>
              <p className="text-xl font-bold text-white">{generatedPlan.summary?.totalWeeks ?? 0} weeks</p>
            </div>
            <div className="p-4 rounded-lg bg-dark-700/50">
              <p className="text-xs text-gray-400 uppercase tracking-wider">Total XSS</p>
              <p className="text-xl font-bold text-strava-500">{Math.round(generatedPlan.summary?.totalXss ?? 0)}</p>
            </div>
            <div className="p-4 rounded-lg bg-dark-700/50">
              <p className="text-xs text-gray-400 uppercase tracking-wider">Avg Hours/Week</p>
              <p className="text-xl font-bold text-white">{generatedPlan.summary?.avgWeeklyHours?.toFixed(1) ?? '0'}h</p>
            </div>
            <div className="p-4 rounded-lg bg-dark-700/50">
              <p className="text-xs text-gray-400 uppercase tracking-wider">Predicted FTP</p>
              <p className="text-xl font-bold text-green-400">
                {Math.round(generatedPlan.predictedFitness?.thresholdPower ?? 0)}W
              </p>
            </div>
          </div>

          {/* Phases */}
          <div className="mb-6">
            <h4 className="text-sm font-medium text-gray-400 mb-3">Training Phases</h4>
            <div className="flex gap-2">
              {(generatedPlan.summary?.phases ?? []).map((phase, index) => (
                <div
                  key={index}
                  className="flex-1 p-3 rounded-lg bg-dark-700/50 text-center"
                  style={{ flex: phase.weeks }}
                >
                  <p className="text-white font-medium">{phase.name}</p>
                  <p className="text-xs text-gray-400">{phase.weeks} weeks</p>
                </div>
              ))}
            </div>
          </div>

          {/* Workout Preview */}
          <div>
            <h4 className="text-sm font-medium text-gray-400 mb-3">
              Upcoming Workouts ({generatedPlan.workouts.length} total)
            </h4>
            <div className="grid gap-2 max-h-80 overflow-y-auto">
              {generatedPlan.workouts.slice(0, 14).map((workout, index) => (
                <div key={index} className="flex items-center gap-3 p-3 rounded-lg bg-dark-700/30 hover:bg-dark-700/50 transition-colors">
                  <div className={`w-3 h-3 rounded-full ${getWorkoutColor(workout.workoutType)}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-medium truncate">{workout.name}</p>
                    <p className="text-xs text-gray-500">
                      {format(new Date(workout.date), 'EEE, MMM d')}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-white">{workout.durationMinutes}m</p>
                    {workout.targetXss && (
                      <p className="text-xs text-gray-500">{Math.round(workout.targetXss.total)} XSS</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
