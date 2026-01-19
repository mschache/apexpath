import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  Calendar,
  Clock,
  TrendingUp,
  CheckCircle2,
  PlayCircle,
  PauseCircle,
  ChevronRight,
  Zap,
  Mountain,
  Heart,
  Award,
  Activity,
} from 'lucide-react';
import { format, differenceInDays, differenceInWeeks } from 'date-fns';
import type { TrainingPlan, PlanGoal, DifficultyLevel } from '../types';

// Mock data
const mockPlans: TrainingPlan[] = [
  {
    id: 1,
    user_id: 1,
    name: 'Spring FTP Builder',
    description: 'Progressive 8-week plan to increase FTP by 5-10%',
    goal: 'ftp_improvement',
    start_date: '2024-01-15',
    end_date: '2024-03-10',
    status: 'active',
    difficulty_level: 'intermediate',
    weekly_hours_target: 8,
    tss_target_weekly: 450,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    user_id: 1,
    name: 'Gran Fondo Preparation',
    description: 'Endurance-focused plan for your upcoming event',
    goal: 'race_preparation',
    start_date: '2024-04-01',
    end_date: '2024-06-15',
    status: 'paused',
    difficulty_level: 'advanced',
    weekly_hours_target: 12,
    tss_target_weekly: 600,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 3,
    user_id: 1,
    name: 'Winter Base Building',
    description: 'Foundation building with aerobic focus',
    goal: 'endurance',
    start_date: '2023-11-01',
    end_date: '2024-01-14',
    status: 'completed',
    difficulty_level: 'beginner',
    weekly_hours_target: 6,
    tss_target_weekly: 300,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const planTemplates = [
  {
    id: 'ftp-builder',
    name: 'FTP Builder',
    description: 'Increase your functional threshold power',
    duration: '8 weeks',
    hoursPerWeek: '6-10',
    icon: <Zap className="w-6 h-6" />,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
  },
  {
    id: 'base-endurance',
    name: 'Base Endurance',
    description: 'Build aerobic foundation and efficiency',
    duration: '12 weeks',
    hoursPerWeek: '8-12',
    icon: <Heart className="w-6 h-6" />,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
  },
  {
    id: 'race-prep',
    name: 'Race Preparation',
    description: 'Peak for your target event',
    duration: '6 weeks',
    hoursPerWeek: '10-15',
    icon: <Award className="w-6 h-6" />,
    color: 'text-strava-500',
    bgColor: 'bg-strava-500/10',
  },
  {
    id: 'climbing',
    name: 'Climbing Focus',
    description: 'Improve power-to-weight for the mountains',
    duration: '8 weeks',
    hoursPerWeek: '8-12',
    icon: <Mountain className="w-6 h-6" />,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
  },
];

function getGoalLabel(goal: PlanGoal): string {
  const labels: Record<PlanGoal, string> = {
    endurance: 'Endurance',
    ftp_improvement: 'FTP Improvement',
    weight_loss: 'Weight Loss',
    race_preparation: 'Race Prep',
    general_fitness: 'General Fitness',
  };
  return labels[goal];
}

function getDifficultyColor(level: DifficultyLevel): string {
  const colors: Record<DifficultyLevel, string> = {
    beginner: 'text-green-400 bg-green-500/10',
    intermediate: 'text-yellow-400 bg-yellow-500/10',
    advanced: 'text-orange-400 bg-orange-500/10',
    elite: 'text-red-400 bg-red-500/10',
  };
  return colors[level];
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'active':
      return <PlayCircle className="w-5 h-5 text-green-400" />;
    case 'paused':
      return <PauseCircle className="w-5 h-5 text-yellow-400" />;
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-blue-400" />;
    default:
      return <Clock className="w-5 h-5 text-gray-400" />;
  }
}

export default function Plans() {
  const [showNewPlanModal, setShowNewPlanModal] = useState(false);

  const activePlan = mockPlans.find((p) => p.status === 'active');
  const otherPlans = mockPlans.filter((p) => p.status !== 'active');

  const getProgress = (plan: TrainingPlan) => {
    const start = new Date(plan.start_date);
    const end = new Date(plan.end_date);
    const now = new Date();

    if (now < start) return 0;
    if (now > end) return 100;

    const totalDays = differenceInDays(end, start);
    const elapsedDays = differenceInDays(now, start);
    return Math.round((elapsedDays / totalDays) * 100);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Training Plans</h1>
          <p className="text-gray-400 mt-1">
            Create and manage your structured training
          </p>
        </div>
        <button
          onClick={() => setShowNewPlanModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          <span>New Plan</span>
        </button>
      </div>

      {/* Active Plan */}
      {activePlan && (
        <div className="card overflow-hidden">
          <div className="p-6 border-b border-dark-700 bg-gradient-to-r from-strava-500/10 to-transparent">
            <div className="flex items-center gap-2 text-strava-500 text-sm font-medium mb-2">
              <Activity className="w-4 h-4" />
              <span>Active Plan</span>
            </div>
            <h2 className="text-xl font-bold text-white">{activePlan.name}</h2>
            <p className="text-gray-400 mt-1">{activePlan.description}</p>
          </div>

          <div className="p-6">
            <div className="grid md:grid-cols-4 gap-6 mb-6">
              <div>
                <p className="text-sm text-gray-400">Goal</p>
                <p className="text-white font-medium mt-1">
                  {getGoalLabel(activePlan.goal)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-400">Duration</p>
                <p className="text-white font-medium mt-1">
                  {differenceInWeeks(
                    new Date(activePlan.end_date),
                    new Date(activePlan.start_date)
                  )}{' '}
                  weeks
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-400">Weekly Target</p>
                <p className="text-white font-medium mt-1">
                  {activePlan.weekly_hours_target}h / {activePlan.tss_target_weekly} TSS
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-400">Difficulty</p>
                <span
                  className={`inline-block px-2 py-1 rounded text-sm font-medium mt-1 ${getDifficultyColor(
                    activePlan.difficulty_level
                  )}`}
                >
                  {activePlan.difficulty_level}
                </span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">Progress</span>
                <span className="text-sm text-white font-medium">
                  {getProgress(activePlan)}%
                </span>
              </div>
              <div className="intensity-bar">
                <div
                  className="intensity-fill bg-strava-500"
                  style={{ width: `${getProgress(activePlan)}%` }}
                />
              </div>
              <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                <span>{format(new Date(activePlan.start_date), 'MMM d')}</span>
                <span>{format(new Date(activePlan.end_date), 'MMM d, yyyy')}</span>
              </div>
            </div>

            <div className="flex gap-3">
              <Link
                to={`/plans/${activePlan.id}`}
                className="btn-primary flex items-center gap-2"
              >
                <Calendar className="w-4 h-4" />
                <span>View Schedule</span>
              </Link>
              <button className="btn-secondary flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                <span>View Progress</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Other Plans */}
      {otherPlans.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">Other Plans</h3>
          <div className="grid md:grid-cols-2 gap-4">
            {otherPlans.map((plan) => (
              <Link
                key={plan.id}
                to={`/plans/${plan.id}`}
                className="card-hover p-6"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(plan.status)}
                    <div>
                      <h4 className="font-semibold text-white">{plan.name}</h4>
                      <p className="text-sm text-gray-400">
                        {getGoalLabel(plan.goal)}
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </div>

                <p className="text-sm text-gray-400 mb-4 line-clamp-2">
                  {plan.description}
                </p>

                <div className="flex items-center gap-4 text-sm">
                  <span className="text-gray-400">
                    {format(new Date(plan.start_date), 'MMM d')} -{' '}
                    {format(new Date(plan.end_date), 'MMM d, yyyy')}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      plan.status === 'completed'
                        ? 'bg-blue-500/10 text-blue-400'
                        : plan.status === 'paused'
                        ? 'bg-yellow-500/10 text-yellow-400'
                        : 'bg-gray-500/10 text-gray-400'
                    }`}
                  >
                    {plan.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Plan Templates */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Plan Templates</h3>
        <p className="text-gray-400 mb-4">
          Get started quickly with a pre-built training plan
        </p>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {planTemplates.map((template) => (
            <button
              key={template.id}
              onClick={() => setShowNewPlanModal(true)}
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
                  {template.duration}
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

      {/* New Plan Modal */}
      {showNewPlanModal && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setShowNewPlanModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="card p-6 max-w-md w-full">
              <h3 className="text-xl font-semibold text-white mb-4">
                Create New Plan
              </h3>
              <p className="text-gray-400 mb-6">
                Build a custom training plan tailored to your goals.
              </p>

              <form className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Plan Name
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g., Summer Racing Season"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Goal
                  </label>
                  <select className="input">
                    <option value="ftp_improvement">FTP Improvement</option>
                    <option value="endurance">Endurance</option>
                    <option value="race_preparation">Race Preparation</option>
                    <option value="weight_loss">Weight Loss</option>
                    <option value="general_fitness">General Fitness</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Start Date
                    </label>
                    <input type="date" className="input" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      End Date
                    </label>
                    <input type="date" className="input" />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Difficulty Level
                  </label>
                  <select className="input">
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                    <option value="elite">Elite</option>
                  </select>
                </div>

                <div className="flex gap-3 mt-6">
                  <button type="submit" className="btn-primary flex-1">
                    Create Plan
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowNewPlanModal(false)}
                    className="btn-secondary flex-1"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
