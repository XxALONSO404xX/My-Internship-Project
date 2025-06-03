import React, { useState, useEffect } from 'react';

/**
 * Super Basic Diagnostic Page - No Tailwind, just inline styles
 * to troubleshoot rendering issues
 */
export default function DiagnosticPage() {
  const [message, setMessage] = useState('Initial rendering works!');
  const [electronStatus, setElectronStatus] = useState('Checking...');
  
  // Basic test of React functionality
  useEffect(() => {
    // Test if useEffect hook is working
    setMessage('React hooks are working!');
    
    // Test if we can access window object
    const windowInfo = `Window size: ${window.innerWidth}x${window.innerHeight}`;
    setMessage(prev => `${prev} - ${windowInfo}`);
    
    // Check if Electron APIs are accessible (but with very basic error handling)
    try {
      if (window.electronAPI) {
        setElectronStatus('Electron API is available');
      } else {
        setElectronStatus('Electron API is NOT available');
      }
    } catch (err) {
      setElectronStatus(`Error: ${err.message}`);
    }
  }, []);

  const basicContainerStyle = {
    padding: '20px',
    maxWidth: '600px',
    margin: '20px auto',
    backgroundColor: 'white',
    border: '1px solid #ccc',
    borderRadius: '5px',
    fontFamily: 'Arial, sans-serif'
  };
  
  const headingStyle = {
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '15px',
    color: '#333'
  };
  
  const sectionStyle = {
    marginBottom: '15px',
    padding: '10px',
    backgroundColor: '#f5f5f5',
    border: '1px solid #ddd',
    borderRadius: '4px'
  };
  
  const buttonStyle = {
    padding: '8px 16px',
    backgroundColor: '#0066cc',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginTop: '10px',
    width: '100%'
  };

  return (
    <div style={basicContainerStyle}>
      <h1 style={headingStyle}>BASIC IoT Platform Diagnostic</h1>
      
      <div style={sectionStyle}>
        <h2 style={{fontSize: '18px', marginBottom: '5px'}}>React Status</h2>
        <p>{message}</p>
      </div>
      
      <div style={sectionStyle}>
        <h2 style={{fontSize: '18px', marginBottom: '5px'}}>Electron Status</h2>
        <p>{electronStatus}</p>
      </div>
      
      <div style={sectionStyle}>
        <h2 style={{fontSize: '18px', marginBottom: '5px'}}>User Agent</h2>
        <p style={{fontSize: '12px', wordBreak: 'break-all'}}>{navigator.userAgent}</p>
      </div>
      
      <button style={buttonStyle} onClick={() => window.location.reload()}>
        Reload Page
      </button>
      
      <div style={{marginTop: '20px', fontSize: '12px', color: '#666'}}>
        Time: {new Date().toLocaleString()}
      </div>
    </div>
  );
}
