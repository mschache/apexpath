import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Bike,
  TrendingUp,
  Calendar,
  Activity,
  Target,
  Zap,
  Shield,
  ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

// Strava brand colors
const STRAVA_ORANGE = '#fc4c02';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuthStore();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as { from?: Location })?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleStravaLogin = () => {
    // Redirect to backend OAuth endpoint
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    window.location.href = `${apiUrl}/auth/strava/login/redirect`;
  };

  const features = [
    {
      icon: <TrendingUp className="w-6 h-6" />,
      title: 'Track Your Fitness',
      description: 'Monitor CTL, ATL, and TSB to optimize your training load',
    },
    {
      icon: <Calendar className="w-6 h-6" />,
      title: 'Plan Your Training',
      description: 'Create personalized training plans that adapt to your goals',
    },
    {
      icon: <Activity className="w-6 h-6" />,
      title: 'Analyze Performance',
      description: 'Deep insights into your power, heart rate, and cadence data',
    },
    {
      icon: <Target className="w-6 h-6" />,
      title: 'Reach Your Goals',
      description: 'Set targets and track progress towards your cycling ambitions',
    },
  ];

  return (
    <div className="min-h-screen bg-dark-900 flex">
      {/* Left side - Hero section */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-3/5 relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-dark-900 via-dark-800 to-strava-900/20" />

        {/* Decorative elements */}
        <div className="absolute top-20 left-20 w-72 h-72 bg-strava-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-20 w-96 h-96 bg-strava-500/5 rounded-full blur-3xl" />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-12 xl:px-20">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-strava-500 to-strava-600 flex items-center justify-center shadow-glow-orange">
              <Bike className="w-10 h-10 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">ApexPath</h1>
              <p className="text-gray-400 text-lg">Your AI-Powered Training Companion</p>
            </div>
          </div>

          <h2 className="text-3xl xl:text-4xl font-bold text-white mb-6 leading-tight">
            Train smarter.<br />
            <span className="gradient-text">Ride stronger.</span>
          </h2>

          <p className="text-lg text-gray-300 mb-12 max-w-lg">
            Connect your Strava account to unlock personalized training insights,
            intelligent workout planning, and comprehensive fitness tracking.
          </p>

          {/* Feature list */}
          <div className="grid grid-cols-2 gap-6 max-w-xl">
            {features.map((feature, index) => (
              <div
                key={index}
                className="flex items-start gap-4 p-4 rounded-xl bg-dark-800/50 border border-dark-700/50 hover:border-dark-600 transition-colors"
              >
                <div className="p-2 rounded-lg bg-strava-500/10 text-strava-500">
                  {feature.icon}
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">{feature.title}</h3>
                  <p className="text-sm text-gray-400">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center justify-center gap-3 mb-8 lg:hidden">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-strava-500 to-strava-600 flex items-center justify-center shadow-glow-orange">
              <Bike className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">ApexPath</h1>
          </div>

          {/* Login card */}
          <div className="card p-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">
                Welcome to ApexPath
              </h2>
              <p className="text-gray-400">
                Connect with Strava to get started
              </p>
            </div>

            {/* Strava Connect Button */}
            <button
              onClick={handleStravaLogin}
              className="w-full flex items-center justify-center gap-3 py-4 px-6 rounded-lg font-semibold text-white transition-all duration-200 hover:opacity-90 active:scale-[0.98]"
              style={{ backgroundColor: STRAVA_ORANGE }}
            >
              {/* Strava logo SVG */}
              <svg
                viewBox="0 0 24 24"
                className="w-6 h-6"
                fill="currentColor"
              >
                <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.599h4.172L10.463 0l-7 13.828h4.169" />
              </svg>
              <span>Connect with Strava</span>
              <ChevronRight className="w-5 h-5" />
            </button>

            {/* Divider */}
            <div className="flex items-center gap-4 my-8">
              <div className="flex-1 h-px bg-dark-600" />
              <span className="text-sm text-gray-500">Why Strava?</span>
              <div className="flex-1 h-px bg-dark-600" />
            </div>

            {/* Benefits */}
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="p-1 rounded-full bg-green-500/20 text-green-400">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-sm text-white font-medium">
                    Automatic activity sync
                  </p>
                  <p className="text-xs text-gray-400">
                    Your rides are imported automatically
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-1 rounded-full bg-blue-500/20 text-blue-400">
                  <Activity className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-sm text-white font-medium">
                    Rich activity data
                  </p>
                  <p className="text-xs text-gray-400">
                    Access power, heart rate, and cadence streams
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-1 rounded-full bg-purple-500/20 text-purple-400">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-sm text-white font-medium">
                    Secure connection
                  </p>
                  <p className="text-xs text-gray-400">
                    We only read your activity data, nothing else
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-sm text-gray-500 mt-6">
            By connecting, you agree to our{' '}
            <a href="/terms" className="text-strava-500 hover:underline">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="/privacy" className="text-strava-500 hover:underline">
              Privacy Policy
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
