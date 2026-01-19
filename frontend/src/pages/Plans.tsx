import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Calendar,
  Clock,
  TrendingUp,
  CheckCircle2,
  PauseCircle,
  ChevronRight,
  Zap,
  Mountain,
  Heart,
  Award,
  Activity,
  Sparkles,
  Loader2,
  AlertCircle,
  Target,
  X,
} from 'lucide-react';
import { format, differenceInWeeks, addDays } from 'date-fns';
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
const DEFAULT_AVAILABILITY: Record<string, DayAvailability> = {
  Monday: { available: true, startTime: '06:00', duration: 60 },
  Tuesday: { available: true, startTime: '06:00', duration: 60 },
  Wednesday: { available: true, startTime: '06:00', duration: 60 },
  Thursday: { available: true, startTime: '06:00', duration: 60 },
  Friday: { available: true, startTime: '06:00', duration: 60 },
  Saturday: { available: true, startTime: '08:00', duration: 120 },
  Sunday: { available: true, startTime: '08:00', duration: 90 },
};

// Plan summary type from API
interface PlanSummary {
  id: number;
  name: string;
  philosophy: string;
  start_date: string;
  end_date: string;
  weekly_hours: number;
  goal_event: string | null;
  is_active: boolean;
  total_workouts: number;
  completed_workouts: number;
  compliance_rate: number;
}

// Goal templates
const goalTemplates = [
  {
    id: 'ftp-builder',
    name: 'FTP Builder',
    description: 'Increase your functional threshold power with structured intervals',
    duration: 8,
    hoursPerWeek: 8,
    icon: <Zap className="w-6 h-6" />,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
    programType: 'goal' as const,
  },
  {
    id: 'endurance',
    name: 'Base Endurance',
    description: 'Build aerobic foundation and improve efficiency',
    duration: 12,
    hoursPerWeek: 10,
    icon: <Heart className="w-6 h-6" />,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    programType: 'goal' as const,
  },
  {
    id: 'race-prep',
    name: 'Race Preparation',
    description: 'Peak for your target event with race-specific training',
    duration: 6,
    hoursPerWeek: 12,
    icon: <Award className="w-6 h-6" />,
    color: 'text-strava-500',
    bgColor: 'bg-strava-500/10',
    programType: 'race' as const,
  },
  {
    id: 'climbing',
    name: 'Climbing Focus',
    description: 'Improve power-to-weight for the mountains',
    duration: 8,
    hoursPerWeek: 10,
    icon: <Mountain className="w-6 h-6" />,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    programType: 'event' as const,
  },
];

