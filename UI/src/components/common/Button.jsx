import React from 'react';

const VARIANT_CLASSES = {
  primary: 'bg-primary text-white hover:bg-primary/90',
  secondary: 'bg-secondary text-white hover:bg-secondary/90',
  danger: 'bg-danger text-white hover:bg-danger/90',
  warning: 'bg-warning text-gray-800 hover:bg-warning/90',
  success: 'bg-success text-white hover:bg-success/90',
};

const SIZE_CLASSES = {
  sm: 'px-3 py-1 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-5 py-3 text-lg',
};

/**
 * Reusable Button component
 * variant: primary|secondary|danger|warning|success
 * size: sm|md|lg
 */
const Button = ({ children, variant = 'primary', size = 'md', disabled = false, className = '', ...props }) => {
  return (
    <button
      className={`rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 transition ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;
