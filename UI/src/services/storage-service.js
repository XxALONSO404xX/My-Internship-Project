/**
 * Storage Service for IoT Platform
 * Handles local storage operations for persisting user authentication data
 */

// Storage key constants
const USER_DATA_KEY = 'iot_platform_user_data';

/**
 * Set user data in local storage
 * @param {Object} userData - User data to store
 */
export function setUserData(userData) {
  try {
    if (!userData) {
      console.warn('Storage Service: Attempting to store undefined or null user data');
      return;
    }
    
    // Store stringified user data
    const userDataString = JSON.stringify(userData);
    localStorage.setItem(USER_DATA_KEY, userDataString);
    
    console.log('Storage Service: User data stored successfully');
  } catch (error) {
    console.error('Storage Service: Error storing user data', error);
  }
}

/**
 * Get user data from local storage
 * @returns {Object|null} User data object or null if not found
 */
export function getUserData() {
  try {
    const userDataString = localStorage.getItem(USER_DATA_KEY);
    
    if (!userDataString) {
      return null;
    }
    
    return JSON.parse(userDataString);
  } catch (error) {
    console.error('Storage Service: Error retrieving user data', error);
    return null;
  }
}

/**
 * Clear user data from local storage
 */
export function clearUserData() {
  try {
    localStorage.removeItem(USER_DATA_KEY);
    console.log('Storage Service: User data cleared successfully');
  } catch (error) {
    console.error('Storage Service: Error clearing user data', error);
  }
}

/**
 * Check if user is logged in based on stored data
 * @returns {boolean} True if user is logged in
 */
export function isUserLoggedIn() {
  const userData = getUserData();
  return !!userData && !!userData.token;
}

// Export the storage key for testing or direct access if needed
export const STORAGE_KEYS = {
  USER_DATA: USER_DATA_KEY
};