export default function Plans() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [isLoadingPlans, setIsLoadingPlans] = useState(true);
  const [showNewPlanModal, setShowNewPlanModal] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<typeof goalTemplates[0] | null>(null);

  // AI Generation state
  const [context, setContext] = useState<AthleteContext | null>(null);
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<GeneratedPlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Plan configuration
  const [config, setConfig] = useState<ForecastConfig>({
    programType: 'goal',
    targetDate: format(addDays(new Date(), 56), 'yyyy-MM-dd'),
    maxWeeklyHours: 8,
    eventReadiness: 3,
    periodizationLevel: 50,
    polarizationRatio: '80/20',
    recoveryDemands: 50,
    availableDays: DEFAULT_AVAILABILITY,
  });
  const [planName, setPlanName] = useState('');

  // Fetch existing plans
  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const response = await apiGet<PlanSummary[]>(endpoints.plans.list);
        setPlans(response.data);
      } catch (err) {
        console.error('Failed to fetch plans:', err);
      } finally {
        setIsLoadingPlans(false);
      }
    };
    fetchPlans();
  }, []);

  // Fetch athlete context when modal opens
  const fetchContext = useCallback(async () => {
    setIsLoadingContext(true);
    setError(null);
    try {
      const response = await apiGet<AthleteContext>(endpoints.ai.context);
      setContext(response.data);
    } catch (err) {
      console.error('Failed to fetch context:', err);
      setError('Failed to load your fitness data. Please try again.');
    } finally {
      setIsLoadingContext(false);
    }
  }, []);

  useEffect(() => {
    if (showNewPlanModal) {
      fetchContext();
    }
  }, [showNewPlanModal, fetchContext]);

  // Apply goal template
  const applyGoalTemplate = (template: typeof goalTemplates[0]) => {
    setSelectedGoal(template);
    setConfig(prev => ({
      ...prev,
      programType: template.programType,
      targetDate: format(addDays(new Date(), template.duration * 7), 'yyyy-MM-dd'),
      maxWeeklyHours: template.hoursPerWeek,
    }));
    setPlanName(template.name);
  };

  // Generate plan
  const handleGeneratePlan = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      // Transform config for API (convert camelCase to snake_case)
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

      const response = await apiPost<GeneratedPlanResponse>(
        `${endpoints.ai.generatePlan}?plan_name=${encodeURIComponent(planName || 'AI Generated Plan')}`,
        apiConfig
      );
      setGeneratedPlan(response.data);
    } catch (err: unknown) {
      console.error('Failed to generate plan:', err);
      // Extract detailed error message from API response
      let errorMessage = 'Failed to generate plan';
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

  // Close modal and navigate to calendar
  const handlePlanCreated = () => {
    setShowNewPlanModal(false);
    setGeneratedPlan(null);
    setSelectedGoal(null);
    // Refresh plans list
    apiGet<PlanSummary[]>(endpoints.plans.list).then(res => setPlans(res.data));
    // Navigate to calendar to see the new workouts
    navigate('/calendar');
  };

  const activePlan = plans.find(p => p.is_active);
  const otherPlans = plans.filter(p => !p.is_active);

  const getProgress = (plan: PlanSummary) => {
    return plan.total_workouts > 0
      ? Math.round((plan.completed_workouts / plan.total_workouts) * 100)
      : 0;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Training Plans</h1>
          <p className="text-gray-400 mt-1">
            Set your goals and generate AI-powered training plans
          </p>
        </div>
        <button
          onClick={() => setShowNewPlanModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          <span>Create AI Plan</span>
        </button>
      </div>

      {/* Loading state */}
      {isLoadingPlans ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      ) : (
        <>
          {/* Active Plan */}
          {activePlan && (
            <div className="card overflow-hidden">
              <div className="p-6 border-b border-dark-700 bg-gradient-to-r from-strava-500/10 to-transparent">
                <div className="flex items-center gap-2 text-strava-500 text-sm font-medium mb-2">
                  <Activity className="w-4 h-4" />
                  <span>Active Plan</span>
                </div>
                <h2 className="text-xl font-bold text-white">{activePlan.name}</h2>
              </div>

              <div className="p-6">
                <div className="grid md:grid-cols-4 gap-6 mb-6">
                  <div>
                    <p className="text-sm text-gray-400">Philosophy</p>
                    <p className="text-white font-medium mt-1 capitalize">
                      {activePlan.philosophy.replace('_', ' ')}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Duration</p>
                    <p className="text-white font-medium mt-1">
                      {differenceInWeeks(new Date(activePlan.end_date), new Date(activePlan.start_date))} weeks
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Weekly Hours</p>
                    <p className="text-white font-medium mt-1">{activePlan.weekly_hours}h</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Compliance</p>
                    <p className="text-white font-medium mt-1">
                      {Math.round(activePlan.compliance_rate * 100)}%
                    </p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-400">Progress</span>
                    <span className="text-sm text-white font-medium">
                      {activePlan.completed_workouts}/{activePlan.total_workouts} workouts
                    </span>
                  </div>
                  <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-strava-500 rounded-full transition-all"
                      style={{ width: `${getProgress(activePlan)}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                    <span>{format(new Date(activePlan.start_date), 'MMM d')}</span>
                    <span>{format(new Date(activePlan.end_date), 'MMM d, yyyy')}</span>
                  </div>
                </div>

                <div className="flex gap-3">
                  <Link to="/calendar" className="btn-primary flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    <span>View Schedule</span>
                  </Link>
                  <Link to={`/plans/${activePlan.id}`} className="btn-secondary flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    <span>View Progress</span>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* No active plan - prompt to create */}
          {!activePlan && plans.length === 0 && (
            <div className="card p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-strava-500/10 flex items-center justify-center mx-auto mb-4">
                <Target className="w-8 h-8 text-strava-500" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Set Your Training Goal</h3>
              <p className="text-gray-400 mb-6 max-w-md mx-auto">
                Create an AI-powered training plan tailored to your fitness level and goals.
                The plan will use your Strava data to optimize workouts for maximum improvement.
              </p>
              <button
                onClick={() => setShowNewPlanModal(true)}
                className="btn-primary inline-flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                <span>Create Your First Plan</span>
              </button>
            </div>
          )}

          {/* Other Plans */}
          {otherPlans.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Previous Plans</h3>
              <div className="grid md:grid-cols-2 gap-4">
                {otherPlans.map((plan) => (
                  <Link
                    key={plan.id}
                    to={`/plans/${plan.id}`}
                    className="card-hover p-6"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        {plan.compliance_rate >= 0.8 ? (
                          <CheckCircle2 className="w-5 h-5 text-green-400" />
                        ) : (
                          <PauseCircle className="w-5 h-5 text-yellow-400" />
                        )}
                        <div>
                          <h4 className="font-semibold text-white">{plan.name}</h4>
                          <p className="text-sm text-gray-400 capitalize">
                            {plan.philosophy.replace('_', ' ')}
                          </p>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>

                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-gray-400">
                        {format(new Date(plan.start_date), 'MMM d')} -{' '}
                        {format(new Date(plan.end_date), 'MMM d, yyyy')}
                      </span>
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-500/10 text-gray-400">
                        {Math.round(plan.compliance_rate * 100)}% complete
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Goal Templates */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Quick Start Templates</h3>
            <p className="text-gray-400 mb-4">
              Choose a goal and we'll create a personalized plan using your Strava data
            </p>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {goalTemplates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => {
                    applyGoalTemplate(template);
                    setShowNewPlanModal(true);
                  }}
                  className="card-hover p-6 text-left"
                >
                  <div className={`p-3 rounded-xl ${template.bgColor} w-fit mb-4`}>
                    <div className={template.color}>{template.icon}</div>
                  </div>
                  <h4 className="font-semibold text-white mb-1">{template.name}</h4>
                  <p className="text-sm text-gray-400 mb-4">{template.description}</p>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {template.duration} weeks
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {template.hoursPerWeek}h/week
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* AI Plan Generation Modal */}
      {showNewPlanModal && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => !isGenerating && setShowNewPlanModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-start justify-center p-4 overflow-y-auto">
            <div className="card p-6 max-w-4xl w-full my-8">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-strava-500" />
                    {generatedPlan ? 'Plan Generated!' : 'Create AI Training Plan'}
                  </h3>
                  <p className="text-gray-400 text-sm mt-1">
                    {generatedPlan
                      ? 'Your personalized training plan is ready'
                      : 'Set your goal and we\'ll create a personalized plan'
                    }
                  </p>
                </div>
                {!isGenerating && (
                  <button
                    onClick={() => {
                      setShowNewPlanModal(false);
                      setGeneratedPlan(null);
                    }}
                    className="p-2 text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
              </div>

              {error && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                  <p className="text-red-400">{error}</p>
                </div>
              )}

              {/* Generated Plan Preview */}
              {generatedPlan ? (
                <div className="space-y-6">
                  {/* Summary */}
                  <div className="grid md:grid-cols-4 gap-4">
                    <div className="card bg-dark-700 p-4">
                      <p className="text-xs text-gray-400 uppercase tracking-wider">Duration</p>
                      <p className="text-xl font-bold text-white mt-1">
                        {generatedPlan.summary?.totalWeeks ?? 0} weeks
                      </p>
                    </div>
                    <div className="card bg-dark-700 p-4">
                      <p className="text-xs text-gray-400 uppercase tracking-wider">Total Workouts</p>
                      <p className="text-xl font-bold text-white mt-1">
                        {generatedPlan.workouts.length}
                      </p>
                    </div>
                    <div className="card bg-dark-700 p-4">
                      <p className="text-xs text-gray-400 uppercase tracking-wider">Avg Weekly Hours</p>
                      <p className="text-xl font-bold text-white mt-1">
                        {generatedPlan.summary?.avgWeeklyHours?.toFixed(1) ?? '0'}h
                      </p>
                    </div>
                    <div className="card bg-dark-700 p-4">
                      <p className="text-xs text-gray-400 uppercase tracking-wider">Total XSS</p>
                      <p className="text-xl font-bold text-strava-500 mt-1">
                        {Math.round(generatedPlan.summary?.totalXss ?? 0)}
                      </p>
                    </div>
                  </div>

                  {/* Phases */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-300 mb-3">Training Phases</h4>
                    <div className="flex gap-2 flex-wrap">
                      {(generatedPlan.summary?.phases ?? []).map((phase, i) => (
                        <div key={i} className="px-3 py-1.5 bg-dark-700 rounded-lg text-sm">
                          <span className="text-white font-medium">{phase.name}</span>
                          <span className="text-gray-400 ml-2">({phase.weeks} weeks)</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Predicted fitness */}
                  <div className="card bg-dark-700 p-4">
                    <h4 className="text-sm font-medium text-gray-300 mb-3">Predicted Fitness at Target Date</h4>
                    <div className="grid md:grid-cols-3 gap-4">
                      <div>
                        <p className="text-xs text-gray-400">Threshold Power</p>
                        <p className="text-lg font-bold text-white">
                          {Math.round(generatedPlan.predictedFitness?.thresholdPower ?? 0)}W
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">Peak Power</p>
                        <p className="text-lg font-bold text-white">
                          {Math.round(generatedPlan.predictedFitness?.peakPower ?? 0)}W
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">HIE</p>
                        <p className="text-lg font-bold text-white">
                          {generatedPlan.predictedFitness?.highIntensityEnergy?.toFixed(1) ?? '0'} kJ
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Sample workouts */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-300 mb-3">
                      First Week Preview
                    </h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {generatedPlan.workouts.slice(0, 7).map((workout, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-dark-700 rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-dark-600 flex items-center justify-center text-xs text-gray-400">
                              {format(new Date(workout.date), 'EEE')}
                            </div>
                            <div>
                              <p className="text-white font-medium">{workout.name}</p>
                              <p className="text-xs text-gray-400 capitalize">{workout.workoutType.replace('_', ' ')}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-white">{workout.durationMinutes} min</p>
                            {workout.targetTss && (
                              <p className="text-xs text-gray-400">{workout.targetTss} TSS</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 pt-4 border-t border-dark-700">
                    <button
                      onClick={handlePlanCreated}
                      className="btn-primary flex-1 flex items-center justify-center gap-2"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      View in Calendar
                    </button>
                    <button
                      onClick={() => setGeneratedPlan(null)}
                      className="btn-secondary"
                    >
                      Adjust Settings
                    </button>
                  </div>
                </div>
              ) : (
                /* Configuration Form */
                <div className="grid md:grid-cols-2 gap-6">
                  {/* Left Column - Goal & Config */}
                  <div className="space-y-6">
                    {/* Plan Name */}
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Plan Name
                      </label>
                      <input
                        type="text"
                        value={planName}
                        onChange={(e) => setPlanName(e.target.value)}
                        placeholder="e.g., Summer FTP Builder"
                        className="input"
                      />
                    </div>

                    {/* Goal Templates */}
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Training Goal
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {goalTemplates.map((template) => (
                          <button
                            key={template.id}
                            onClick={() => applyGoalTemplate(template)}
                            className={`p-3 rounded-lg text-left transition-all ${
                              selectedGoal?.id === template.id
                                ? 'bg-strava-500/20 border border-strava-500'
                                : 'bg-dark-700 border border-transparent hover:border-dark-600'
                            }`}
                          >
                            <div className={`${template.color} mb-1`}>{template.icon}</div>
                            <p className="text-sm font-medium text-white">{template.name}</p>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Target Date */}
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Target Date
                      </label>
                      <input
                        type="date"
                        value={config.targetDate}
                        onChange={(e) => setConfig({ ...config, targetDate: e.target.value })}
                        min={format(addDays(new Date(), 14), 'yyyy-MM-dd')}
                        className="input"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {differenceInWeeks(new Date(config.targetDate), new Date())} weeks from now
                      </p>
                    </div>

                    {/* Weekly Hours */}
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Max Weekly Hours: {config.maxWeeklyHours}h
                      </label>
                      <input
                        type="range"
                        min={3}
                        max={20}
                        value={config.maxWeeklyHours}
                        onChange={(e) => setConfig({ ...config, maxWeeklyHours: parseInt(e.target.value) })}
                        className="w-full accent-strava-500"
                      />
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>3h</span>
                        <span>20h</span>
                      </div>
                    </div>

                    {/* Periodization */}
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Periodization: {config.periodizationLevel < 30 ? 'Base Focus' : config.periodizationLevel > 70 ? 'Peak Focus' : 'Balanced'}
                      </label>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={config.periodizationLevel}
                        onChange={(e) => setConfig({ ...config, periodizationLevel: parseInt(e.target.value) })}
                        className="w-full accent-strava-500"
                      />
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>More Base</span>
                        <span>More Intensity</span>
                      </div>
                    </div>
                  </div>

                  {/* Right Column - Current Fitness & Availability */}
                  <div className="space-y-6">
                    {/* Current Fitness Summary */}
                    <div className="card bg-dark-700 p-4">
                      <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                        <Activity className="w-4 h-4" />
                        Your Current Fitness
                      </h4>
                      {isLoadingContext ? (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                        </div>
                      ) : context?.signature ? (
                        <div className="space-y-3">
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <p className="text-xs text-gray-400">Threshold Power</p>
                              <p className="text-lg font-bold text-white">
                                {Math.round(context.signature.thresholdPower || 0)}W
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-400">Weekly XSS Avg</p>
                              <p className="text-lg font-bold text-strava-500">
                                {Math.round(context.weeklyXssAverage || 0)}
                              </p>
                            </div>
                          </div>
                          {context.status && STATUS_CONFIG[context.status] && (
                            <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${STATUS_CONFIG[context.status].bgColor}`}>
                              <div className={`w-2 h-2 rounded-full ${STATUS_CONFIG[context.status].color.replace('text-', 'bg-')}`} />
                              <span className={`text-sm font-medium ${STATUS_CONFIG[context.status].color}`}>
                                {STATUS_CONFIG[context.status].label}
                              </span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-400">
                          No fitness data yet. Sync your Strava activities to get personalized recommendations.
                        </p>
                      )}
                    </div>

                    {/* Training Days */}
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-3">
                        Available Training Days
                      </label>
                      <div className="space-y-2">
                        {DAYS.map((day) => (
                          <div key={day} className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              checked={config.availableDays[day]?.available ?? true}
                              onChange={(e) => setConfig({
                                ...config,
                                availableDays: {
                                  ...config.availableDays,
                                  [day]: {
                                    ...config.availableDays[day],
                                    available: e.target.checked,
                                  },
                                },
                              })}
                              className="w-4 h-4 rounded border-dark-600 bg-dark-700 text-strava-500 focus:ring-strava-500"
                            />
                            <span className="text-sm text-gray-300 w-24">{day}</span>
                            {config.availableDays[day]?.available && (
                              <input
                                type="number"
                                min={30}
                                max={300}
                                step={15}
                                value={config.availableDays[day]?.duration ?? 60}
                                onChange={(e) => setConfig({
                                  ...config,
                                  availableDays: {
                                    ...config.availableDays,
                                    [day]: {
                                      ...config.availableDays[day],
                                      duration: parseInt(e.target.value),
                                    },
                                  },
                                })}
                                className="input w-20 text-sm py-1"
                              />
                            )}
                            {config.availableDays[day]?.available && (
                              <span className="text-xs text-gray-500">min</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Generate Button */}
              {!generatedPlan && (
                <div className="mt-6 pt-6 border-t border-dark-700">
                  <button
                    onClick={handleGeneratePlan}
                    disabled={isGenerating || !planName}
                    className="btn-primary w-full flex items-center justify-center gap-2"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Generating your plan...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Generate Training Plan
                      </>
                    )}
                  </button>
                  <p className="text-xs text-gray-500 text-center mt-2">
                    Uses AI to create a personalized plan based on your fitness data
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
