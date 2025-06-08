import React, { useState, useContext, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import "../login.css"; // Import CSS for animations
import "../styles/auth.css"; // Import enhanced auth styles
import { AuthContext } from '../contexts/AuthContext';
import { ThemeContext } from '../contexts/ThemeContext';
import { trackEvent } from '../services/analytics-service';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import { 
  Box, 
  Flex, 
  Input, 
  InputGroup, 
  InputRightElement, 
  IconButton, 
  Button, 
  HStack,
  useTheme,
  useColorModeValue 
} from '@chakra-ui/react';

/**
 * Login Page Component
 * Provides UI for authenticating users to the IoT Platform
 */
export default function LoginPage() {
  // Get authentication context
  const { login, error: authError, loading, clearError } = useContext(AuthContext);
  
  // Get theme context
  const { theme } = useContext(ThemeContext);
  const navigate = useNavigate();
  
  // Precomputed colors to satisfy Rules of Hooks
  const headingColor  = useColorModeValue('black','white');
  const subTextColor  = useColorModeValue('gray.600','gray.300');
  const errorColor    = useColorModeValue('red.600','red.400');
  const feedbackColor = useColorModeValue('blue.600','blue.300');
  const hoverBlue     = useColorModeValue('blue.700','blue.200');
  const linkPurple    = useColorModeValue('purple.600','purple.300');
  const hoverPurple   = useColorModeValue('purple.700','purple.200');
  
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
        // Redirect on successful login
        // Reset welcome animation flag for new session
        sessionStorage.removeItem('welcomeShown');
        navigate('/dashboard');
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

  // Add theme-aware colors at top of component
  const bgColor = useColorModeValue('#f5f5f5', '#0a0a0a');
  const cardBg = useColorModeValue('rgba(255,255,255,0.9)', 'rgba(26,26,26,0.95)');
  const textColor = useColorModeValue('gray.800', 'white');
  const placeholderColor = useColorModeValue('gray.500', 'gray.400');
  const labelColor = useColorModeValue('gray.700', 'gray.300');
  const borderColor = useColorModeValue('#000000', '#404040');

  return (
    <Box
      minH="100vh"
      bg={useColorModeValue('#f5f5f5', '#0a0a0a')}
      position="relative"
      overflow="hidden"
    >
      {/* Login card */}
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
            <h1 className="text-3xl font-bold text-center" style={{ color: headingColor }}>
              The Management & security of IoT Objects Platform
            </h1>
            <p className="mt-2 text-center text-sm" style={{ color: subTextColor }}>
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
                  <p style={{ color: errorColor }} className="font-medium">{formError}</p>
                  {loginAttempts > 1 && (
                    <div className="mt-3 flex flex-col sm:flex-row gap-2 text-sm">
                      <Button
                        variant="link"
                        color={useColorModeValue('blue.600', 'blue.300')}
                        _hover={{ 
                          textDecoration: 'none',
                          color: hoverBlue
                        }}
                        onClick={(e) => {
                          e.preventDefault();
                          navigate('/forgot-password');
                          trackEvent('auth_reset_password_from_login');
                        }}
                      >
                        Reset your password
                      </Button>
                      <Button
                        variant="link"
                        color={linkPurple}
                        _hover={{
                          textDecoration: 'none',
                          color: hoverPurple
                        }}
                        onClick={(e) => {
                          e.preventDefault(); 
                          navigate('/register');
                          trackEvent('auth_register_from_login');
                        }}
                      >
                        Create a new account
                      </Button>
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
                  <p style={{ color: feedbackColor }} className="text-blue-800 dark:text-blue-300">{feedbackMessage}</p>
                  {feedbackMessage.toLowerCase().includes('unverified') && (
                    <div className="mt-2">
                      <Button
                        variant="link"
                        color={feedbackColor}
                        _hover={{ 
                          textDecoration: 'none',
                          color: hoverBlue
                        }}
                        onClick={(e) => {
                          e.preventDefault();
                          navigate('/verify-email');
                          trackEvent('auth_verification_from_login');
                        }}
                      >
                        Verify my email now
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="space-y-4">
              {/* Username field with visible label */}
              <div>
                <label style={{ color: labelColor }} htmlFor="username" className="block text-sm font-medium mb-1">
                  Username
                  <span className="text-red-600 ml-1">*</span>
                </label>
                <Input
                  borderColor={borderColor}
                  _hover={{ borderColor: 'gray.300' }}
                  _focus={{
                    borderColor: 'black',
                    boxShadow: '0 0 0 1px black',
                    bg: useColorModeValue('white', 'gray.800')
                  }}
                  size="lg"
                  bg={useColorModeValue('white', 'rgba(26,26,26,0.95)')}
                  type="text"
                  id="username"
                  name="username"
                  autoComplete="username"
                  required
                  variant="outline"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isSubmitting || loading}
                  aria-describedby="username-error"
                  placeholder="Enter your username"
                  color={textColor}
                  _placeholder={{ color: placeholderColor }}
                />
                {username === '' && attempted && (
                  <p style={{ color: errorColor }} className="mt-1 text-sm fade-in" id="username-error">
                    Username is required
                  </p>
                )}
              </div>
              
              <div className="form-group slide-in relative" style={{animationDelay: '200ms'}}>
                <label style={{ color: labelColor }} htmlFor="password" className="block text-sm font-medium mb-1">Password</label>
                <InputGroup size="lg">
                  <Input
                    borderColor={borderColor}
                    _hover={{ borderColor: 'gray.300' }}
                    _focus={{
                      borderColor: 'black',
                      boxShadow: '0 0 0 1px black',
                      bg: useColorModeValue('white', 'rgba(26,26,26,0.95)')
                    }}
                    size="lg"
                    bg={useColorModeValue('white', 'rgba(26,26,26,0.95)')}
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    name="password"
                    autoComplete="current-password"
                    variant="outline"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    color={textColor}
                    _placeholder={{ color: placeholderColor }}
                  />
                  <InputRightElement>
                    <IconButton
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      icon={showPassword ? <EyeSlashIcon /> : <EyeIcon />}
                      variant="ghost"
                      color={useColorModeValue('gray.500', 'gray.400')}
                      _hover={{ color: useColorModeValue('black', 'white') }}
                      onClick={togglePasswordVisibility}
                    />
                  </InputRightElement>
                </InputGroup>
                {attempted && !password && <p style={{ color: errorColor }} className="mt-2 text-sm fade-in">Password is required</p>}
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
                    <label style={{ color: labelColor }} htmlFor="remember-me" className="font-medium select-none">
                      Remember me
                    </label>
                    <p style={{ color: useColorModeValue('gray.500', 'gray.400') }} className="text-gray-500 dark:text-gray-400 text-xs">Keep me signed in on this device</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Submit button with enhanced appearance */}
            <div className="mt-2">
              <Button
                size="lg"
                w="full"
                fontWeight="bold"
                borderRadius="md"
                bg="black"
                color="white"
                _hover={{
                  bg: '#333',
                  transform: 'scale(1.02)'
                }}
                _active={{
                  transform: 'none'
                }}
                border="2px solid"
                borderColor="black"
                isLoading={isSubmitting}
                onClick={handleSubmit}
              >
                Sign In
              </Button>
            </div>
            
            {/* Registration and password reset links */}
            <div className="mt-8 text-center slide-in" style={{animationDelay: '400ms'}}>
              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
                </div>
                <div className="relative flex justify-center">
                  <span style={{ color: useColorModeValue('gray.500', 'gray.400') }} className="px-2 bg-white dark:bg-gray-700 text-sm text-gray-500 dark:text-gray-400">Or</span>
                </div>
              </div>
              
              <HStack justify="space-between">
                <Button
                  variant="ghost"
                  color={useColorModeValue('gray.600', 'gray.300')}
                  _hover={{
                    color: useColorModeValue('black', 'white'),
                    bg: 'transparent'
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    navigate('/forgot-password');
                    trackEvent('auth_forgot_password_clicked');
                  }}
                >
                  Forgot password?
                </Button>
                <Button
                  variant="ghost"
                  color={useColorModeValue('gray.600', 'gray.300')}
                  _hover={{
                    color: useColorModeValue('black', 'white'),
                    bg: 'transparent'
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    navigate('/register');
                    trackEvent('auth_register_clicked');
                  }}
                >
                  Create account
                </Button>
              </HStack>
            </div>
            
            {/* Information text with legal links */}
            <div className="mt-4 text-center text-xs text-gray-500 dark:text-gray-400 slide-in" style={{animationDelay: '450ms'}}>
              By signing in, you agree to our
              <a style={{ color: useColorModeValue('blue.600', 'blue.300') }} href="#terms" className="hover:text-blue-800 dark:hover:text-blue-300 mx-1">Terms</a>
              and
              <a style={{ color: useColorModeValue('blue.600', 'blue.300') }} href="#privacy" className="hover:text-blue-800 dark:hover:text-blue-300 mx-1">Privacy Policy</a>
            </div>
          </form>
        </Box>
      </Flex>
    </Box>
  );
}
