import React from 'react';

/**
 * Card component for grouping content
 */
const Card = ({ children, className = '', ...props }) => (
  <div className={`bg-white dark:bg-gray-800 shadow rounded-md p-4 ${className}`} {...props}>
    {children}
  </div>
);

export default Card;
