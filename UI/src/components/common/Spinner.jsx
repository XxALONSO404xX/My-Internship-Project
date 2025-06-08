import React from 'react';

/**
 * Full-page overlay spinner
 */
const Spinner = () => (
  <div className="fixed inset-0 flex items-center justify-center bg-white bg-opacity-75 dark:bg-gray-900 dark:bg-opacity-75 z-50">
    <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-primary"></div>
  </div>
);

export default Spinner;
