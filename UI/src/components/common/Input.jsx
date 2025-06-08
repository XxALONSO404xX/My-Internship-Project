import React from 'react';

/**
 * Reusable Input component with label and error handling
 */
const Input = ({
  label,
  value,
  onChange,
  type = 'text',
  placeholder = '',
  error = '',
  className = '',
  ...props
}) => (
  <div className={`flex flex-col ${className}`}>
    {label && (
      <label className="mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
    )}
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition ${
        error ? 'border-danger' : 'border-gray-300 dark:border-gray-600'
      }`}
      {...props}
    />
    {error && (
      <span className="mt-1 text-sm text-danger">
        {error}
      </span>
    )}
  </div>
);

export default Input;
