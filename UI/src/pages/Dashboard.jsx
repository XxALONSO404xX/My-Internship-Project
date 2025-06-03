import React from 'react';
import Sidebar from '../components/common/Sidebar';

function Dashboard({ user, logout }) {
  return (
    <div className="flex h-full">
      <Sidebar user={user} onLogout={logout} />
      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">Dashboard</h1>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <div className="card">
              <h2 className="text-xl font-semibold mb-2">Device Summary</h2>
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-gray-500 dark:text-gray-400">Total Devices</p>
                  <p className="text-2xl font-bold">0</p>
                </div>
                <div className="h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-blue-600 dark:text-blue-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
            </div>
            
            <div className="card">
              <h2 className="text-xl font-semibold mb-2">Security Status</h2>
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-gray-500 dark:text-gray-400">Secure Devices</p>
                  <p className="text-2xl font-bold">0</p>
                </div>
                <div className="h-12 w-12 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-green-600 dark:text-green-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
              </div>
            </div>
            
            <div className="card">
              <h2 className="text-xl font-semibold mb-2">System Status</h2>
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-gray-500 dark:text-gray-400">All Systems</p>
                  <p className="text-2xl font-bold text-green-500">Online</p>
                </div>
                <div className="h-12 w-12 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-purple-600 dark:text-purple-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
          
          <div className="card mb-8">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Recent Activity</h2>
              <button className="btn-primary text-sm">View All</button>
            </div>
            <div className="space-y-4">
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">No recent activity to display.</p>
            </div>
          </div>
          
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Quick Actions</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <button className="btn-primary">Add New Device</button>
              <button className="btn-secondary">Run Security Scan</button>
              <button className="btn">View Reports</button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
