import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Calendar,
  ClipboardList,
  Activity,
  Settings,
  LogOut,
  Menu,
  X,
  User,
  ChevronDown,
  Bike,
  TrendingUp,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

interface LayoutProps {
  children: React.ReactNode;
}

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
  { path: '/calendar', label: 'Calendar', icon: <Calendar size={20} /> },
  { path: '/plans', label: 'Training Plans', icon: <ClipboardList size={20} /> },
  { path: '/activities', label: 'Activities', icon: <Activity size={20} /> },
  { path: '/analytics', label: 'Analytics', icon: <TrendingUp size={20} /> },
];

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActivePath = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-dark-900 flex">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-64 bg-dark-800 border-r border-dark-700
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-dark-700">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-strava-500 to-strava-600 flex items-center justify-center shadow-glow-orange">
            <Bike className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-white text-lg">ApexPath</h1>
            <p className="text-xs text-gray-400">Training Companion</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setSidebarOpen(false)}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                ${
                  isActivePath(item.path)
                    ? 'bg-dark-700 text-white border-l-2 border-strava-500 pl-[14px]'
                    : 'text-gray-400 hover:text-white hover:bg-dark-700'
                }
              `}
            >
              {item.icon}
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>

        {/* Bottom section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-dark-700">
          <Link
            to="/settings"
            className="flex items-center gap-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-all duration-200"
          >
            <Settings size={20} />
            <span className="font-medium">Settings</span>
          </Link>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Header */}
        <header className="bg-dark-800/80 backdrop-blur-lg border-b border-dark-700 sticky top-0 z-30">
          <div className="flex items-center justify-between px-4 lg:px-6 py-4">
            {/* Mobile menu button */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-colors"
            >
              {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
            </button>

            {/* Page title - hidden on mobile */}
            <div className="hidden lg:block">
              <h2 className="text-xl font-semibold text-white">
                {navItems.find((item) => isActivePath(item.path))?.label || 'Dashboard'}
              </h2>
            </div>

            {/* Right side - Profile dropdown */}
            <div className="relative">
              <button
                onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-dark-700 transition-colors"
              >
                {user?.profile_image ? (
                  <img
                    src={user.profile_image}
                    alt={user.name || 'Profile'}
                    className="w-8 h-8 rounded-full object-cover ring-2 ring-dark-600"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-dark-600 flex items-center justify-center">
                    <User size={18} className="text-gray-400" />
                  </div>
                )}
                <div className="hidden sm:block text-left">
                  <p className="text-sm font-medium text-white">
                    {user?.name || 'Athlete'}
                  </p>
                  {user?.ftp && (
                    <p className="text-xs text-gray-400">FTP: {user.ftp}W</p>
                  )}
                </div>
                <ChevronDown
                  size={16}
                  className={`text-gray-400 transition-transform ${
                    profileDropdownOpen ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {/* Dropdown menu */}
              {profileDropdownOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setProfileDropdownOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-56 bg-dark-800 border border-dark-700 rounded-xl shadow-xl z-50 py-2">
                    <div className="px-4 py-3 border-b border-dark-700">
                      <p className="text-sm font-medium text-white">
                        {user?.name || 'Athlete'}
                      </p>
                      <p className="text-xs text-gray-400">{user?.email || 'Connected via Strava'}</p>
                    </div>
                    <Link
                      to="/profile"
                      onClick={() => setProfileDropdownOpen(false)}
                      className="flex items-center gap-3 px-4 py-2 text-gray-300 hover:bg-dark-700 hover:text-white transition-colors"
                    >
                      <User size={16} />
                      <span>Profile</span>
                    </Link>
                    <Link
                      to="/settings"
                      onClick={() => setProfileDropdownOpen(false)}
                      className="flex items-center gap-3 px-4 py-2 text-gray-300 hover:bg-dark-700 hover:text-white transition-colors"
                    >
                      <Settings size={16} />
                      <span>Settings</span>
                    </Link>
                    <div className="border-t border-dark-700 mt-2 pt-2">
                      <button
                        onClick={handleLogout}
                        className="flex items-center gap-3 px-4 py-2 w-full text-left text-red-400 hover:bg-dark-700 transition-colors"
                      >
                        <LogOut size={16} />
                        <span>Sign out</span>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 p-4 lg:p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
