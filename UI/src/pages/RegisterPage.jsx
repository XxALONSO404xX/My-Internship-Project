import React, { useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { trackEvent } from '../services/analytics-service';
import { Fade, useColorMode, Box, Flex, Input, Button, useColorModeValue } from '@chakra-ui/react';
// Using inline SVG icons instead of Heroicons to avoid import issues

/**
 * Registration Page Component
 * Allows new users to register for the IoT Platform
 */
export default function RegisterPage({ onSuccess, onCancel }) {
  const navigate = useNavigate();
  const { colorMode } = useColorMode();
  // Get authentication context
  const { register, error: authError, loading, clearError } = useContext(AuthContext);
  
  // Form state
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [feedbackMessage, setFeedbackMessage] = useState('');

  // Sync context error with form error
  useEffect(() => {
    if (authError) {
      setFormError(authError);
    }
  }, [authError]);

  // Password strength calculation
  useEffect(() => {
    if (!password) {
      setPasswordStrength(0);
      return;
    }
    
    // Calculate password strength (0-100)
    let strength = 0;
    
    // Length check (up to 40 points)
    strength += Math.min(password.length * 5, 40);
    
    // Character variety checks
    if (/[A-Z]/.test(password)) strength += 10; // uppercase
    if (/[a-z]/.test(password)) strength += 10; // lowercase
    if (/[0-9]/.test(password)) strength += 10; // numbers
    if (/[^A-Za-z0-9]/.test(password)) strength += 15; // special chars
    
    // Variety of characters
    const uniqueChars = new Set(password.split('')).size;
    strength += Math.min(uniqueChars * 2, 15);
    
    setPasswordStrength(Math.min(strength, 100));
  }, [password]);
  
  // Form validation
  const validateForm = () => {
    // Clear previous errors
    setFormError('');
    setFeedbackMessage('');
    
    if (!username.trim()) {
      setFormError('Username is required');
      return false;
    }
    
    if (!email.trim()) {
      setFormError('Email is required');
      return false;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setFormError('Please enter a valid email address');
      return false;
    }
    
    if (!password) {
      setFormError('Password is required');
      return false;
    }
    
    // Password complexity validation
    if (password.length < 8) {
      setFormError('Password must be at least 8 characters long');
      return false;
    }
    
    if (passwordStrength < 50) {
      setFormError('Please use a stronger password with a mix of letters, numbers, and special characters');
      return false;
    }
    
    if (password !== confirmPassword) {
      setFormError('Passwords do not match');
      return false;
    }
    
    return true;
  };
  
  // Toggle password visibility
  const togglePasswordVisibility = () => {
    setShowPassword(prev => !prev);
  };
  
  // Toggle confirm password visibility
  const toggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(prev => !prev);
  };

  // Handle registration form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Clear previous errors and messages
    clearError();
    setFormError('');
    setSuccessMessage('');
    setFeedbackMessage('Validating information...');
    
    // Validate form
    if (!validateForm()) return;
    
    try {
      setIsSubmitting(true);
      setFeedbackMessage('Creating your account...');
      
      // Track registration attempt in analytics
      trackEvent('auth_register_attempt', { 
        timestamp: new Date().toISOString(),
        environment: window.electron ? 'electron' : 'browser',
        username_length: username.length,
        password_strength: passwordStrength
      });
      
      // Call register function from context
      const result = await register(username, email, password);
      
      if (result.success) {
        // Track successful registration
        trackEvent('auth_register_success', { 
          email_domain: email.split('@')[1],
          timestamp: new Date().toISOString()
        });
        
        setSuccessMessage(result.message || 'Registration successful! Please check your email to verify your account.');
        // Clear form data on success
        setUsername('');
        setEmail('');
        setPassword('');
        setConfirmPassword('');
        
        // Call onSuccess callback if provided
        if (onSuccess && typeof onSuccess === 'function') {
          setTimeout(() => {
            onSuccess(email);
          }, 2000);
        }
      } else {
        // Track failed registration
        trackEvent('auth_register_failed', { 
          reason: result.message,
          timestamp: new Date().toISOString()
        });
        
        setFormError(result.message || 'Registration failed');
      }
    } catch (err) {
      trackEvent('auth_register_error', { 
        error: err.message,
        timestamp: new Date().toISOString()
      });
      
      setFormError(err.message || 'An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
      setFeedbackMessage('');
    }
  };

  // Handle cancel button click
  const handleCancel = () => {
    if (onCancel && typeof onCancel === 'function') {
      onCancel();
    }
  };

  // Update theme colors to match LoginPage
  const bgColor = useColorModeValue('#f5f5f5', '#0a0a0a');
  const cardBg = useColorModeValue('rgba(255,255,255,0.9)', 'rgba(26,26,26,0.9)');
  const textColor = useColorModeValue('#000000', '#ffffff');
  const borderColor = useColorModeValue('#000000', '#404040');

  return (
    <Fade in key={colorMode}>
      <Box 
        minH="100vh" 
        bg={bgColor}
        position="relative"
        overflow="hidden"
      >
        <Flex 
          position="relative"
          zIndex="1"
          minH="100vh"
          align="center"
          justify="center"
          px={4}
        >
          <Box
            w="100%"
            maxW="md"
            p={8}
            borderRadius="xl"
            bg={cardBg}
            border="1px solid"
            borderColor={borderColor}
            boxShadow="xl"
            backdropFilter="blur(10px)"
            color={textColor}
          >
            <div>
              <h2 className="mt-2 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
                Create an Account
              </h2>
              <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-300">
                Register to access the IoT vulnerability scanning platform
              </p>
            </div>
            
            <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
              {/* Success message */}
              {successMessage && (
                <div className="p-3 bg-green-50 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded text-green-700 dark:text-green-300 text-sm">
                  {successMessage}
                </div>
              )}
              
              {/* Error message */}
              {formError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded text-red-700 dark:text-red-300 text-sm">
                  <p className="font-medium">{formError}</p>
                  {formError.includes('already exists') && (
                    <p className="mt-1 text-xs">
                      Try <a 
                        href="/login" 
                        onClick={(e) => {
                          e.preventDefault(); 
                          navigate('/login'); 
                          trackEvent('auth_login_from_register_error');
                        }}
                        className="text-red-600 dark:text-red-400 underline hover:text-red-800"
                      >
                        logging in
                      </a> instead, or <a 
                        href="/forgot-password" 
                        onClick={(e) => {
                          e.preventDefault(); 
                          navigate('/forgot-password'); 
                          trackEvent('auth_forgot_password_from_register_error');
                        }}
                        className="text-red-600 dark:text-red-400 underline hover:text-red-800"
                      >
                        reset your password
                      </a>.
                    </p>
                  )}
                </div>
              )}
              
              {/* Feedback message */}
              {feedbackMessage && !formError && !successMessage && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-700 rounded text-blue-700 dark:text-blue-300 text-sm">
                  {feedbackMessage}
                </div>
              )}

              <div className="space-y-4">
                {/* Username field */}
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Username
                  </label>
                  <Input
                    id="username"
                    type="text"
                    placeholder="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    borderColor={borderColor}
                    _hover={{ borderColor: 'gray.300' }}
                    size="lg"
                  />
                </div>
                
                {/* Email field */}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Email address
                  </label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="Email address"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    borderColor={borderColor}
                    _hover={{ borderColor: 'gray.300' }}
                    size="lg"
                  />
                </div>
                
                {/* Password field */}
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Password
                  </label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      borderColor={borderColor}
                      _hover={{ borderColor: 'gray.300' }}
                      size="lg"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-500"
                      onClick={togglePasswordVisibility}
                      tabIndex="-1"
                    >
                      {showPassword ? (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                        </svg>
                      ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      )}
                    </button>
                  </div>
                  {/* Password strength meter */}
                  <div className="mt-2">
                    <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700">
                      <div 
                        className={`h-full rounded-full ${passwordStrength < 33 ? 'bg-red-500' : passwordStrength < 66 ? 'bg-yellow-500' : 'bg-green-500'}`} 
                        style={{ width: `${passwordStrength}%` }}
                      ></div>
                    </div>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {passwordStrength < 33 && 'Weak password - Add length and complexity'}
                      {passwordStrength >= 33 && passwordStrength < 66 && 'Moderate password - Add special characters'}
                      {passwordStrength >= 66 && 'Strong password'}
                    </p>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Must be at least 8 characters long with a mix of letters, numbers, and special characters
                    </p>
                  </div>
                </div>
                
                {/* Confirm Password field */}
                <div>
                  <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Input
                      id="confirm-password"
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder="Confirm Password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      borderColor={borderColor}
                      _hover={{ borderColor: 'gray.300' }}
                      size="lg"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-500"
                      onClick={toggleConfirmPasswordVisibility}
                      tabIndex="-1"
                    >
                      {showConfirmPassword ? (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                        </svg>
                      ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      )}
                    </button>
                  </div>
                  {confirmPassword && password !== confirmPassword && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                      Passwords do not match
                    </p>
                  )}
                </div>
              </div>

              {/* Submit button */}
              <div>
                <Button
                  type="submit"
                  bg="black"
                  _hover={{ bg: 'gray.800' }}
                  color="white"
                  size="lg"
                  width="full"
                  isLoading={isSubmitting}
                  loadingText="Registering"
                >
                  Register
                </Button>
              </div>
              
              {/* Login link */}
              <div className="text-center mt-4">
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Already have an account?{' '}
                  <a 
                    href="/login" 
                    onClick={(e) => { 
                      e.preventDefault(); 
                      navigate('/login'); 
                      trackEvent('auth_login_click_from_register');
                    }} 
                    className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    Sign in here
                  </a>
                </p>
              </div>
              
              {/* Information text */}
              <div className="text-center text-xs text-gray-500 dark:text-gray-400 mt-4">
                By registering, you'll have access to the IoT vulnerability scanning dashboard,
                which allows you to detect and remediate security issues in your connected devices.
                <br />
                Already have              <button 
                    type="button" 
                    className="text-blue-500 hover:text-blue-700 font-medium"
                    onClick={(e) => {
                      navigate('/login');
                      trackEvent('auth_login_button_from_register');
                    }}
                    disabled={isSubmitting || loading}
                  >
                    Sign in
                  </button>
              </div>
            </form>
          </Box>
        </Flex>
      </Box>
    </Fade>
  );
}
