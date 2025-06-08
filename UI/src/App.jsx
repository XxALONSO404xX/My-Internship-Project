import React, { useState, useEffect, useContext } from 'react'
import { AuthProvider, AuthContext } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { NotificationProvider } from './contexts/NotificationContext'
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Dashboard from './pages/Dashboard';
import DeviceList from './pages/DeviceList';
import DeviceDetail from './pages/DeviceDetail';
import SecurityPage from './pages/SecurityPage';
import ActivityLogPage from './pages/ActivityLogPage';
import NetworkPage from './pages/NetworkPage';
import RulesPage from './pages/RulesPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import VerificationPage from './pages/VerificationPage';
import PasswordResetPage from './pages/PasswordResetPage';
import { Toaster } from 'react-hot-toast'
import './index.css'
import './styles/theme.css'
import { Fade } from '@chakra-ui/react';
import ThemeToggle from './components/ThemeToggle';

// Error boundary component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong.</h2>
          <details>
            <summary>Error details</summary>
            <p>{this.state.error && this.state.error.toString()}</p>
            <p>Component stack:</p>
            <pre>{this.state.errorInfo && this.state.errorInfo.componentStack}</pre>
          </details>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <NotificationProvider>
            <Router>
              <Fade in={true} transition={{ enter: { duration: 0.3 } }}>
                <Routes>
                  <Route path='/login' element={<LoginPage />} />
                  <Route path='/register' element={<RegisterPage />} />
                  <Route path='/verify-email/:token' element={<VerificationPage />} />
                  <Route path='/forgot-password' element={<PasswordResetPage />} />
                  <Route path='/reset-password/:token' element={<PasswordResetPage />} />
                  <Route element={<ProtectedRoute />}>  {/* Protected routes */}
                    <Route path='/' element={<Navigate to='/dashboard' replace />} />
                    <Route path='/dashboard' element={<Dashboard />} />
                    <Route path='/devices' element={<DeviceList />} />
                    <Route path='/devices/:id' element={<DeviceDetail />} />
                    <Route path='/security' element={<SecurityPage />} />
                    {/* Redirect base activities to logs, filter by target route */}
                    <Route path='/activities' element={<Navigate to='/activities/logs' replace />} />
                    <Route path='/activities/targets/:targetType/:targetId' element={<ActivityLogPage />} />
                    <Route path='/activities/logs' element={<ActivityLogPage />} />
                    <Route path='/activities/alerts' element={<ActivityLogPage />} />
                    <Route path='/network' element={<NetworkPage />} />
                    <Route path='/rules' element={<RulesPage />} />
                    <Route path='*' element={<Navigate to='/dashboard' replace />} />
                  </Route>
                </Routes>
              </Fade>
            </Router>
            <Toaster
              position='top-right'
              toastOptions={{
                success: {
                  style: {
                    background: '#10B981',
                    color: 'white',
                  },
                  iconTheme: {
                    primary: 'white',
                    secondary: '#10B981',
                  },
                  duration: 3000,
                },
                error: {
                  style: {
                    background: '#EF4444',
                    color: 'white',
                  },
                  iconTheme: {
                    primary: 'white',
                    secondary: '#EF4444',
                  },
                  duration: 4000,
                },
                loading: {
                  style: {
                    background: '#3B82F6',
                    color: 'white',
                  },
                  iconTheme: {
                    primary: 'white',
                    secondary: '#3B82F6',
                  },
                },
              }}
            />
            <ThemeToggle />
          </NotificationProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App
