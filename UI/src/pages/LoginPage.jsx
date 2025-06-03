import React, { useState, useContext, useEffect } from 'react';
import "../login.css"; // Import CSS for animations
import "../styles/auth.css"; // Import enhanced auth styles
import { AuthContext } from '../contexts/AuthContext';
import { ThemeContext } from '../contexts/ThemeContext';
import { trackEvent } from '../services/analytics-service';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import ThemeToggle from '../components/ThemeToggle';

/**
 * Login Page Component
 * Provides UI for authenticating users to the IoT Platform
 */
export default function LoginPage() {
  // Get authentication context
  const { login, error: authError, loading, clearError } = useContext(AuthContext);
  
  // Form state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loginAttempts, setLoginAttempts] = useState(0);
  const [lastLoginTime, setLastLoginTime] = useState(null);
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [attempted, setAttempted] = useState(false); // Track if form submission was attempted

  // Sync context error with form error and set appropriate feedback
  useEffect(() => {
    if (authError) {
      setFormError(authError);
      
      // Special handling for common error messages
      if (authError.includes('Invalid credentials or unverified account')) {
        // Set a more helpful feedback message for unverified accounts
        setFeedbackMessage('If your account is unverified, please check your email for verification instructions');
      }
    }
  }, [authError]);

  // Form validation
  const validateForm = () => {
    if (!username.trim()) {
      setFormError('Username is required');
      return false;
    }
    
    if (!password) {
      setFormError('Password is required');
      return false;
    }
    
    return true;
  };

  // Handle login form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Mark form as attempted to show inline validation messages
    setAttempted(true);
    
    // Clear previous errors and feedback
    clearError();
    setFormError('');
    setFeedbackMessage('');
    
    // Validate form
    if (!validateForm()) return;
    
    // Track login attempt
    setLoginAttempts(prev => prev + 1);
    setLastLoginTime(new Date());
    
    try {
      setIsSubmitting(true);
      setFeedbackMessage('Verifying your credentials...');
      
      // Track event in analytics
      trackEvent('auth_login_attempt', { 
        timestamp: new Date().toISOString(),
        environment: window.electron ? 'electron' : 'browser'
      });
      
      // Call login function from context
      const result = await login(username, password, rememberMe);
      
      if (!result.success) {
        // Enhanced error handling
        setFormError(result.message || 'Login failed');
        
        // Track failed login
        trackEvent('auth_login_failed', { 
          reason: result.message,
          requiresVerification: result.requiresVerification || false
        });
        
        // Special handling for unverified accounts
        if (result.requiresVerification) {
          setFeedbackMessage('Check your email inbox for verification instructions');
        }
      } else {
        // Track successful login
        trackEvent('auth_login_success', { username });
      }
    } catch (err) {
      setFormError(err.message || 'An unexpected error occurred');
      trackEvent('auth_login_error', { error: err.message });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Toggle password visibility
  const togglePasswordVisibility = () => {
    setShowPassword(prev => !prev);
  };

  // Get theme context
  const { theme } = useContext(ThemeContext);
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 py-12 px-4 sm:px-6 lg:px-8 transition-colors duration-300">
      {/* Theme toggle positioned absolutely in top-right corner */}
      <ThemeToggle className="absolute top-4 right-4 fade-in" />
      
      <div className="w-full max-w-md space-y-6 bg-white dark:bg-gray-800 p-8 rounded-xl shadow-lg hover:shadow-xl dark:shadow-gray-900/30 transition-all duration-300 slide-up">
        <div>
          <h2 className="mt-2 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            The Management & security of IoT Objects Platform
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-300">
            Welcome to our Platform!
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {/* Error message with enhanced visualization */}
          {formError && (
            <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg shadow-sm flex items-start space-x-3">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="font-medium text-red-800 dark:text-red-300">{formError}</p>
                {loginAttempts > 1 && (
                  <div className="mt-3 flex flex-col sm:flex-row gap-2 text-sm">
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        window.location.hash = 'forgot-password';
                        trackEvent('auth_reset_password_from_login');
                      }}
                      className="flex items-center justify-center py-1.5 px-3 bg-red-100 hover:bg-red-200 dark:bg-red-800/40 dark:hover:bg-red-800/70 rounded text-red-700 dark:text-red-300 text-xs transition-colors duration-150"
                    >
                      <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                      </svg>
                      Reset your password
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault(); 
                        window.location.hash = 'register';
                        trackEvent('auth_register_from_login');
                      }}
                      className="flex items-center justify-center py-1.5 px-3 bg-red-100 hover:bg-red-200 dark:bg-red-800/40 dark:hover:bg-red-800/70 rounded text-red-700 dark:text-red-300 text-xs transition-colors duration-150"
                    >
                      <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
                      </svg>
                      Create a new account
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Feedback message with improved visual design */}
          {feedbackMessage && !formError && (
            <div className="p-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg shadow-sm flex items-start space-x-3">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-blue-800 dark:text-blue-300">{feedbackMessage}</p>
                {feedbackMessage.toLowerCase().includes('unverified') && (
                  <div className="mt-2">
                    <button 
                      className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded bg-blue-100 text-blue-800 hover:bg-blue-200 dark:bg-blue-800/40 dark:text-blue-300 dark:hover:bg-blue-800/70 transition-colors"
                      onClick={(e) => {
                        e.preventDefault();
                        window.location.hash = 'verify-email';
                        trackEvent('auth_verification_from_login');
                      }}
                    >
                      <svg className="w-3.5 h-3.5 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                      Verify my email now
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="space-y-4">
            {/* Username field with visible label */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Username
                <span className="text-red-600 ml-1">*</span>
              </label>
              <div className="relative rounded-md">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                  </svg>
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  className="appearance-none block w-full pl-10 px-3 py-3 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:border-blue-500 transition-colors text-gray-900 dark:text-white dark:bg-gray-800 sm:text-sm"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isSubmitting || loading}
                  aria-describedby="username-error"
                />
              </div>
              {username === '' && attempted && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400 fade-in" id="username-error">
                  Username is required
                </p>
              )}
            </div>
            
            <div className="form-group slide-in relative" style={{animationDelay: '200ms'}}>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`appearance-none rounded-lg relative block w-full px-3 py-3 border ${attempted && !password ? 'border-red-300 dark:border-red-700' : 'border-gray-300 dark:border-gray-600'} placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm transition-all duration-200`}
                placeholder="Enter your password"
                required
              />
              <button
                type="button"
                className="absolute top-9 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-200"
                onClick={togglePasswordVisibility}
                tabIndex="-1"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <EyeSlashIcon className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <EyeIcon className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
              {attempted && !password && <p className="mt-2 text-sm text-red-600 dark:text-red-400 fade-in">Password is required</p>}
            </div>
          </div>

          {/* Remember me checkbox */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center slide-in" style={{animationDelay: '250ms'}}>
              <div className="relative flex items-start">
                <div className="flex items-center h-5">
                  <input
                    id="remember-me"
                    name="remember-me"
                    type="checkbox"
                    className="h-5 w-5 text-blue-600 focus:ring-blue-500 dark:bg-gray-800 border-gray-300 dark:border-gray-600 rounded transition-colors"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    disabled={isSubmitting || loading}
                  />
                </div>
                <div className="ml-2 text-sm">
                  <label htmlFor="remember-me" className="font-medium text-gray-700 dark:text-gray-300 select-none">
                    Remember me
                  </label>
                  <p className="text-gray-500 dark:text-gray-400 text-xs">Keep me signed in on this device</p>
                </div>
              </div>
            </div>
          </div>

          {/* Submit button with enhanced appearance */}
          <div className="mt-2">
            <button
              type="submit"
              disabled={isSubmitting || loading}
              className={`group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] ${isSubmitting || loading ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'} slide-in`}
              style={{animationDelay: '300ms'}}
            >
              {isSubmitting || loading ? (
                <>
                  <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </span>
                  <span className="flex items-center">Signing in<span className="dots-loading"><span>.</span><span>.</span><span>.</span></span></span>
                </>
              ) : (
                <span className="flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
                  </svg>
                  Sign in to your account
                </span>
              )}
            </button>
          </div>
          
          {/* Registration and password reset links */}
          <div className="mt-8 text-center slide-in" style={{animationDelay: '400ms'}}>
            <div className="relative py-2">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
              </div>
              <div className="relative flex justify-center">
                <span className="px-2 bg-white dark:bg-gray-700 text-sm text-gray-500 dark:text-gray-400">Or</span>
              </div>
            </div>
            
            <div className="mt-4 flex flex-col sm:flex-row justify-center gap-4 sm:gap-6">
              <a
                href="#register"
                className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md text-white bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 hover:from-blue-600 hover:to-blue-700 dark:hover:from-blue-500 dark:hover:to-blue-600 transition-all duration-300 transform hover:scale-[1.03] hover:shadow-md"
                onClick={(e) => {
                  e.preventDefault();
                  window.location.hash = 'register';
                  trackEvent('auth_register_clicked');
                }}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
                </svg>
                Create account
              </a>
              
              <a
                href="#forgot-password"
                className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-300 transform hover:scale-[1.03] hover:shadow-md"
                onClick={(e) => {
                  e.preventDefault();
                  window.location.hash = 'forgot-password';
                  trackEvent('auth_forgot_password_clicked');
                }}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                </svg>
                Forgot password?
              </a>
            </div>
          </div>
          
          {/* Information text with legal links */}
          <div className="mt-4 text-center text-xs text-gray-500 dark:text-gray-400 slide-in" style={{animationDelay: '450ms'}}>
            By signing in, you agree to our
            <a href="#terms" className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 mx-1">Terms</a>
            and
            <a href="#privacy" className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 mx-1">Privacy Policy</a>
          </div>
        </form>
      </div>
    </div>
  );
}
