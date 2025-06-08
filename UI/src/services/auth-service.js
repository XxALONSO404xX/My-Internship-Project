/**
 * Authentication Service for IoT Platform
 * Handles all authentication API calls and token management
 */

// Base API URL for authentication endpoints
// Use explicit IPv4 address instead of 'localhost' to avoid IPv6 resolution issues
import { setUserData, getUserData, clearUserData } from './storage-service';

// Determine if we're in development or production environment
const isDevelopment = process.env.NODE_ENV === 'development';

// No demo mode - we'll connect directly to the API

// API endpoints - make these work in both Electron and browser environments
const getBaseApiUrl = () => {
  // Check if we're in Electron environment
  const isElectron = window.electronAPI !== undefined || 
                    (window.navigator && window.navigator.userAgent && 
                     window.navigator.userAgent.indexOf('Electron') >= 0);
  
  // Debug logging
  console.log(`Environment detection - isElectron: ${isElectron}, isDevelopment: ${isDevelopment}`);
  console.log(`Current location: ${window.location.href}`);
  
  // For tests and direct access, prioritize using a direct URL
  if (window.location.hostname === '' || window.location.protocol === 'file:') {
    // We're likely opening the file directly - use localhost API
    console.log('Direct file access detected - using localhost API');
    return 'http://localhost:8000';
  }
  
  // For browser environments, we need to be smarter about API URL selection
  const hostname = window.location.hostname;
  const port = window.location.port;
  
  // Always use localhost for Electron regardless of environment
  if (isElectron) {
    console.log('Using Electron-specific API endpoint: http://localhost:8000');
    return 'http://localhost:8000';
  }
  
  // For local development in browser
  if (isDevelopment || hostname === 'localhost' || hostname === '127.0.0.1') {
    // Always use explicit localhost:8000 for development, regardless of the frontend port
    // This is critical for cross-origin requests between frontend (port 1234) and backend (port 8000)
    console.log('Using development API endpoint: http://localhost:8000');
    return 'http://localhost:8000';
  }
  
  // For production environment in browser
  // Try to determine if we're on the same server or need to use a specific API URL
  const protocol = window.location.protocol;
  let apiUrl;
  
  // If we're on a standard port (80/443), don't include port in API URL
  if (port === '80' || port === '443' || port === '') {
    apiUrl = `${protocol}//${hostname}/api`; // Assume API is at /api path
  } else {
    // Otherwise use the current hostname but default API port
    apiUrl = `${protocol}//${hostname}:8000`;
  }
  
  console.log(`Using browser API endpoint: ${apiUrl}`);
  return apiUrl;
};

// Updated API URL construction to align with backend structure
export const API_BASE_URL = getBaseApiUrl();

// IMPORTANT: The full API path structure analysis based on backend router configuration:
// The API URL structure might vary depending on the backend implementation
// Common patterns include:
// - BASE_URL + '/api/v1/auth' (FastAPI with versioning)
// - BASE_URL + '/api/auth' (FastAPI without versioning)
// - BASE_URL + '/auth' (Simple Express/Node.js)

// Define multiple possible auth API URL patterns to try
const AUTH_API_URLS = {
  // Primary URL with versioning
  v1: `${API_BASE_URL}/api/v1/auth`,
  // Without versioning
  standard: `${API_BASE_URL}/api/auth`,
  // Direct auth endpoint
  direct: `${API_BASE_URL}/auth`,
  // Common localhost dev patterns
  localV1: 'http://localhost:8000/api/v1/auth',
  localStandard: 'http://localhost:8000/api/auth',
  localDirect: 'http://localhost:8000/auth'
};

// User confirmed the API uses v1 prefix
const AUTH_API_URL = AUTH_API_URLS.v1;

/**
 * Enhanced fetch function with retry capability and improved error handling
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @param {number} [retries=2] - Number of retries before giving up
 * @returns {Promise<Object>} - Parsed JSON response
 */
async function enhancedFetch(url, options, retries = 2) {
  // Log the request details
  console.log(`Making fetch request to: ${url}`, { 
    method: options.method, 
    headers: options.headers,
    retries
  });
  
  try {
    const response = await fetch(url, options);
    console.log(`Fetch response status: ${response.status}`);
    
    // Handle HTTP error responses
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`HTTP error ${response.status}:`, errorText);
      
      // Try to parse the error response as JSON
      try {
        const errorJson = JSON.parse(errorText);
        return { 
          success: false, 
          status: response.status,
          message: errorJson.detail || errorJson.message || `HTTP error ${response.status}`,
          error: errorJson
        };
      } catch (e) {
        // If not valid JSON, return the text
        return { 
          success: false, 
          status: response.status,
          message: errorText || `HTTP error ${response.status}`,
        };
      }
    }
    
    // Handle successful response
    try {
      const data = await response.json();
      return { success: true, ...data };
    } catch (e) {
      console.error('Error parsing JSON response:', e);
      return { 
        success: true, 
        message: 'Operation completed, but response was not valid JSON',
        rawResponse: await response.text()
      };
    }
  } catch (error) {
    console.error(`Fetch error (${retries} retries left):`, error);
    
    if (retries > 0) {
      console.log(`Retrying fetch to ${url} in 1 second...`);
      // Wait 1 second before retrying
      await new Promise(resolve => setTimeout(resolve, 1000));
      return enhancedFetch(url, options, retries - 1);
    }
    
    throw new Error(
      `Failed to connect to server after multiple attempts: ${error.message}. ` +
      'Please check your network connection and ensure the server is running.'
    );
  }
}

