import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Bike, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import api, { endpoints } from '../utils/api';
import type { LoginResponse } from '../types';

type CallbackStatus = 'processing' | 'success' | 'error';

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login, setError } = useAuthStore();
  const [status, setStatus] = useState<CallbackStatus>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const handleCallback = async () => {
      // Get code and state from URL params
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Handle Strava OAuth error
      if (error) {
        setStatus('error');
        setErrorMessage(errorDescription || 'Authorization was denied');
        setError(errorDescription || 'Authorization was denied');
        return;
      }

      // Check for required params
      if (!code) {
        setStatus('error');
        setErrorMessage('No authorization code received');
        setError('No authorization code received');
        return;
      }

      try {
        // Exchange code for token via backend (GET request with code as query param)
        const response = await api.get<{ user: LoginResponse['user']; token: { access_token: string; token_type: string } }>(
          `${endpoints.strava.callback}?code=${encodeURIComponent(code)}${state ? `&state=${encodeURIComponent(state)}` : ''}`
        );

        const { user, token } = response.data;

        // Convert backend response format to frontend expected format
        const tokens = {
          access_token: token.access_token,
          token_type: token.token_type,
        };

        // Store user and tokens in auth store
        login(user, tokens);

        setStatus('success');

        // Redirect to dashboard after short delay
        setTimeout(() => {
          navigate('/', { replace: true });
        }, 1500);
      } catch (err) {
        console.error('Auth callback error:', err);
        setStatus('error');

        // Extract error message
        let message = 'Failed to complete authentication';
        if (err instanceof Error) {
          message = err.message;
        }
        if (typeof err === 'object' && err !== null) {
          const axiosError = err as { response?: { data?: { detail?: string } } };
          if (axiosError.response?.data?.detail) {
            message = axiosError.response.data.detail;
          }
        }

        setErrorMessage(message);
        setError(message);
      }
    };

    handleCallback();
  }, [searchParams, login, setError, navigate]);

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-strava-500 to-strava-600 flex items-center justify-center shadow-glow-orange">
            <Bike className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">ApexPath</h1>
        </div>

        {/* Status card */}
        <div className="card p-8 text-center">
          {status === 'processing' && (
            <>
              <div className="flex justify-center mb-6">
                <div className="w-16 h-16 relative">
                  {/* Spinning ring */}
                  <div className="absolute inset-0 border-4 border-dark-600 rounded-full" />
                  <div className="absolute inset-0 border-4 border-transparent border-t-strava-500 rounded-full animate-spin" />
                  {/* Center icon */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Bike className="w-6 h-6 text-strava-500" />
                  </div>
                </div>
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">
                Connecting to Strava
              </h2>
              <p className="text-gray-400">
                Please wait while we complete your authentication...
              </p>

              {/* Progress steps */}
              <div className="mt-6 space-y-2">
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
                    <CheckCircle2 className="w-3 h-3 text-green-400" />
                  </div>
                  <span className="text-gray-400">Authorization received</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-5 h-5 rounded-full bg-strava-500/20 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-strava-500 animate-pulse" />
                  </div>
                  <span className="text-gray-300">Exchanging token...</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-5 h-5 rounded-full bg-dark-600 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-dark-500" />
                  </div>
                  <span className="text-gray-500">Loading your data</span>
                </div>
              </div>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="flex justify-center mb-6">
                <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center">
                  <CheckCircle2 className="w-10 h-10 text-green-400" />
                </div>
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">
                Successfully Connected!
              </h2>
              <p className="text-gray-400 mb-4">
                Your Strava account has been linked. Redirecting to your dashboard...
              </p>
              <div className="flex justify-center">
                <div className="w-32 h-1 bg-dark-600 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500 rounded-full animate-[progress_1.5s_ease-in-out]" />
                </div>
              </div>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="flex justify-center mb-6">
                <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center">
                  <AlertCircle className="w-10 h-10 text-red-400" />
                </div>
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">
                Connection Failed
              </h2>
              <p className="text-gray-400 mb-6">{errorMessage}</p>
              <div className="space-y-3">
                <button
                  onClick={() => {
                    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
                    window.location.href = `${apiUrl}/auth/strava/login/redirect`;
                  }}
                  className="btn-primary w-full"
                >
                  Try Again
                </button>
                <button
                  onClick={() => navigate('/login', { replace: true })}
                  className="btn-secondary w-full"
                >
                  Back to Login
                </button>
              </div>
            </>
          )}
        </div>

        {/* Help text */}
        {status === 'error' && (
          <p className="text-center text-sm text-gray-500 mt-6">
            Having trouble?{' '}
            <a href="/support" className="text-strava-500 hover:underline">
              Contact support
            </a>
          </p>
        )}
      </div>

      {/* Progress animation keyframes (inline for this component) */}
      <style>{`
        @keyframes progress {
          0% { width: 0%; }
          100% { width: 100%; }
        }
      `}</style>
    </div>
  );
}
