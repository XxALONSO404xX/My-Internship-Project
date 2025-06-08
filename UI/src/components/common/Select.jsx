import React from 'react';

/**
 * Reusable Select component
 * props:
 * - label: optional label text
 * - options: array of { value, label }
 * - value: selected value
 * - onChange: function(e) or function(value)
 */
const Select = ({ label, options = [], value, onChange, className = '', ...props }) => (
  <div className={`flex flex-col ${className}`}> 
    {label && <label className="mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>}
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition"
      {...props}
    >
      {options.map(opt => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  </div>
);

export default Select;
