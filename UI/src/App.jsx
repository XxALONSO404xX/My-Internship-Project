import React, { useState, useEffect, useContext } from 'react'
import { AuthProvider, AuthContext } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import LoginPage from './pages/LoginPage'
import Dashboard from './pages/Dashboard'
import RegisterPage from './pages/RegisterPage'
import PasswordResetPage from './pages/PasswordResetPage'
import VerificationPage from './pages/VerificationPage'
import './index.css'
import './styles/theme.css'

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

// Main app content that uses authentication context
function AppContent() {
  const { isAuthenticated, loading, verificationNeeded, user, logout, clearError } = useContext(AuthContext)
  const [currentPage, setCurrentPage] = useState('login')

  // State for verification and reset tokens
  const [verificationToken, setVerificationToken] = useState(null)
  const [resetToken, setResetToken] = useState(null)

  // Handle hash-based navigation
  useEffect(() => {
    const handleHashChange = () => {
      // Clear any authentication errors when changing pages
      clearError();
      
      // Get the hash without the # symbol
      const fullHash = window.location.hash.replace('#', '')
      
      // Check for verification token
      if (fullHash.startsWith('verify/')) {
        const token = fullHash.replace('verify/', '')
        setVerificationToken(token)
        setCurrentPage('verify')
        return
      }
      
      // Check for password reset token
      if (fullHash.startsWith('reset-password/')) {
        // Extract token and remove any URL encoding or trailing slashes
        const token = fullHash.replace('reset-password/', '').trim()
        console.log('App: Password reset token extracted:', token ? `${token.substring(0, 5)}...` : 'empty token')
        
        if (!token) {
          console.error('App: Empty reset token extracted from URL')
          // Still set the page but with empty token for proper error handling
        }
        
        setResetToken(token)
        setCurrentPage('forgot-password')
        return
      }
      
      // Regular page navigation
      const hash = fullHash || 'login'
      setCurrentPage(hash)
      // Clear tokens when navigating away
      if (hash !== 'verify') setVerificationToken(null)
      if (hash !== 'forgot-password') setResetToken(null)
    }

    // Set initial page based on hash
    handleHashChange()

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [clearError])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }

  // If authenticated, always show dashboard
  if (isAuthenticated) {
    return <Dashboard user={user} logout={logout} />
  }

  // If account needs verification, show verification page
  if (verificationNeeded && currentPage !== 'verify') {
    window.location.hash = 'verify'
    return null
  }

  // Otherwise, show appropriate auth page based on hash
  switch (currentPage) {
    case 'register':
      return <RegisterPage />
    case 'forgot-password':
      return <PasswordResetPage token={resetToken} />
    case 'verify':
      return <VerificationPage token={verificationToken} />
    case 'login':
    default:
      return <LoginPage />
  }
}

// Main App component with providers
function App() {
  // Dark mode is now managed by ThemeContext
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export default App
