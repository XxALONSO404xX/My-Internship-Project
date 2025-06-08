import React, { createContext, useState, useEffect, useContext } from 'react';
import { useColorMode } from '@chakra-ui/react';

// Theme context for synchronizing Tailwind dark mode and Chakra UI color mode
export const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const { colorMode: chakraColorMode, toggleColorMode: toggleChakra } = useColorMode();

  // Check for user preference in localStorage or system preference
  const getInitialTheme = () => {
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
      return savedTheme;
    }
    
    // Check for system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    
    return 'light';
  };
  
  const [theme, setTheme] = useState(getInitialTheme);
  
  // Toggle theme function
  const toggleTheme = () => {
    setTheme(prevTheme => {
      const newTheme = prevTheme === 'light' ? 'dark' : 'light';
      return newTheme;
    });
  };
  
  // Apply theme to document
  useEffect(() => {
    // Save to localStorage
    localStorage.setItem('theme', theme);
    localStorage.setItem('darkMode', theme === 'dark'); // For compatibility with existing code
    
    // Apply to document
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark'); // Keep both systems
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.removeAttribute('data-theme');
    }
    // Sync Chakra UI color mode
    if (chakraColorMode !== theme) {
      toggleChakra();
    }
  }, [theme]);
  
  // Update theme if system preference changes
  useEffect(() => {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      const handleChange = (e) => {
        const hasUserSetPreference = localStorage.getItem('theme');
        
        // Only change if user hasn't explicitly set a preference
        if (!hasUserSetPreference) {
          setTheme(e.matches ? 'dark' : 'light');
        }
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
