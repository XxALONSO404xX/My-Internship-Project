import React, { useState, useEffect, useContext, useRef } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import { ThemeContext } from '../contexts/ThemeContext';
import { trackEvent } from '../services/analytics-service';
import confetti from 'canvas-confetti';
import ThemeToggle from '../components/ThemeToggle';

// Import our theme and auth CSS
import '../styles/theme.css';
import '../styles/auth.css';

// Add React Router hook for navigation
import { useNavigate, useParams } from 'react-router-dom';

/**
 * Verification Page Component
 * Handles email verification and verification requests
 */
export default function VerificationPage({ email, onSuccess, onCancel }) {
  // Get token from URL params
  const { token } = useParams();

  // Get authentication context
  const { 
    sendVerificationEmail, 
    verifyAccount, 
    verificationEmail,
    error: authError, 
    loading, 
    clearError 
  } = useContext(AuthContext);
  
  // State
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [emailInput, setEmailInput] = useState(email || verificationEmail || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [verificationSent, setVerificationSent] = useState(false);
  const [verificationSuccess, setVerificationSuccess] = useState(false);
  const [countdown, setCountdown] = useState(5); // Increased countdown timer for redirect
  const [progressValue, setProgressValue] = useState(100); // Progress bar value
  const confettiRef = useRef(null); // Ref for confetti animation

  // React Router navigate hook
  const navigate = useNavigate();

  // Sync context error with component error
  useEffect(() => {
    if (authError) {
      setError(authError);
    }
  }, [authError]);

  // If a token is provided, verify it on component mount
  useEffect(() => {
    if (token) {
      verifyEmailWithToken(token);
    }
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps
  
  // Countdown effect for automatic redirect after successful verification
  useEffect(() => {
    let timer;
    if (verificationSuccess && countdown > 0) {
      // Update countdown every second
      timer = setTimeout(() => {
        setCountdown(prevCount => prevCount - 1);
        // Update progress bar in sync with countdown
        setProgressValue(prevCount => (prevCount - 1) * 20); // 5 seconds = 100% to 0%
      }, 1000);
    } else if (verificationSuccess && countdown === 0) {
      // Track redirect event
      trackEvent('auth_verification_auto_redirect', {
        success: true,
        timestamp: new Date().toISOString()
      });
      if (navigate) {
        navigate('/login');
      } else {
        window.location.hash = 'login';
      }
    }
    
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [verificationSuccess, countdown]);
  
  // Confetti effect on successful verification
  useEffect(() => {
    if (verificationSuccess && confettiRef.current) {
      const canvas = confettiRef.current;
      const myConfetti = confetti.create(canvas, {
        resize: true,
        useWorker: true
      });
      
      // Fire confetti
      myConfetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 }
      });
      
      // Fire again after a short delay for a better effect
      setTimeout(() => {
        myConfetti({
          particleCount: 50,
          angle: 60,
          spread: 55,
          origin: { x: 0 }
        });
      }, 250);
      
      setTimeout(() => {
        myConfetti({
          particleCount: 50,
          angle: 120,
          spread: 55,
          origin: { x: 1 }
        });
      }, 400);
    }
  }, [verificationSuccess]);

  // Status for API communication feedback
  const [apiStatus, setApiStatus] = useState({
    state: 'idle', // idle, connecting, success, error
    lastAttempt: null,
    retryCount: 0
  });

  // Handle verification token processing with enhanced error handling and status tracking
  const verifyEmailWithToken = async (verificationToken) => {
    clearError();
    setError('');
    setMessage('');
    setIsSubmitting(true);
    setApiStatus({ state: 'connecting', lastAttempt: new Date(), retryCount: apiStatus.retryCount });

    try {
      // Track verification attempt
      trackEvent('auth_verification_attempt', {
        timestamp: new Date().toISOString(),
        environment: window.electronAPI ? 'electron' : 'browser',
        retry_count: apiStatus.retryCount
      });
      
      // Add timeout to the verification request to prevent long waiting
      const verificationPromise = verifyAccount(verificationToken);
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('API server connection timeout. The server may be offline or unreachable.')), 15000); // Extended timeout
      });
      
      // Race the verification against a timeout
      const result = await Promise.race([verificationPromise, timeoutPromise]);
      
      if (result && result.success) {
        // Track successful verification
        trackEvent('auth_verification_success', {
          timestamp: new Date().toISOString()
        });
        
        setApiStatus({ state: 'success', lastAttempt: new Date(), retryCount: 0 });
        setVerificationSuccess(true);
        setMessage(result.message || 'Your email has been successfully verified. You can now log in.');
        // Start countdown for redirect
        setCountdown(5); // 5 seconds for better UX
        setProgressValue(100);
      } else {
        // Track failed verification
        trackEvent('auth_verification_failed', {
          reason: result?.message || 'Unknown error',
          timestamp: new Date().toISOString()
        });
        
        setApiStatus({ state: 'error', lastAttempt: new Date(), retryCount: apiStatus.retryCount + 1 });
        
        // Handle specific error cases with more user-friendly messages
        if (result?.message?.toLowerCase().includes('token already used') || 
            result?.message?.toLowerCase().includes('already verified')) {
          // This is actually a "success" case - the user is verified
          setVerificationSuccess(true);
          setMessage('Your email has already been verified. You can log in to your account now.');
          // Start countdown for redirect
          setCountdown(5);
          setProgressValue(100);
          
          // Still track as "success" since the account is verified
          trackEvent('auth_verification_already_verified', {
            timestamp: new Date().toISOString()
          });
        } else if (
            result?.message?.toLowerCase().includes('invalid token') ||
            result?.message?.toLowerCase().includes('expired') ||
            result?.message?.toLowerCase().includes('bad request') ||
            result?.message?.toLowerCase().includes('400')
        ) {
          setError(
            <div className="space-y-2">
              <p className="font-medium">Invalid link used or expired</p>
              <p className="text-sm">This may be because:</p>
              <ul className="list-disc ml-5 text-sm">
                <li>The link has expired (valid for 24 hours)</li>
                <li>The link was already used</li>
                <li>The token was incorrectly copied</li>
              </ul>
              <p className="text-sm mt-2">Please request a new verification email using the form below.</p>
            </div>
          );
        } else {
          setError(result?.message || 'Verification failed. Please try again or request a new verification email.');
        }
      }
    } catch (err) {
      // Track verification error
      trackEvent('auth_verification_error', {
        error: err.message,
        timestamp: new Date().toISOString()
      });
      
      setApiStatus({ state: 'error', lastAttempt: new Date(), retryCount: apiStatus.retryCount + 1 });
      
      // Provide more helpful error messages for common issues
      if (err.message.includes('Failed to fetch') || err.message.includes('timeout')) {
        setError(
          <>
            <p className="text-red-600 font-medium">Unable to connect to the verification server.</p>
            <p className="mt-2 text-sm">This could be due to:</p>
            <ul className="list-disc pl-5 mt-1 text-sm space-y-1">
              <li>Network connectivity issues</li>
              <li>Server unavailability</li>
              <li>Firewall or security settings</li>
            </ul>
            <p className="mt-2 text-sm">Try refreshing the page or try again later.</p>
            <button 
              onClick={handleRetryVerification}
              className="mt-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Retry Verification
            </button>
          </>
        );
      } else if (err.message.includes('CORS')) {
        setError(
          <>
            <p className="text-red-600 font-medium">Browser security policy prevented verification.</p>
            <p className="mt-2 text-sm">This is typically caused by cross-origin issues.</p>
            <p className="mt-2 text-sm">Please use the desktop application or contact support for assistance.</p>
            <div className="mt-3 flex space-x-3">
              <button 
                onClick={() => window.location.reload()}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Reload Page
              </button>
            </div>
          </>
        );
      } else if (err.message.includes('500') || err.message.includes('Internal Server Error') || err.message.includes('Server error')) {
        // Specific handling for 500 Internal Server Errors
        setError(
          <>
            <p className="text-red-600 font-medium">Server Error (500)</p>
            <p className="mt-2 text-sm">Our server encountered an unexpected condition that prevented it from fulfilling this request.</p>
            <div className="mt-3 bg-yellow-50 border-l-4 border-yellow-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-yellow-700">
                    This is likely a temporary issue with our authentication servers. Please try again in a few minutes or contact support if the problem persists.
                  </p>
                </div>
              </div>
            </div>
            <div className="mt-4 flex space-x-3">
              <button 
                onClick={handleRetryVerification}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Try Again
              </button>
              <button 
                onClick={() => setShowEmailForm(true)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Request New Verification Email
              </button>
            </div>
          </>
        );
      } else {
        setError(
          <>
            <p className="text-red-600 font-medium">An unexpected error occurred during verification</p>
            <p className="mt-2 text-sm">{err.message}</p>
            <div className="mt-4 flex space-x-3">
              <button 
                onClick={handleRetryVerification}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Try Again
              </button>
              <button 
                onClick={() => setShowEmailForm(true)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Request New Verification
              </button>
            </div>
          </>
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Retry verification
  const handleRetryVerification = () => {
    if (token) {
      // Add small delay before retry
      setTimeout(() => verifyEmailWithToken(token), 500);
    }
  };

  // Handle request for a new verification email with improved error handling and UX
  const handleSendVerification = async (e) => {
    e.preventDefault();
    
    clearError();
    setError('');
    setMessage('');
    setApiStatus({ state: 'idle', lastAttempt: null, retryCount: 0 });
    
    if (!emailInput.trim()) {
      setError('Please enter your email address');
      return;
    }
    
    // Validate email format with more comprehensive regex
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(emailInput)) {
      setError('Please enter a valid email address');
      return;
    }
    
    setIsSubmitting(true);
    setApiStatus({ state: 'connecting', lastAttempt: new Date(), retryCount: apiStatus.retryCount });
    
    try {
      // Track verification email request
      trackEvent('auth_verification_email_request', {
        email_domain: emailInput.split('@')[1],
        timestamp: new Date().toISOString(),
        retry_count: apiStatus.retryCount
      });
      
      // Add timeout to prevent waiting too long
      const emailPromise = sendVerificationEmail(emailInput);
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Email verification request timed out. The server may be offline or unreachable.')), 10000);
      });
      
      // Race the verification against a timeout
      const result = await Promise.race([emailPromise, timeoutPromise]);
      
      if (result && result.success) {
        // Track successful email send
        trackEvent('auth_verification_email_sent', {
          email_domain: emailInput.split('@')[1],
          timestamp: new Date().toISOString()
        });
        
        setApiStatus({ state: 'success', lastAttempt: new Date(), retryCount: 0 });
        setVerificationSent(true);
        setMessage(result.message || 'Verification email sent successfully! Please check your email inbox.');
      } else {
        // Track failed email send
        trackEvent('auth_verification_email_failed', {
          reason: result?.message || 'Unknown error',
          email_domain: emailInput.split('@')[1],
          timestamp: new Date().toISOString()
        });
        
        setApiStatus({ state: 'error', lastAttempt: new Date(), retryCount: apiStatus.retryCount + 1 });
        setError(result?.message || 'Failed to send verification email. Please try again.');
      }
    } catch (err) {
      // Track email send error
      trackEvent('auth_verification_email_error', {
        error: err.message,
        timestamp: new Date().toISOString()
      });
      
      setApiStatus({ state: 'error', lastAttempt: new Date(), retryCount: apiStatus.retryCount + 1 });
      
      // Provide more helpful error messages for common issues
      if (err.message.includes('Failed to fetch') || err.message.includes('timeout')) {
        setError(
          <>
            <p>Unable to connect to the email verification service.</p>
            <p className="mt-2 text-sm">This could be due to network connectivity issues or the server being temporarily unavailable.</p>
            <p className="mt-2 text-sm">Please try again in a few minutes.</p>
          </>
        );
      } else if (err.message.includes('CORS')) {
        setError(
          <>
            <p>Browser security policy prevented sending the verification email.</p>
            <p className="mt-2 text-sm">Please try using the desktop application or a different browser.</p>
          </>
        );
      } else {
        setError(err.message || 'An unexpected error occurred while sending the verification email.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Reset form to try again
  const handleTryAgain = () => {
    setVerificationSent(false);
    setError('');
    setMessage('');
    setApiStatus({ state: 'idle', lastAttempt: null, retryCount: 0 });
  };

  // Handle navigation back to login
  const handleBackToLogin = () => {
    trackEvent('auth_verification_manual_redirect', {
      status: verificationSuccess ? 'after_success' : 'before_completion',
      timestamp: new Date().toISOString()
    });
    if (navigate) {
      navigate('/login');
    } else {
      window.location.hash = 'login';
    }
  };

  // Get theme context
  const { theme } = useContext(ThemeContext);
  
  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4 sm:p-6" 
      style={{
        background: theme === 'dark' 
          ? 'radial-gradient(circle at top left, rgba(59, 130, 246, 0.05), transparent 30%), radial-gradient(circle at bottom right, rgba(99, 102, 241, 0.05), transparent 30%), linear-gradient(to bottom right, #111827, #1f2937)'
          : 'radial-gradient(circle at top left, rgba(59, 130, 246, 0.02), transparent 30%), radial-gradient(circle at bottom right, rgba(99, 102, 241, 0.02), transparent 30%), linear-gradient(to bottom right, #f9fafb, #ffffff)'
      }}
    >
      <div className="relative w-full max-w-md bg-white dark:bg-gray-800 rounded-xl shadow-2xl overflow-hidden border border-gray-200 dark:border-gray-700 fade-in slide-up dark:backdrop-blur-sm dark:bg-opacity-90 dark:shadow-[0_20px_70px_-20px_rgba(0,0,0,0.9)]">
        {/* Theme toggle positioned at top right */}
        <div className="absolute top-4 right-4 fade-in" style={{ animationDelay: '0.2s' }}>
          <ThemeToggle />
        </div>
        
        <div className="w-full space-y-6 p-8">
          <div className="fade-in space-y-2">
            <div className="flex justify-center">
              <div className="relative inline-block">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-indigo-500 blur-md opacity-10 dark:opacity-20 rounded-lg transform -rotate-1"></div>
                <h2 className="relative mt-2 text-center text-3xl font-extrabold text-gray-900 dark:text-white bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-700 dark:from-white dark:to-blue-100">
                  {token ? 'Verifying Email' : 'Email Verification'}
                </h2>
              </div>
            </div>
            <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-300 max-w-xs mx-auto leading-relaxed">
              {token 
                ? 'Please wait while we verify your email address to complete your account activation.'
                : 'Request a verification email to activate your account and gain full access.'}
            </p>
          </div>
          
          {/* Success message - only show for cases other than verification success */}
          {message && !verificationSuccess && (
            <div className="p-4 bg-gradient-to-br from-green-50 to-green-100/90 dark:from-green-900/40 dark:to-green-800/30 border border-green-300/70 dark:border-green-600/50 rounded-lg text-green-700 dark:text-green-200 text-sm shadow-sm slide-in">
              <div className="flex items-center space-x-2">
                <div className="flex-shrink-0 bg-green-100 dark:bg-green-700/50 p-1.5 rounded-full shadow-inner">
                  <svg className="h-4 w-4 text-green-500 dark:text-green-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div className="ml-1 flex-1">
                  {message}
                </div>
              </div>
            </div>
          )}
          
          {/* Canvas for confetti */}
          <canvas ref={confettiRef} className="fixed inset-0 z-10 pointer-events-none" style={{ width: '100%', height: '100%' }}></canvas>
          
          {/* Verification success message with countdown */}
          {verificationSuccess && (
            <div className="p-6 bg-gradient-to-br from-green-50 to-green-100/80 dark:from-green-900/50 dark:to-green-800/30 border-2 border-green-400/60 dark:border-green-500/40 rounded-lg text-center mt-4 relative overflow-hidden shadow-lg slide-up fade-in">
              {/* Decorative success circles */}
              <div className="absolute -top-12 -right-12 w-24 h-24 bg-green-500/10 dark:bg-green-400/10 rounded-full blur-xl"></div>
              <div className="absolute -bottom-8 -left-8 w-20 h-20 bg-green-500/10 dark:bg-green-400/10 rounded-full blur-xl"></div>
              
              <div className="flex justify-center mb-4 pulse-animation">
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-green-400 to-emerald-500 dark:from-green-500 dark:to-emerald-400 rounded-full blur-md opacity-30 animate-pulse"></div>
                  <div className="rounded-full bg-gradient-to-br from-green-100 to-green-200 dark:from-green-800/70 dark:to-green-900/60 p-4 shadow-inner relative z-10">
                    <svg className="w-16 h-16 text-green-500 dark:text-green-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                  </div>
                </div>
              </div>
              <h3 className="text-xl font-bold text-green-800 dark:text-green-100 mb-2">Email Verified Successfully!</h3>
              <p className="text-green-700 dark:text-green-200 mb-5">{message}</p>
              
              {/* Progress bar with improved styling and animation */}
              <div className="w-full bg-gray-200/80 dark:bg-gray-700/50 rounded-full h-4 mb-2 shadow-inner overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-green-500 to-emerald-500 dark:from-green-400 dark:to-emerald-500 h-4 rounded-full transition-all duration-1000 ease-out relative"
                  style={{ width: `${progressValue}%` }}
                >
                  <div className="absolute inset-0 overflow-hidden">
                    <div className="h-full w-20 bg-white/20 animate-[pulse_2s_ease-in-out_infinite] skew-x-12"></div>
                  </div>
                </div>
              </div>
              <p className="text-sm text-green-600 dark:text-green-300/90 font-medium">
                Redirecting to login in <span className="font-bold">{countdown}</span> {countdown === 1 ? 'second' : 'seconds'}...
              </p>
              
              {/* Environment-specific guidance with improved styling */}
              {window.electron ? (
                <p className="mt-3 text-xs text-green-600 dark:text-green-300 bg-green-50 dark:bg-green-800/20 p-2 rounded inline-block border border-green-100 dark:border-green-700/50 shadow-sm">
                  <svg className="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                  You'll be automatically logged in with your credentials
                </p>
              ) : (
                <p className="mt-3 text-xs text-green-600 dark:text-green-300 bg-green-50 dark:bg-green-800/20 p-2 rounded inline-block border border-green-100 dark:border-green-700/50 shadow-sm">
                  <svg className="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                  Prepare to enter your credentials on the login page
                </p>
              )}
            </div>
          )}
          
          {/* API Status - Email Verification Request in Progress */}
          {!token && apiStatus.state === 'connecting' && !verificationSent && !verificationSuccess && (
            <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100/90 dark:from-blue-900/50 dark:to-blue-800/30 border border-blue-300/70 dark:border-blue-600/50 rounded-lg text-blue-700 dark:text-blue-200 text-sm flex items-center shadow-sm slide-in relative overflow-hidden">
              {/* Animated background effect */}
              <div className="absolute inset-0 overflow-hidden">
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-400/30 dark:via-blue-300/20 to-transparent animate-[pulse_2s_ease-in-out_infinite]"></div>
              </div>
              
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-blue-500/10 dark:bg-blue-400/20 blur-md animate-pulse"></div>
                <svg className="animate-spin h-6 w-6 mr-3 text-blue-600 dark:text-blue-400 relative z-10" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25 dark:opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"></circle>
                  <path className="opacity-75 dark:opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              
              <div>
                <span className="font-medium text-blue-800 dark:text-blue-100">Sending verification email...</span>
                <p className="text-xs mt-1 text-blue-600 dark:text-blue-300">Connecting to authentication service...</p>
              </div>
            </div>
          )}
          
          {/* Enhanced API Status Indicators with multi-stage visualization */}
          {token && apiStatus.state === 'connecting' && (
            <div className="p-6 bg-blue-50 dark:bg-blue-900/50 border border-blue-300 dark:border-blue-600/70 rounded-lg shadow-md text-blue-700 dark:text-blue-200 text-sm mb-4">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-700/60 flex items-center justify-center animate-pulse shadow-inner">
                    <svg className="animate-spin h-6 w-6 text-blue-600 dark:text-blue-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                </div>
                <div className="ml-4 flex-1">
                  <h3 className="text-base font-medium text-blue-800 dark:text-blue-100">Verifying Your Account</h3>
                  <div className="mt-2 space-y-1">
                    <p className="dark:text-blue-200">We're processing your verification request. This typically takes less than 10 seconds.</p>
                    <div className="pt-2">
                      <div className="w-full bg-blue-200 dark:bg-blue-700/40 rounded-full h-1.5 shadow-inner">
                        <div className="bg-blue-600 dark:bg-blue-400 h-1.5 rounded-full animate-pulse" style={{width: '50%'}}></div>
                      </div>
                    </div>
                    <p className="text-xs mt-1 text-blue-600 dark:text-blue-300">Connecting to authentication service...</p>
                  </div>
                  
                  {/* Show retry option if it's taking longer than expected */}
                  {apiStatus.retryCount > 0 && (
                    <div className="mt-4">
                      <p className="text-sm font-medium text-blue-700 dark:text-blue-200">Taking longer than expected?</p>
                      <button 
                        onClick={handleRetryVerification}
                        className="mt-2 inline-flex items-center px-3 py-1.5 border border-blue-300 dark:border-blue-500/70 text-sm leading-4 font-medium rounded-md text-blue-700 dark:text-blue-200 bg-blue-50 dark:bg-blue-800/60 hover:bg-blue-100 dark:hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-blue-400 transition-all duration-150 transform hover:scale-105 active:scale-95 shadow-sm hover:shadow"
                      >
                        <svg className="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                        </svg>
                        Retry Verification
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {/* Show a loading skeleton while submitting */}
          {isSubmitting && apiStatus.state !== 'connecting' && (
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm animate-pulse mb-4">
              <div className="flex space-x-4">
                <div className="rounded-full bg-gray-200 dark:bg-gray-700 h-10 w-10"></div>
                <div className="flex-1 space-y-4 py-1">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                  <div className="space-y-2">
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error message with improved formatting and retry options */}
          {error && (
            <div className="p-5 bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/40 dark:to-red-800/30 border border-red-300 dark:border-red-600/70 rounded-lg text-red-700 dark:text-red-200 mb-4 shadow-md slide-up fade-in">
              <div className="flex items-start">
                <div className="flex-shrink-0 bg-red-100 dark:bg-red-700/60 p-2 rounded-full shadow-inner">
                  <svg className="h-6 w-6 text-red-500 dark:text-red-300 shake-animation" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="ml-4 flex-1">
                  <h3 className="text-base font-bold text-red-800 dark:text-red-100">Verification Issue</h3>
                  <div className="mt-2 bg-white/50 dark:bg-red-900/20 p-3 rounded-md border border-transparent dark:border-red-700/30 shadow-sm">
                    {typeof error === 'string' ? (
                      <p className="text-sm">{error}</p>
                    ) : error}
                  </div>
                  
                  {/* Token-related errors */}
                  {(typeof error === 'string' && error.toLowerCase().includes('token')) || 
                  (error.props && error.toString().toLowerCase().includes('token')) ? (
                    <div className="mt-4 flex flex-col space-y-3">
                      <button 
                        onClick={handleRetryVerification}
                        className="inline-flex justify-center items-center px-4 py-2.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-gradient-to-r from-red-500 to-red-600 dark:from-red-600 dark:to-red-700 hover:from-red-600 hover:to-red-700 dark:hover:from-red-500 dark:hover:to-red-600 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:ring-offset-gray-800 focus:ring-red-500 dark:focus:ring-red-400 transition-all duration-200 transform hover:scale-105 active:scale-95 shadow hover:shadow-md w-full md:w-auto"
                      >
                        <svg className="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Request New Verification Link
                      </button>
                      <button 
                        onClick={handleBackToLogin}
                        className="inline-flex justify-center items-center px-4 py-2.5 border border-red-200 dark:border-red-500/50 text-sm font-medium rounded-md text-red-600 dark:text-red-300 bg-white dark:bg-red-900/30 hover:bg-red-50 dark:hover:bg-red-800/40 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:ring-offset-gray-800 focus:ring-red-500 dark:focus:ring-red-400 transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-sm hover:shadow w-full md:w-auto"
                      >
                        <svg className="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
                        </svg>
                        Return to Login
                      </button>
                    </div>
                  ) : null}
                  
                  {/* API Connectivity Errors */}
                  {token && apiStatus.state === 'error' && apiStatus.retryCount < 3 && (
                    <div className="mt-3 flex space-x-2">
                      <button 
                        onClick={() => verifyEmailWithToken(token)}
                        className="px-3 py-1.5 bg-red-100 dark:bg-red-700/60 text-red-700 dark:text-red-100 rounded-md text-xs hover:bg-red-200 dark:hover:bg-red-600 transition-all duration-200 flex items-center shadow-sm hover:shadow transform hover:scale-105 active:scale-95 border border-transparent dark:border-red-600/40"
                      >
                        <svg className="w-3 h-3 mr-1.5 animate-spin-slow" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                        </svg>
                        Try Again
                      </button>
                    </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Resend verification request form when token is invalid or expired */}
        {(typeof error === 'string' && 
          (error.toLowerCase().includes('token') || 
           error.toLowerCase().includes('invalid') || 
           error.toLowerCase().includes('expired'))) && token && (
          <div className="mt-6 p-5 bg-blue-50 dark:bg-blue-900/40 rounded-lg border border-blue-200 dark:border-blue-700/70 shadow-md">
            <h3 className="text-lg font-medium text-blue-800 dark:text-blue-200">Need a new verification link?</h3>
            <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
              Enter your email address below to request a new verification link.
            </p>
            <div className="mt-4">
              <button
                onClick={handleRetryVerification}
                className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 hover:from-blue-600 hover:to-blue-700 dark:hover:from-blue-500 dark:hover:to-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-blue-400 transition-all duration-200 transform hover:scale-105 active:scale-95 shadow hover:shadow-md"
              >
                <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                </svg>
                Request New Verification Link
              </button>
            </div>
          </div>
        )}
        
        {/* Already verified information block with login button */}
        {(typeof error === 'string' && error.toLowerCase().includes('already verified')) && (
          <div className="mt-6 p-5 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/20 rounded-lg border-2 border-green-300 dark:border-green-700 shadow-lg slide-up fade-in">
            <div className="flex justify-center mb-4 pulse-animation">
              <div className="rounded-full bg-green-100 dark:bg-green-800/50 p-3 shadow-inner">
                <svg className="w-14 h-14 text-green-500 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
            </div>
            <h3 className="text-xl font-bold text-green-800 dark:text-green-300 text-center">Your Account is Already Verified!</h3>
            <p className="mt-3 text-sm text-green-700 dark:text-green-400 text-center bg-white/50 dark:bg-black/10 p-3 rounded-md">
              You can now log in to your account with your credentials.
            </p>
            <div className="mt-6 flex justify-center slide-in-delayed-1">
              <button
                onClick={() => {
                  trackEvent('auth_login_from_already_verified');
                  handleBackToLogin();
                }}
                className="inline-flex justify-center items-center px-5 py-3 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-green-500 to-green-600 dark:from-green-600 dark:to-green-700 hover:from-green-600 hover:to-green-700 dark:hover:from-green-500 dark:hover:to-green-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-all duration-200 transform hover:scale-105 active:scale-95 hover:shadow-xl"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
                </svg>
                Log In Now
              </button>
            </div>
          </div>
        )}
        
        {/* After multiple retries, show support options */}
        {apiStatus.retryCount >= 3 && (
          <div className="mt-3 border-t border-red-200 dark:border-red-700 pt-2">
            <p className="text-xs font-medium">Still having trouble?</p>
            <div className="mt-2 flex flex-col space-y-2">
              <a href="#help" className="text-xs text-red-700 dark:text-red-300 hover:underline flex items-center">
                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                View Help Documentation
              </a>
              <a href="mailto:support@iotplatform.com" className="text-xs text-red-700 dark:text-red-300 hover:underline flex items-center">
                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                </svg>
                Contact Support
              </a>
            </div>
          </div>
        )}
        {/* Show verification form only if not already verifying a token and not successfully verified */}
        {!token && !verificationSuccess && (
          <form className="mt-8 space-y-6 fade-in slide-up" onSubmit={handleSendVerification}>
            <div className="relative group">
              <div className="relative">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  className="peer appearance-none block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-blue-500 dark:focus:border-blue-500 sm:text-sm bg-white dark:bg-gray-700/90 text-gray-900 dark:text-white transition-colors duration-200"
                  placeholder="you@example.com"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  disabled={isSubmitting || loading || verificationSent}
                />
                <label 
                  htmlFor="email" 
                  className="absolute top-0 left-0 flex items-center px-4 h-full text-sm text-gray-500 dark:text-gray-300 pointer-events-none transform transition-all duration-200 ease-out peer-focus:text-xs peer-focus:h-1/3 peer-focus:text-blue-500 dark:peer-focus:text-blue-300 peer-placeholder-shown:text-base peer-placeholder-shown:h-full peer-placeholder-shown:text-gray-500 dark:peer-placeholder-shown:text-gray-400"
                >
                  Email address
                </label>
              </div>
              <div className="absolute inset-0 rounded-lg border border-gray-200 dark:border-gray-700 pointer-events-none transform transition-opacity duration-200 opacity-0 group-hover:opacity-100 -mx-1 -my-1"></div>
            </div>
            
            <div className="flex space-x-4">
              <button
                type="button"
                className="group relative flex-1 flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-gray-200 dark:bg-gray-700/80 hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:ring-offset-gray-800 focus:ring-gray-500 dark:focus:ring-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-sm hover:shadow"
                onClick={handleBackToLogin}
                disabled={isSubmitting || loading}
              >
                Back to Login
              </button>
              <button
                type="submit"
                className="group relative flex-1 flex justify-center items-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 hover:from-blue-600 hover:to-blue-700 dark:hover:from-blue-500 dark:hover:to-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95 transition-all duration-200 shadow hover:shadow-md"
                disabled={isSubmitting || loading || verificationSent}
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                    Processing...
                  </>
                ) : (
                  <>
                    <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                    </svg>
                    Send Verification Email
                  </>
                )}
              </button>
            </div>
          </form>
        )}
        
        {/* Actions for verification email sent */}
        {verificationSent && !verificationSuccess && (
          <div className="flex justify-center mt-6 slide-up-delayed">
            <button
              type="button"
              className="inline-flex justify-center items-center py-3 px-5 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 hover:from-blue-600 hover:to-blue-700 dark:hover:from-blue-500 dark:hover:to-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-md hover:shadow-lg"
              onClick={handleBackToLogin}
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 17l-5-5m0 0l5-5m-5 5h12"></path>
              </svg>
              Back to Login
            </button>
          </div>
        )}
        
        {/* Immediate login option after successful verification */}
        {verificationSuccess && (
          <div className="flex justify-center mt-6 slide-up-delayed">
            <button
              type="button"
              className="inline-flex justify-center items-center py-3 px-5 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 hover:from-blue-600 hover:to-blue-700 dark:hover:from-blue-500 dark:hover:to-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-md hover:shadow-lg"
              onClick={handleBackToLogin}
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
              </svg>
              Login Now
            </button>
          </div>
        )}
        
        {/* Loading spinner for token verification */}
        {token && isSubmitting && (
          <div className="flex flex-col items-center justify-center py-8 space-y-3">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-indigo-500 dark:from-blue-500 dark:to-indigo-600 rounded-full blur-md opacity-30 animate-pulse"></div>
              <svg className="animate-spin h-12 w-12 text-blue-500 dark:text-blue-400 relative z-10" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25 dark:opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"></circle>
                <path className="opacity-85 dark:opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-300 animate-pulse">Verifying your email...</p>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
