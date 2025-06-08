import React from 'react';

const VARIANT_CLASSES = {
  online: 'bg-device-online text-white',
  offline: 'bg-device-offline text-white',
  info: 'bg-primary text-white',
  warning: 'bg-warning text-gray-800',
  danger: 'bg-danger text-white',
};

/**
 * Badge component for status indicators
 * variant: online|offline|info|warning|danger
 */
const Badge = ({ children, variant = 'info', className = '' }) => (
  <span
    className={`inline-block px-2 py-1 text-xs font-semibold rounded ${VARIANT_CLASSES[variant] || VARIANT_CLASSES.info} ${className}`}
  >
    {children}
  </span>
);

export default Badge;
