import React, { useState, useRef, useEffect } from 'react';
import { trackEvent } from '../../services/analytics-service';

const MIN_WIDTH = 96; // collapse threshold matches w-24 (96px)
const MAX_WIDTH = 384; // 96 * 4px (w-96)

const Sidebar = ({ activeTab, onTabChange, user, onLogout }) => {
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(256); // Default: w-64 (64 * 4px)
  const sidebarRef = useRef(null);

  const startResizing = React.useCallback((e) => {
    setIsResizing(true);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const stopResizing = React.useCallback(() => {
    setIsResizing(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  const resize = React.useCallback(
    (e) => {
      if (isResizing && sidebarRef.current) {
        const newWidth = e.clientX - sidebarRef.current.getBoundingClientRect().left;
        if (newWidth >= MIN_WIDTH && newWidth <= MAX_WIDTH) {
          setSidebarWidth(newWidth);
        }
      }
    },
    [isResizing]
  );

  useEffect(() => {
    window.addEventListener('mousemove', resize);
    window.addEventListener('mouseup', stopResizing);
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [resize, stopResizing]);

  const tabs = [
    { id: 'home', label: 'Home', icon: 'home' },
    { id: 'network', label: 'Network', icon: 'device' },
    { id: 'devices', label: 'Devices', icon: 'device' },
    { id: 'security', label: 'Security', icon: 'shield' },
    { id: 'firmware', label: 'Firmware', icon: 'download' },
    { id: 'groups', label: 'Groups', icon: 'device' },
    { id: 'clients', label: 'Clients', icon: 'device' },
    { id: 'rules', label: 'Rules', icon: 'clipboard-list' },
  ];

  return (
    <>
      <aside 
        ref={sidebarRef}
        className="relative h-screen bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 pt-8 flex-shrink-0 flex flex-col transition-all duration-200"
        style={{ width: `${sidebarWidth}px`, minWidth: `${MIN_WIDTH}px` }}
      >
        {/* Resize handle */}
        <div
          className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-300 active:bg-blue-500 transition-colors"
          onMouseDown={startResizing}
        />

        {/* User profile */}
        <div className="px-4 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
              <span className="text-gray-600 dark:text-gray-300 font-medium">
                {user?.name?.charAt(0) || 'U'}
              </span>
            </div>
            {sidebarWidth > 96 && (
              <div className="ml-3 overflow-hidden">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                  {user?.name || 'User'}
                </p>
                <button 
                  onClick={() => {
                    trackEvent('auth_logout_button_click', {
                      location: 'sidebar',
                      timestamp: new Date().toISOString()
                    });
                    setShowLogoutConfirm(true);
                  }}
                  className="text-xs text-primary hover:text-blue-700 dark:hover:text-blue-400 text-left w-full truncate"
                  disabled={loggingOut}
                >
                  {loggingOut ? 'Signing out...' : 'Sign out'}
                </button>
              </div>
            )}
          </div>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto">
          <ul className="p-0 m-0 list-none space-y-2">
            {tabs.map(tab => {
              const isActive = activeTab === tab.id;
              const isCollapsed = sidebarWidth <= MIN_WIDTH;
              return (
                <li key={tab.id} className={isCollapsed ? 'flex justify-center' : ''}>
                  <button
                    type="button"
                    onClick={() => onTabChange(tab.id)}
                    className={`flex items-center ${
                      isCollapsed
                        ? 'justify-center p-2 w-auto'
                        : 'justify-start w-full px-4 py-3'
                    } transition-colors duration-200 rounded-lg text-sm ${
                      isActive
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-primary'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/20'
                    }`}
                  >
                    <SidebarIcon type={tab.icon} active={isActive} />
                    {!isCollapsed && <span className="ml-3 truncate">{tab.label}</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>
      
      {/* Logout Confirmation Modal */}
      {showLogoutConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-25 backdrop-blur-sm flex justify-center items-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 m-4 max-w-sm w-full">
            <div className="flex justify-center mb-4 text-amber-500">
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-gray-100 text-center mb-2">
              Sign Out Confirmation
            </h3>
            
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
              Are you sure you want to sign out? Any unsaved changes will be lost.
            </p>
            
            <div className="mt-6 flex justify-center space-x-4">
              <button
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400"
                onClick={() => {
                  trackEvent('auth_logout_cancel', {
                    timestamp: new Date().toISOString()
                  });
                  setShowLogoutConfirm(false);
                }}
                disabled={loggingOut}
              >
                Cancel
              </button>
              
              <button
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                onClick={async () => {
                  setLoggingOut(true);
                  trackEvent('auth_logout_confirm', {
                    timestamp: new Date().toISOString()
                  });
                  
                  try {
                    await onLogout();
                    // The redirect will happen in the onLogout function
                  } catch (error) {
                    console.error('Logout failed:', error);
                    setLoggingOut(false);
                    setShowLogoutConfirm(false);
                  }
                }}
                disabled={loggingOut}
              >
                {loggingOut ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing out...
                  </>
                ) : (
                  'Sign Out'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

// Enhanced SidebarIcon with better responsive sizing
const SidebarIcon = ({ type, active }) => {
  const activeClass = active ? 'text-primary' : 'text-gray-500 dark:text-gray-400';
  
  // Common icon props
  const iconProps = {
    className: `w-5 h-5 ${activeClass} transition-all duration-200`,
    fill: "none",
    stroke: "currentColor",
    viewBox: "0 0 24 24"
  };

  switch (type) {
    case 'device':
      return (
        <svg {...iconProps}>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      );
    case 'shield':
      return (
        <svg {...iconProps}>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      );
    case 'download':
      return (
        <svg {...iconProps}>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
        </svg>
      );
    case 'clipboard-list':
      return (
        <svg {...iconProps}>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 3h6a2 2 0 012 2v0a2 2 0 01-2 2H9a2 2 0 01-2-2V5a2 2 0 012-2z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9h6M9 13h6M9 17h6" />
        </svg>
      );
    case 'home':
      return (
        <svg {...iconProps}>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 2l2-2m2 2l2-2m4 2l2-2m2 2l2-2l2 2-2 2-2-2-2 2-2 2 2 2 2-2" />
        </svg>
      );
    default:
      return null;
  }
};

export default Sidebar;