// Log the API configuration for debugging
console.log('Auth Service: API endpoints configured as:', {
  base: API_BASE_URL,
  auth: AUTH_API_URL
});

/**
 * Attempt login with credentials
 * @param {string} username - Username for login
 * @param {string} password - Password for login
 * @param {boolean} rememberMe - Whether to create a persistent session
 * @returns {Promise<Object>} Login result with success status and client data
 */
export async function login(username, password, rememberMe = false) {
  console.log('Auth Service: Attempting login', { username, rememberMe });
  
  try {
    console.log('Auth Service: Sending login request to:', `${AUTH_API_URL}/login`);
    
    // Login via Electron secure channel or HTTP fetch in browser
    let response;
    if (window.electronAPI && typeof window.electronAPI.apiRequest === 'function') {
      response = await window.electronAPI.apiRequest({
        url: `${AUTH_API_URL}/login`,
        method: 'POST',
        body: { username, password, remember_me: rememberMe }
      });
    } else {
      // Browser fallback
      const res = await fetch(`${AUTH_API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, remember_me: rememberMe })
      });
      const data = await res.json();
      response = { ok: res.ok, status: data.status || res.status, data };
    }
    
    // Log the complete response for debugging
    console.log('Auth Service: Received response:', JSON.stringify(response));
    
    // Handle error response
    if (!response.ok) {
      // Log the complete error response
      console.error('Auth Service: Error details:', {
        status: response.status,
        data: response.data,
        error: response.error
      });
      
      // Check if it's an unverified account error
      if (response.data?.code === 'unverified_account') {
        return {
          success: false,
          message: 'Your account is not verified. Please check your email for a verification link.',
          requiresVerification: true,
          email: username.includes('@') ? username : null // Assume it's an email if it contains @
        };
      }

      const errorMessage = response.data?.message || 
                           response.data?.detail || 
                           response.error ||
                           'Authentication failed';
      console.error('Auth Service: Login failed', errorMessage);
      return { 
        success: false, 
        message: errorMessage
      };
    }
    
    // Extract token data from nested response structure
    // Backend returns: { status, message, data: { access_token, token_type, refresh_token, expires_at, client } }
    const tokenData = response.data?.data;
    
    if (!tokenData || !tokenData.access_token) {
      console.error('Auth Service: Invalid token data', response.data);
      return { 
        success: false, 
        message: 'Invalid response format from server' 
      };
    }
    
    // Store tokens: try Electron API first, then fallback to localStorage
    const isElectron = window && typeof window.electronAPI !== 'undefined';

    if (isElectron && window.electronAPI && typeof window.electronAPI.storeAuthToken === 'function') {
      try {
        await window.electronAPI.storeAuthToken({
          token: tokenData.access_token,
          refreshToken: tokenData.refresh_token,
          expiresAt: tokenData.expires_at,
          persistent: rememberMe
        });
        console.log('Auth Service: Token stored via Electron API.');
        // setUserData might still be relevant for Electron if it handles UI state not covered by main process token store
        if (tokenData.client) setUserData({ client: tokenData.client, rememberMe });
      } catch (electronError) {
        console.error('Auth Service: Failed to store token via Electron API, falling back to localStorage.', electronError);
        // Fallback to localStorage if Electron API fails
        localStorage.setItem('authToken', tokenData.access_token);
        if (tokenData.refresh_token) localStorage.setItem('refreshToken', tokenData.refresh_token);
        if (tokenData.client) setUserData({ client: tokenData.client, rememberMe }); 
      }
    } else {
      // Not in Electron or storeAuthToken not available, use localStorage
      console.log('Auth Service: Not in Electron or storeAuthToken unavailable, using localStorage.');
      localStorage.setItem('authToken', tokenData.access_token);
      if (tokenData.refresh_token) localStorage.setItem('refreshToken', tokenData.refresh_token);
      // Store user data (like client info)
      if (tokenData.client) setUserData({ client: tokenData.client, rememberMe }); 
    }
    
    console.log('Auth Service: Login successful');
    
    // Ensure authToken stored in localStorage for fallback headers
    try {
      localStorage.setItem('authToken', tokenData.access_token);
      if (tokenData.refresh_token) localStorage.setItem('refreshToken', tokenData.refresh_token);
    } catch (e) {
      console.warn('Auth Service: Failed to persist authToken to localStorage', e);
    }
    
    // Return success with client data and token info
    return {
      success: true,
      user: tokenData.client, // Note: returning as 'user' to match the expected interface in App.jsx
      accessToken: tokenData.access_token,
      refreshToken: tokenData.refresh_token,
      expiresAt: tokenData.expires_at
    };
  } catch (error) {
    console.error('Auth Service: Login error', error);
    return { 
      success: false, 
      message: error.message || 'Connection error during login'
    };
  }
}

/**
 * Register a new client
 * @param {string} username - Username for registration
 * @param {string} email - Email address
 * @param {string} password - Password
 * @returns {Promise<Object>} Registration result with success status and message
 */
export async function register(username, email, password) {
  console.log('Auth Service: Registering new client', { username, email });
  
  try {
    console.log('Auth Service: Sending registration request to API:', `${AUTH_API_URL}/register`);
    
    const response = await window.electronAPI.apiRequest({
      url: `${AUTH_API_URL}/register`,
      method: 'POST',
      body: {
        username,
        email,
        password
      },
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Auth Service: Registration response received:', response);
    
    if (!response.ok) {
      const errorMessage = response.data?.message || 
                          response.data?.detail || 
                          response.error || 
                          'Registration failed';
      console.error('Auth Service: Registration failed', errorMessage, response);
      return { 
        success: false, 
        message: errorMessage
      };
    }
    
    console.log('Auth Service: Registration successful');
    return {
      success: true,
      message: 'Registration successful. Please check your email to verify your account.'
    };
  } catch (error) {
    console.error('Auth Service: Registration error', error);
    return { 
      success: false, 
      message: error.message || 'Connection error during registration'
    };
  }
}

/**
 * Request email verification
 * @param {string} email - Email to verify
 * @returns {Promise<Object>} Result with success status and message
 */
export async function requestEmailVerification(email) {
  try {
    console.log(`Auth Service: Requesting email verification for ${email}`);
    
    // Gmail-specific recommendations check
    if (email.toLowerCase().includes('gmail.com')) {
      console.log('Auth Service: Gmail address detected - adding additional instructions');
    }
    
    let response;
    
    // Check if running in Electron or browser environment
    if (window.electronAPI && window.electronAPI.apiRequest) {
      // Electron environment
      response = await window.electronAPI.apiRequest({
        url: `${AUTH_API_URL}/resend-verification`,
        method: 'POST',
        body: { email },
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
    } else {
      // Browser environment - use fetch API
      console.log('Auth Service: Using browser fetch API for verification request');
      try {
        const fetchResponse = await fetch(`${AUTH_API_URL}/resend-verification`, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email }),
          mode: 'cors',
          credentials: 'omit', // Omit credentials to avoid CORS preflight issues
          cache: 'no-cache'
        });
        
        const data = await fetchResponse.json();
        
        response = {
          status: fetchResponse.ok ? 'success' : 'error',
          message: data.message || (fetchResponse.ok ? 'Verification email sent' : 'Failed to send verification email'),
          data: data
        };
      } catch (fetchError) {
        console.error('Auth Service: Fetch error during verification request', fetchError);
        throw new Error(fetchError.message || 'Network error during verification request');
      }
    }
    
    console.log('Auth Service: Verification request response:', response);
    
    if (response && response.status === 'success') {
      console.log('Auth Service: Verification email sent successfully');
      return {
        success: true,
        status: 'success',
        message: 'Verification email sent. Please check your inbox and spam folder.',
        additionalInfo: 'If you don\'t receive the email within a few minutes, please check your spam folder or try again.'
      };
    } else if (response && response.status === 'error') {
      console.error('Auth Service: Verification request failed with error status', response);
      return {
        success: false,
        status: 'error',
        message: response.message || 'Failed to send verification email',
        additionalInfo: 'This could be due to a server issue. Please try again later.'
      };
    }
    
    // Fallback success case
    console.log('Auth Service: Verification email sent (fallback)');
    return {
      success: true,
      status: 'success',
      message: 'Verification email sent. Please check your inbox and spam folder.',
      additionalInfo: 'If you don\'t receive the email within a few minutes, please check your spam folder or try again.'
    };
  } catch (error) {
    console.error('Auth Service: Verification request error', error);
    return { 
      success: false,
      status: 'error',
      message: error.message || 'Connection error during verification request',
      additionalInfo: 'Please check your internet connection and try again.'
    };
  }
}

/**
 * Verify email with token
 * @param {string} token - Verification token from email
 * @returns {Promise<Object>} Result with success status and message
 */
export async function verifyEmail(token) {
  console.log('Auth Service: Verifying email with token length:', token?.length);
  
  if (!token) {
    console.error('Auth Service: Empty or invalid verification token provided');
    return {
      success: false,
      message: 'Verification failed: No token provided'
    };
  }
  
  // Log the verification attempt for debugging
  console.log('Auth Service: Verification attempt with token:', {
    tokenStart: token.substring(0, 5),
    tokenEnd: token.substring(token.length - 5),
    tokenLength: token.length
  });
  
  // IMPORTANT: We need to determine if the token came from a URL hash fragment
  // Examining how the token is passed to this function - it might be from #verify/TOKEN in the URL
  const currentUrl = window.location.href;
  console.log('Auth Service: Current URL:', currentUrl);
  
  // Check if the current URL contains the verification token
  // This would suggest the user clicked a verification link directly
  const isDirectVerificationLink = currentUrl.includes(token) || 
                                 currentUrl.includes('verify') || 
                                 currentUrl.includes('verification');
  
  console.log('Auth Service: Is direct verification link:', isDirectVerificationLink);
  
  // Extract verification information from URL if possible
  let verificationInfo = {
    isFromUrl: isDirectVerificationLink,
    urlPattern: null,
    token: token.trim(),
    apiVersion: 'v1'  // Default as confirmed by user
  };
  
  // If this token came from a URL, we can extract more information
  if (isDirectVerificationLink) {
    // Check URL patterns to understand API structure
    if (currentUrl.includes('/#/verify/')) {
      verificationInfo.urlPattern = 'hash-verify-token';
    } else if (currentUrl.includes('/#verify/')) {
      verificationInfo.urlPattern = 'hash-verify-direct';
    } else if (currentUrl.includes('/verify-email')) {
      verificationInfo.urlPattern = 'path-verify-email';
    } else if (currentUrl.includes('/verify')) {
      verificationInfo.urlPattern = 'path-verify';
    }
    
    console.log('Auth Service: Verification URL pattern detected:', verificationInfo.urlPattern);
  }
  
  // Special handling for verification from email links
  // If the token came from a URL hash fragment like /#verify/TOKEN
  if (verificationInfo.urlPattern === 'hash-verify-direct' || 
      verificationInfo.urlPattern === 'hash-verify-token') {
    // The backend likely expects just the token without any URL context
    // This is common in single-page applications where the token is in the hash fragment
    console.log('Auth Service: Token appears to be from URL hash fragment, will use direct token value');
  }
  
  console.log('Auth Service: Verification information:', verificationInfo);
  
  try {
    // Initialize response variable
    let response = null;
    let responseData = null;
    
    // Check if we're in Electron environment
    if (window.electronAPI && window.electronAPI.apiRequest) {
      console.log('Auth Service: Using Electron IPC for verification');
      // Use IPC for API requests in Electron
      try {
        response = await window.electronAPI.apiRequest({
          url: `${AUTH_API_URL}/verify-email`,
          method: 'POST',
          body: { token: token.trim() },
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        });
        
        console.log('Auth Service: Electron API response:', response);
        
        if (response && response.data) {
          return {
            success: true,
            message: response.data.message || 'Email verified successfully. You can now log in.'
          };
        } else if (response && response.error) {
          throw new Error(response.error || 'Email verification failed');
        }
      } catch (electronError) {
        console.error('Auth Service: Electron API request failed:', electronError);
        throw electronError;
      }
    } else {
      // Browser environment
      console.log('Auth Service: Using browser fetch API');
      
      // Construct endpoints based on URL pattern analysis and verified v1 prefix
      
      // Define the most precise API structure based on the error patterns we've seen
      // Notice the endpoints with 404 errors are missing proper path structure
      
      // For precise debugging, log the exact API_BASE_URL
      console.log('Auth Service: API_BASE_URL =', API_BASE_URL);
      
      // Using the exact API structure from the screenshots
      const endpoints = [];
      
      // Extract just the base domain from API_BASE_URL
      const baseUrl = API_BASE_URL || 'http://localhost:8000';
      
      // For the verification endpoint (first screenshot shows /verify-email)
      endpoints.push(`${baseUrl}/api/v1/auth/verify-email`);
      
      // If we're in a testing environment, also include the localhost endpoint
      if (baseUrl !== 'http://localhost:8000') {
        endpoints.push('http://localhost:8000/api/v1/auth/verify-email');
      }
      
      console.log('Auth Service: Using exact API pattern: /api/v1/auth/verify-email');
      
      // Make sure we don't have duplicates
      const uniqueEndpoints = [...new Set(endpoints)];
      
      // For each endpoint, log the full URL to help debugging
      console.log('Auth Service: Attempting verification with these endpoints:');
      endpoints.forEach(endpoint => console.log(` - ${endpoint}`));
      
      console.log('Auth Service: Attempting verification with these endpoints:', endpoints);
      
      // Try each endpoint in sequence until one works
      let lastError = null;
      
      for (const endpoint of endpoints) {
        let response;
        try {
          console.log(`Auth Service: Trying verification endpoint: ${endpoint}`);
          
          // Based on the screenshots showing POST requests to /api/v1/auth/verify-email
          response = await fetch(endpoint, {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
              token: verificationInfo.token.trim()
            }),
            mode: 'cors',
            credentials: 'omit',  // Avoid CORS issues
            cache: 'no-cache'
          });
          
          console.log(`Auth Service: POST request to ${endpoint} returned status: ${response.status}`);
          
          // Get response data if possible
          let data = null;
          try {
            if (response.status !== 204) { // No Content
              data = await response.json();
            }
          } catch (jsonError) {
            console.log('Auth Service: Error parsing response JSON:', jsonError);
            // Continue without JSON data
          }
          
          console.log(`Auth Service: Response details:`, {
            endpoint,
            status: response.status,
            statusText: response.statusText,
            data: data
          });
          
          // SUCCESS CASE 1: Standard success response
          if (response.status === 200 || response.status === 204) {
            console.log('Auth Service: Email verification successful');
            return {
              success: true,
              message: data?.message || 'Email verified successfully. You can now log in.'
            };
          }
          
          // SUCCESS CASE 2: Token already used (technically a 400, but a success for user)
          if (response.status === 400 && data?.message && 
              (data.message.toLowerCase().includes('token already used') || 
               data.message.toLowerCase().includes('already verified'))) {
            
            console.log('Auth Service: Token already used - treating as success');
            return {
              success: true,
              alreadyVerified: true,
              message: 'Email already verified. You can now log in.'
            };
          }
          
          // For other error responses, try next endpoint
          if (data?.message) {
            lastError = new Error(data.message);
          } else {
            lastError = new Error(`Error ${response.status}: ${response.statusText}`);
          }
          
        } catch (fetchError) {
          // Connection errors, network issues, CORS, etc.
          console.warn(`Auth Service: Fetch error for ${endpoint}:`, fetchError);
          lastError = fetchError;
          // Continue to next endpoint
        }
      }
      
      // At this point we've tried all endpoints and none worked
      console.error('Auth Service: All verification endpoints failed');
      
      // Special case check - see if any of the errors indicate "already verified"
      if (lastError && lastError.message && 
          (lastError.message.toLowerCase().includes('already used') || 
           lastError.message.toLowerCase().includes('already verified'))) {
        return {
          success: true,
          alreadyVerified: true,
          message: 'Email already verified. You can now log in.'
        };
      }
      
      // Otherwise throw the error
      throw new Error(lastError?.message || 'Email verification failed. Unable to connect to verification service.');
    }
    
    // Default success case
    return {
      success: true,
      message: 'Email verified successfully. You can now log in to your account.'
    };
  } catch (error) {
    console.error('Auth Service: Email verification error', error);
    return { 
      success: false, 
      message: error.message || 'Connection error during email verification'
    };
  }
}

/**
 * Request password reset
 * @param {string} email - Email to send reset link to
 * @returns {Promise<Object>} Result with success status and message
 */
export async function requestPasswordReset(email) {
  try {
    console.log('Auth Service: Requesting password reset for', email);
    
    // Basic email validation before sending request
    if (!email || !email.includes('@') || !email.includes('.')) {
      console.error('Auth Service: Invalid email format provided');
      return {
        success: false,
        status: 'error',
        message: 'Please enter a valid email address',
        additionalInfo: 'The email address format is invalid.'
      };
    }
    
    // Gmail-specific recommendations check
    if (email.toLowerCase().includes('gmail.com')) {
      console.log('Auth Service: Gmail address detected - adding additional instructions');
    }
    
    const response = await window.electronAPI.apiRequest({
      url: `${AUTH_API_URL}/forgot-password`,
      method: 'POST',
      body: { email },
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Auth Service: Password reset response received:', response);
    
    // Check for user not found errors
    if (response?.data?.detail?.toLowerCase().includes('not found') ||
        response?.data?.message?.toLowerCase().includes('not found') ||
        response?.error?.toLowerCase().includes('not found') ||
        response?.status === 404) {
      console.error('Auth Service: Email not found in database');
      return {
        success: false,
        status: 'error',
        message: 'No account found with this email address',
        additionalInfo: 'Please check the email address or create a new account.'
      };
    }
    
    // Fix: check the actual response data status, not just HTTP status
    // Many APIs return HTTP 200 but indicate error in the response body
    if (response && response.data && response.data.status === 'success') {
      // The backend returns success when email was sent
      console.log('Auth Service: Password reset email sent successfully');
      
      return {
        success: true,
        status: 'success',
        message: 'Password reset email sent. Please check your inbox and spam folder.',
        additionalInfo: 'If you don\'t receive the email within a few minutes, please check your spam folder or try again.'
      };
    } else if (response && response.data) {
      // The backend returns error with details about what went wrong
      console.log('Auth Service: Password reset request failed', response?.data?.message);
      
      // Check if the error is about account not existing
      const responseMsg = response?.data?.message || '';
      if (responseMsg.includes('No account found') || responseMsg.includes('not found')) {
        return {
          success: false,
          status: 'error',
          message: `No account found with this email address`,
          additionalInfo: 'Please check the email address or create a new account.'
        };
      }
      
      // Other errors
      return {
        success: false,
        status: 'error',
        message: response?.data?.message || 'Failed to send password reset email',
        additionalInfo: 'The server responded with an error. Please try again later.'
      };
    }
    
    // Fallback for ambiguous or unexpected response formats
    // This helps handle backend security measures that might return success even for non-existent emails
    console.log('Auth Service: Password reset email sent (fallback)');
    return {
      success: true,
      status: 'success', 
      message: 'If the email exists, a password reset link will be sent.',
      additionalInfo: 'Please check both your inbox and spam folder. If you don\'t receive an email within 15 minutes, verify that you entered the correct email address or try another recovery method.'
    };
  } catch (error) {
    console.error('Auth Service: Password reset request error', error);
    return { 
      success: false,
      status: 'error',
      message: error.message || 'Connection error during password reset request',
      additionalInfo: 'Please check your internet connection and try again.'
    };
  }
}

/**
 * Reset password with token
 * @param {string} token - Reset token from email
 * @param {string} newPassword - New password
 * @returns {Promise<Object>} Result with success status and message
 */
export async function resetPassword(token, newPassword) {
  console.log('Auth Service: Resetting password with token', { tokenLength: token ? token.length : 0 });
  
  // Make sure the token is valid
  if (!token || token.trim() === '') {
    console.error('Auth Service: Invalid reset token provided');
    return { 
      success: false, 
      message: 'Invalid password reset token. Please request a new reset link.'
    };
  }
  
  try {
    // Clean the token in case it has any unwanted characters
    const cleanToken = token.trim();
    
    console.log('Auth Service: Sending password reset with token to API:', `${AUTH_API_URL}/reset-password`);
    console.log('Token prefix:', cleanToken.substring(0, 5) + '...');
    console.log('Password length:', newPassword.length);
    
    // Formatting payload exactly as expected by backend API
    // Using 'new_password' with underscore to match Pydantic model in backend
    const payload = {
      token: cleanToken,
      new_password: newPassword  // Ensure this matches the backend schema (PasswordResetConfirm)
    };
    
    console.log('Auth Service: Request payload structure:', Object.keys(payload).join(', '));
    
    let response;
    
    // Check if we're in Electron or browser environment
    if (typeof window.electronAPI !== 'undefined') {
      console.log('Auth Service: Using Electron IPC bridge for API request');
      // We're in Electron app
      response = await window.electronAPI.apiRequest({
        url: `${AUTH_API_URL}/reset-password`,
        method: 'POST',
        body: payload,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
    } else {
      console.log('Auth Service: Using browser fetch API for direct request');
      // We're in a browser - use fetch API directly
      try {
        const fetchResponse = await fetch(`${AUTH_API_URL}/reset-password`, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });
        
        const responseData = await fetchResponse.json();
        
        // Format response to match Electron's format
        response = {
          ok: fetchResponse.ok,
          status: fetchResponse.status,
          data: responseData,
          headers: Object.fromEntries([...fetchResponse.headers.entries()])
        };
        
        console.log('Auth Service: Browser fetch response:', response);
      } catch (fetchError) {
        console.error('Auth Service: Browser fetch error:', fetchError);
        return { 
          success: false, 
          message: `Connection error: ${fetchError.message}`,
          isConnectionError: true
        };
      }
    }
    
    // Detailed response logging for debugging
    console.log('Auth Service: Password reset response status:', response.status, response.ok);
    console.log('Auth Service: Response data:', JSON.stringify(response.data || {}));
    
    // Process response
    if (response.ok) {
      console.log('Auth Service: Password reset successful');
      
      // Track token as used in local storage to prevent reuse with timestamp
      try {
        // Try to load existing tokens - supporting both old format (array) and new format (object with timestamps)
        const storedData = localStorage.getItem('used_reset_tokens');
        let usedTokens = {};
        
        if (storedData) {
          const parsedData = JSON.parse(storedData);
          // Convert old format to new if needed
          if (Array.isArray(parsedData)) {
            parsedData.forEach(t => { usedTokens[t] = new Date().toISOString(); });
          } else {
            usedTokens = parsedData;
          }
        }
        
        // Add the current token with timestamp
        if (!usedTokens[token]) {
          usedTokens[token] = new Date().toISOString();
          localStorage.setItem('used_reset_tokens', JSON.stringify(usedTokens));
        }
        console.log('Auth Service: Marked token as used with timestamp');
      } catch (storageErr) {
        console.warn('Auth Service: Could not mark token as used:', storageErr);
      }
      
      return { 
        success: true, 
        message: 'Your password has been reset successfully. You can now log in with your new password.',
        data: response.data,
        // Don't mark as expired on success since this causes confusion
        tokenExpired: false
      };
    } else {
      const statusCode = response.status || 500;
      let errorMessage = 'An error occurred during password reset';
      let isTokenExpired = false;
      
      // Better error detection for token issues
      if (response.data && (response.data.detail || response.data.message)) {
        errorMessage = response.data.detail || response.data.message;
        
        // Only mark as expired if explicitly mentioned in the error
        isTokenExpired = /expired|invalid token|already used/i.test(errorMessage);
        
        // Provide clearer error messages based on the issue type
        if (isTokenExpired && /expired/i.test(errorMessage)) {
          errorMessage = 'This password reset link has expired. Please request a new link from the login page.';
        } else if (isTokenExpired && /already used/i.test(errorMessage)) {
          errorMessage = 'This password reset link has already been used. For security reasons, each reset link can only be used once.';
        } else if (isTokenExpired) {
          errorMessage = 'This password reset link is no longer valid. Please request a new link.';
        }
      }
      
      // Check local storage for used tokens
      try {
        const storedData = localStorage.getItem('used_reset_tokens');
        if (storedData) {
          const parsedData = JSON.parse(storedData);
          
          // Check if token exists in either array format or object format
          const isUsed = Array.isArray(parsedData) 
            ? parsedData.includes(token)
            : Object.prototype.hasOwnProperty.call(parsedData, token);
          
          if (isUsed) {
            errorMessage = 'This reset link has already been used. For security reasons, password reset links can only be used once.';
            isTokenExpired = true;
            
            // Get timestamp if available
            if (!Array.isArray(parsedData) && parsedData[token]) {
              try {
                const usedDate = new Date(parsedData[token]);
                const formattedDate = usedDate.toLocaleDateString();
                const formattedTime = usedDate.toLocaleTimeString();
                errorMessage = `This reset link was already used on ${formattedDate} at ${formattedTime}. Please request a new link.`;
              } catch (dateError) {
                console.warn('Auth Service: Error formatting used token date', dateError);
              }
            }
          }
        }
      } catch (e) {
        console.warn('Auth Service: Error checking local used tokens', e);
      }
      
      console.log('Auth Service: Password reset failed with message:', errorMessage);
      
      return { 
        success: false, 
        message: errorMessage,
        status: statusCode,
        tokenExpired: isTokenExpired
      };
    }
    // No need for this duplicate return - already handled above
  } catch (err) {
    console.error('Auth Service: Password reset error', err);
    // Provide more helpful error message for connection issues
    const errorMessage = err.message || 'An unexpected error occurred during password reset';
    const isConnectionIssue = /network|fetch|connection|timeout/i.test(errorMessage);
    
    return { 
      success: false, 
      message: isConnectionIssue 
        ? 'Unable to connect to the server. Please check your internet connection and try again.' 
        : errorMessage,
      isConnectionError: true
    };
  }
}

/**
 * Refresh the access token using a refresh token
 * @returns {Promise<Object>} Result with new tokens or error
 */
export async function refreshToken() {
  console.log('Auth Service: Refreshing access token');
  
  try {
    // Get the refresh token from storage
    const { refreshToken } = await window.electronAPI.getAuthToken();
    
    if (!refreshToken) {
      console.error('Auth Service: No refresh token available');
      return { 
        success: false, 
        message: 'No refresh token available'
      };
    }
    
    const response = await window.electronAPI.apiRequest({
      url: `${AUTH_API_URL}/refresh`,
      method: 'POST',
      body: { refresh_token: refreshToken }
    });
    
    if (!response.ok) {
      console.error('Auth Service: Token refresh failed', response.data);
      // Clear tokens as they are invalid
      await window.electronAPI.clearAuthToken();
      return { 
        success: false, 
        message: 'Failed to refresh token. Please log in again.'
      };
    }
    
    const tokenData = response.data?.data;
    
    if (!tokenData || !tokenData.access_token) {
      console.error('Auth Service: Invalid token refresh data', response.data);
      return { 
        success: false, 
        message: 'Invalid response format from server' 
      };
    }
    
    // Store the new tokens
    await window.electronAPI.storeAuthToken({
      token: tokenData.access_token,
      refreshToken: tokenData.refresh_token,
      expiresAt: tokenData.expires_at
    });
    
    console.log('Auth Service: Token refresh successful');
    return {
      success: true,
      accessToken: tokenData.access_token,
      refreshToken: tokenData.refresh_token,
      expiresAt: tokenData.expires_at
    };
  } catch (error) {
    console.error('Auth Service: Token refresh error', error);
    return { 
      success: false, 
      message: error.message || 'Connection error during token refresh'
    };
  }
}

/**
 * Get the current authenticated client's profile
 * @returns {Promise<Object|null>} Client data or null if not authenticated
 */
export async function getCurrentUser() {
  console.log('Auth Service: Fetching current user profile');
  
  try {
    // First check if we have a token
    const isAuth = await checkAuth();
    if (!isAuth) {
      console.log('Auth Service: No auth token available');
      return null;
    }
    
    // Call the /me endpoint to get client profile
    const response = await window.electronAPI.apiRequest({
      url: `${AUTH_API_URL}/me`,
      method: 'GET'
    });
    
    if (!response.ok) {
      // If we get a 401 Unauthorized, our token might be expired
      if (response.status === 401) {
        console.log('Auth Service: Token expired, attempting refresh');
        const refreshResult = await refreshToken();
        
        if (refreshResult.success) {
          // Try again with the new token
          const retryResponse = await window.electronAPI.apiRequest({
            url: `${AUTH_API_URL}/me`,
            method: 'GET'
          });
          
          if (retryResponse.ok) {
            console.log('Auth Service: User profile retrieved after token refresh');
            return retryResponse.data?.data;
          }
        }
        
        // If we reach here, refresh failed or retry failed
        console.error('Auth Service: Failed to refresh token and retry');
        return null;
      }
      
      console.error('Auth Service: Failed to get user profile', response.data);
      return null;
    }
    
    const userData = response.data?.data;
    console.log('Auth Service: User profile retrieved successfully');
    return userData;
  } catch (error) {
    console.error('Auth Service: Error requesting user profile:', error);
    
    // Enhanced error handling with more detailed information
    const errorMessage = error.response?.data?.message || error.message || 'Unknown error';
    const statusCode = error.response?.status || 'No status';
    console.error(`Auth Service: User profile request failed - ${statusCode}: ${errorMessage}`);
    
    // Rethrow with more context
    throw {
      ...error,
      friendlyMessage: 'Unable to retrieve user profile. Please try again later.',
      details: {
        endpoint: `${AUTH_API_URL}/me`,
        statusCode,
        serverMessage: errorMessage
      }
    };
  }
}

// Function to get the API token, aware of Electron environment
export async function getApiToken() {
  try {
    // Check if we're in Electron environment
    const isElectron = window && typeof window.electronAPI !== 'undefined';
    
    if (isElectron && window.electronAPI && window.electronAPI.getAuthToken) {
      // In Electron app
      console.log('Auth Service (getApiToken Electron): Calling window.electronAPI.getAuthToken()');
      const authData = await window.electronAPI.getAuthToken(); 
      console.log('Auth Service (getApiToken Electron): Received authData:', authData);
      let token = null;
      if (typeof authData === 'string') {
        token = authData; // authData is the token string itself
      } else if (authData && typeof authData.token === 'string') {
        token = authData.token; // authData is an object with a token property
      }
      console.log('Auth Service (getApiToken Electron): Returning token:', token);
      return token;
    } else {
      // In browser or if electronAPI is not configured for this
      const token = localStorage.getItem('authToken');
      console.log('Auth Service (getApiToken localStorage): Returning token:', token);
      return token;
    }
  } catch (error) {
    console.error('Auth Service (getApiToken): Error retrieving token:', error);
    return null; // Return null on error to indicate failure
  }
}

/**
 * Provides auth headers for API calls, reading token from storage-service or fallback to localStorage 'authToken'.
 */
export async function getAuthHeaders() {
  const userData = getUserData() || {};
  const token = userData.token || localStorage.getItem('authToken');
  console.log('getAuthHeaders token →', token);
  return {
    Authorization: token ? `Bearer ${token}` : ''
  };
}

/**
 * Check if user is currently authenticated
 * @returns {Promise<boolean>} Authentication status
 */
export async function checkAuth() {
  try {
    // Check if we're in Electron environment
    const isElectron = window && typeof window.electronAPI !== 'undefined';
    
    // Get token from secure storage in main process if in Electron
    // Otherwise, get from localStorage
    let token, expiresAt;
    
    if (isElectron && window.electronAPI && window.electronAPI.getAuthToken) {
      // In Electron app
      const authData = await window.electronAPI.getAuthToken() || {};
      token = authData.token;
      expiresAt = authData.expiresAt;
    } else {
      // In browser
      token = localStorage.getItem('authToken');
      expiresAt = localStorage.getItem('tokenExpiry');
    }
    
    if (!token) {
      console.log('Auth Service: No authentication token found');
      return false;
    }
    
    // Check if token is expired
    if (expiresAt) {
      const now = new Date();
      const expiry = new Date(expiresAt);
      
      if (now >= expiry) {
        console.log('Auth Service: Token expired, attempting refresh');
        const refreshResult = await refreshToken();
        return refreshResult.success;
      }
    }
    
    return true;
  } catch (error) {
    console.error('Auth Service: Error checking auth status', error);
    return false;
  }
}

/**
 * Log out the current user
 * @returns {Promise<Object>} Logout result
 */
export async function logout() {
  console.log('Auth Service: Logging out');
  
  try {
    // Get the refresh token before clearing
    const { refreshToken } = await window.electronAPI.getAuthToken() || {};
    
    // Clear tokens in local storage
    await window.electronAPI.clearAuthToken();
    
    // If we have a refresh token, invalidate it on the server
    if (refreshToken) {
      try {
        await window.electronAPI.apiRequest({
          url: `${AUTH_API_URL}/logout`,
          method: 'POST',
          body: { refresh_token: refreshToken }
        });
        console.log('Auth Service: Server-side logout successful');
      } catch (logoutError) {
        // Even if server logout fails, we've cleared the local tokens
        console.warn('Auth Service: Server-side logout failed, but local tokens cleared', logoutError);
      }
    }
    
    console.log('Auth Service: Logout successful');
    return { success: true };
  } catch (error) {
    console.error('Auth Service: Logout error', error);
    // Still consider it a successful logout if we cleared the tokens locally
    await window.electronAPI.clearAuthToken();
    return { 
      success: true,
      message: 'Logged out locally, but encountered an error: ' + (error.message || 'Unknown error')
    };
  }
}
