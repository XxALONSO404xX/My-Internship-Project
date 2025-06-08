import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import Button from './Button';

/**
 * Modal component: overlays screen with content container
 * Props:
 *  - isOpen: boolean to show/hide
 *  - onClose: function to call when closing
 *  - title: modal title
 *  - children: modal body
 */
const Modal = ({ isOpen, onClose, title, children }) => {
  useEffect(() => {
    const handleEscape = e => { if (e.key === 'Escape') onClose(); };
    if (isOpen) {
      document.body.classList.add('overflow-hidden');
      window.addEventListener('keydown', handleEscape);
    }
    return () => {
      document.body.classList.remove('overflow-hidden');
      window.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden max-w-lg w-full z-10 p-6 animate-fadeIn">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
          <Button variant="secondary" size="sm" onClick={onClose}>Close</Button>
        </div>
        <div>{children}</div>
      </div>
    </div>,
    document.body
  );
};

export default Modal;
