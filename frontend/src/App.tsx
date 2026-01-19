import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Components (keep these eager - they're needed immediately)
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Loading fallback component
function PageLoader() {
  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-dark-600 border-t-strava-500 rounded-full animate-spin" />
        <p className="text-gray-400">Loading...</p>
      </div>
    </div>
  );
}

// Lazy load pages - these will be split into separate chunks
const Login = lazy(() => import('./pages/Login'));
const AuthCallback = lazy(() => import('./pages/AuthCallback'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const CalendarPage = lazy(() => import('./pages/CalendarPage'));
const Plans = lazy(() => import('./pages/Plans'));
const WorkoutDetail = lazy(() => import('./pages/WorkoutDetail'));
const ActivitiesPage = lazy(() => import('./pages/ActivitiesPage'));
const Profile = lazy(() => import('./pages/Profile'));

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/auth/callback" element={<AuthCallback />} />

            {/* Protected routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Dashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/calendar"
              element={
                <ProtectedRoute>
                  <Layout>
                    <CalendarPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/plans"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Plans />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/plans/:id"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Plans />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/workouts/:id"
              element={
                <ProtectedRoute>
                  <Layout>
                    <WorkoutDetail />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Activities routes */}
            <Route
              path="/activities"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ActivitiesPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/activities/:id"
              element={
                <ProtectedRoute>
                  <Layout>
                    <ActivitiesPage />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <Layout>
                    <div className="text-white">
                      <h1 className="text-2xl font-bold">Analytics</h1>
                      <p className="text-gray-400 mt-2">Analytics page coming soon...</p>
                    </div>
                  </Layout>
                </ProtectedRoute>
              }
            />
            {/* Redirect old AI planner route to plans */}
            <Route
              path="/ai-planner"
              element={<Navigate to="/plans" replace />}
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Layout>
                    <div className="text-white">
                      <h1 className="text-2xl font-bold">Settings</h1>
                      <p className="text-gray-400 mt-2">Settings page coming soon...</p>
                    </div>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Profile />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Catch-all route */}
            <Route
              path="*"
              element={
                <div className="min-h-screen bg-dark-900 flex items-center justify-center">
                  <div className="text-center">
                    <h1 className="text-4xl font-bold text-white mb-4">404</h1>
                    <p className="text-gray-400 mb-6">Page not found</p>
                    <a href="/" className="btn-primary">
                      Go to Dashboard
                    </a>
                  </div>
                </div>
              }
            />
          </Routes>
        </Suspense>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
