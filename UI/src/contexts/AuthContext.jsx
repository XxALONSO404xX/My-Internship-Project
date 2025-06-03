import React, { createContext, useState, useEffect, useCallback } from 'react';
import { 
  login as authLogin, 
  logout as authLogout, 
  register as authRegister,
  checkAuth, 
  getCurrentUser,
  requestEmailVerification as requestVerification,
  verifyEmail,
  requestPasswordReset,
  resetPassword,
  refreshToken 
} from '../services/auth-service';

// Create the AuthContext with named export to match App.jsx import expectations
export const AuthContext = createContext();

/**
 * Authentication Provider Component
 * Manages authentication state and provides auth functions
 */
export function AuthProvider({ children }) {
  // Authentication state
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState(null);
  const [verificationNeeded, setVerificationNeeded] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState('');

  // Clear error helper function
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Reset verification state
  const clearVerificationState = useCallback(() => {
    setVerificationNeeded(false);
    setVerificationEmail('');
  }, []);

  // Check authentication status on component mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      setLoading(true);
      try {
        console.log('AuthContext: Checking authentication status');
        const isAuth = await checkAuth();
        
        if (isAuth) {
          console.log('AuthContext: Token found, fetching user profile');
          const userData = await getCurrentUser();
          
          if (userData) {
            setUser(userData);
            setIsAuthenticated(true);
            console.log('AuthContext: Authentication successful', userData);
          } else {
            // We have a token but couldn't get the user data - possibly an expired token
            console.log('AuthContext: Invalid token, logging out');
            await authLogout();
            setUser(null);
            setIsAuthenticated(false);
          }
        } else {
          console.log('AuthContext: No authentication token found');
          setUser(null);
          setIsAuthenticated(false);
        }
      } catch (err) {
        console.error('AuthContext: Error during authentication check', err);
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  /**
   * Login function
   * @param {string} username - Username for login
   * @param {string} password - Password for login
   * @param {boolean} rememberMe - Whether to persist the session
   * @returns {Promise<{success: boolean, message?: string, requiresVerification?: boolean}>}
   */
  const login = useCallback(async (username, password, rememberMe = false) => {
    // Validate inputs
    if (!username || !password) {
      setError('Username and password are required');
      return { success: false, message: 'Username and password are required' };
    }

    setLoading(true);
    clearError();
    clearVerificationState();

    try {
      console.log('AuthContext: Attempting login for', username);
      const result = await authLogin(username, password, rememberMe);

      if (result.success) {
        setUser(result.user);
        setIsAuthenticated(true);
        console.log('AuthContext: Login successful');
        return { success: true };
      } else {
        // Check if account needs verification
        if (result.requiresVerification) {
          setVerificationNeeded(true);
          setVerificationEmail(result.email || username);
          setError(result.message);
          console.warn('AuthContext: Account requires verification', result.message);
          return { 
            success: false, 
            message: result.message, 
            requiresVerification: true,
            email: result.email || username
          };
        }
        
        setError(result.message);
        console.error('AuthContext: Login failed', result.message);
        return { success: false, message: result.message };
      }
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      console.error('AuthContext: Login error', err);
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  }, [clearError, clearVerificationState]);

  /**
   * Register a new user
   * @param {string} username - Username for registration
   * @param {string} email - Email address
   * @param {string} password - Password
   * @returns {Promise<{success: boolean, message?: string}>}
   */
  const register = useCallback(async (username, email, password) => {
    // Validate inputs
    if (!username || !email || !password) {
      setError('All fields are required');
      return { success: false, message: 'All fields are required' };
    }

    setLoading(true);
    clearError();

    try {
      console.log('AuthContext: Registering new user', { username, email });
      const result = await authRegister(username, email, password);

      if (result.success) {
        console.log('AuthContext: Registration successful');
        // Set verification needed flag to true
        setVerificationNeeded(true);
        setVerificationEmail(email);
        return { success: true, message: result.message };
      } else {
        setError(result.message);
        console.error('AuthContext: Registration failed', result.message);
        return { success: false, message: result.message };
      }
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      console.error('AuthContext: Registration error', err);
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  }, [clearError]);

  /**
   * Request email verification
   * @param {string} email - Email to verify
   * @returns {Promise<{success: boolean, message?: string}>}
   */
  const sendVerificationEmail = useCallback(async (email) => {
    if (!email) {
      setError('Email is required');
      return { success: false, message: 'Email is required' };
    }

    setLoading(true);
    clearError();

    try {
      console.log('AuthContext: Requesting verification email for', email);
      const result = await requestVerification(email);

      if (result.success) {
        console.log('AuthContext: Verification email sent');
        return { success: true, message: result.message };
      } else {
        setError(result.message);
        console.error('AuthContext: Failed to send verification email', result.message);
        return { success: false, message: result.message };
      }
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      console.error('AuthContext: Error sending verification email', err);
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  }, [clearError]);

  /**
   * Verify email with token
   * @param {string} token - Verification token from email
   * @returns {Promise<{success: boolean, message?: string}>}
   */
  const verifyAccount = useCallback(async (token) => {
    if (!token) {
      setError('Verification token is required');
      return { success: false, message: 'Verification token is required' };
    }

    setLoading(true);
    clearError();

    try {
      console.log('AuthContext: Verifying account with token');
      const result = await verifyEmail(token);

      if (result.success) {
        console.log('AuthContext: Account verification successful');
        setVerificationNeeded(false);
        setVerificationEmail('');
        return { success: true, message: result.message };
      } else {
        setError(result.message);
        console.error('AuthContext: Account verification failed', result.message);
        return { success: false, message: result.message };
      }
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      console.error('AuthContext: Error verifying account', err);
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  }, [clearError]);

  /**
   * Request password reset
   * @param {string} email - Email for password reset
   * @returns {Promise<{success: boolean, message?: string}>}
   */
  const forgotPassword = useCallback(async (email) => {
    if (!email) {
      setError('Email is required');
      return { success: false, message: 'Email is required' };
    }

    setLoading(true);
    clearError();

    try {
      console.log('AuthContext: Requesting password reset for', email);
      const result = await requestPasswordReset(email);

      if (result.success) {
        console.log('AuthContext: Password reset email sent');
        return { success: true, message: result.message };
      } else {
        setError(result.message);
        console.error('AuthContext: Failed to send password reset email', result.message);
        return { success: false, message: result.message };
      }
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      console.error('AuthContext: Error sending password reset email', err);
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  }, [clearError]);

  /**
   * Reset password with token
   * @param {string} token - Reset token from email
   * @param {string} newPassword - New password
   * @returns {Promise<{success: boolean, message?: string, data?: any}>}
   */
  const resetUserPassword = useCallback(async (token, newPassword) => {
    if (!token || !newPassword) {
      setError('Token and new password are required');
      return { success: false, message: 'Token and new password are required' };
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return { success: false, message: 'Password must be at least 8 characters long' };
    }

    setLoading(true);
    clearError();

    try {
      // Log the token format for debugging
      console.log('AuthContext: Resetting password with token format:', 
                  token ? `${token.substring(0, 5)}...${token.slice(-5)} (${token.length} chars)` : 'Invalid token');
      
      // Call the service function with proper token formatting
      const result = await resetPassword(token, newPassword);
      console.log('AuthContext: Password reset API result:', JSON.stringify(result));

      if (result.success) {
        console.log('AuthContext: Password reset successful');
        // For successful reset, don't set any error
        clearError();
        return { 
          success: true, 
          message: result.message || 'Password reset successful. You can now log in with your new password.',
          data: result.data
        };
      } else {
        // Handle different types of errors
        let errorMsg = result.message;
        
        if (result.isConnectionError) {
          errorMsg = 'Could not connect to server. Please check your internet connection and try again.';
        } else if (result.statusCode === 401 || result.statusCode === 403) {
          errorMsg = 'Authorization failed. Your reset link may have expired.';
        } else if (result.statusCode === 400) {
          errorMsg = result.message || 'Invalid request. Please check your password and try again.';
        } else if (result.statusCode === 404) {
          errorMsg = 'Reset endpoint not found. Please contact support.';
        }
        
        setError(errorMsg);
        console.error('AuthContext: Password reset failed', errorMsg);
        return { success: false, message: errorMsg, statusCode: result.statusCode };
      }
    } catch (err) {
      const errorMessage = err.message || 'An unexpected error occurred';
      setError(errorMessage);
      console.error('AuthContext: Error resetting password', err);
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  }, [clearError]);

  /**
   * Logout function
   * @returns {Promise<void>}
   */
  const logout = useCallback(async () => {
    setLoading(true);
    
    try {
      console.log('AuthContext: Logging out');
      await authLogout();
      
      // Reset auth state
      setUser(null);
      setIsAuthenticated(false);
      clearError();
      clearVerificationState();
      
      console.log('AuthContext: Logout complete');
    } catch (err) {
      console.error('AuthContext: Logout error', err);
      // Still reset auth state even if logout API call fails
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  }, [clearError, clearVerificationState]);

  /**
   * Refresh the auth token
   * @returns {Promise<{success: boolean}>}
   */
  const refreshAuthToken = useCallback(async () => {
    try {
      console.log('AuthContext: Refreshing auth token');
      const result = await refreshToken();

      if (result.success) {
        console.log('AuthContext: Token refresh successful');
        return { success: true };
      } else {
        console.error('AuthContext: Token refresh failed', result.message);
        // If token refresh fails, log the user out
        await logout();
        return { success: false, message: result.message };
      }
    } catch (err) {
      console.error('AuthContext: Error refreshing token', err);
      await logout();
      return { success: false, message: err.message };
    }
  }, [logout]);

  // Context value that will be provided to consumers
  const value = {
    // State
    user,
    loading,
    isAuthenticated,
    error,
    verificationNeeded,
    verificationEmail,
    
    // Auth functions
    login,
    logout,
    register,
    sendVerificationEmail,
    verifyAccount,
    forgotPassword,
    resetUserPassword,
    refreshAuthToken,
    clearError,
    clearVerificationState
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
