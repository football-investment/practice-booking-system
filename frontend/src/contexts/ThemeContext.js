import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  // Initialize theme from localStorage or default to 'auto'
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme || 'auto';
  });

  // Initialize color scheme from localStorage or default to 'purple'  
  const [colorScheme, setColorScheme] = useState(() => {
    const savedColorScheme = localStorage.getItem('colorScheme');
    return savedColorScheme || 'purple';
  });

  // Apply theme to document root whenever theme or colorScheme changes
  useEffect(() => {
    const root = document.documentElement;
    
    console.log('🎨 ThemeContext: Applying theme:', { theme, colorScheme });

    if (theme === 'auto') {
      // Safe check for test environment and browser compatibility
      const mediaQuery = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
      
      const applyAutoTheme = () => {
        const prefersDark = mediaQuery && mediaQuery.matches;
        root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        root.setAttribute('data-color', colorScheme);
        console.log('🌗 Auto theme applied:', prefersDark ? 'dark' : 'light');
      };

      // Apply initial theme
      applyAutoTheme();
      
      // Listen for system theme changes (if available)
      if (mediaQuery && typeof mediaQuery.addListener === 'function') {
        const listener = applyAutoTheme;
        mediaQuery.addListener(listener);

        // Cleanup listener on unmount or theme change
        return () => {
          if (mediaQuery && typeof mediaQuery.removeListener === 'function') {
            mediaQuery.removeListener(listener);
          }
        };
      }
    } else {
      // Manual theme selection
      root.setAttribute('data-theme', theme);
      root.setAttribute('data-color', colorScheme);
      console.log('🎨 Manual theme applied:', theme);
    }
  }, [theme, colorScheme]);

  // Theme change handler with localStorage persistence
  const changeTheme = (newTheme) => {
    console.log('🎨 ThemeContext: Changing theme to:', newTheme);
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Dispatch custom event for any components that need to react
    window.dispatchEvent(new CustomEvent('themeChanged', { 
      detail: { theme: newTheme, colorScheme } 
    }));
  };

  // Color scheme change handler with localStorage persistence
  const changeColorScheme = (newColorScheme) => {
    console.log('🎨 ThemeContext: Changing color scheme to:', newColorScheme);
    setColorScheme(newColorScheme);
    localStorage.setItem('colorScheme', newColorScheme);
    
    // Dispatch custom event for any components that need to react
    window.dispatchEvent(new CustomEvent('colorSchemeChanged', { 
      detail: { theme, colorScheme: newColorScheme } 
    }));
  };

  // Get current effective theme (resolving 'auto' to actual theme)
  const getEffectiveTheme = () => {
    if (theme === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return theme;
  };

  // Determine if current theme is dark
  const isDarkMode = () => {
    return getEffectiveTheme() === 'dark';
  };

  // Toggle between light and dark (useful for quick testing)
  const toggleTheme = () => {
    const currentEffective = getEffectiveTheme();
    const newTheme = currentEffective === 'dark' ? 'light' : 'dark';
    changeTheme(newTheme);
  };

  const value = {
    // State
    theme,
    colorScheme,
    
    // Actions
    setTheme: changeTheme,
    setColorScheme: changeColorScheme,
    toggleTheme,
    
    // Utilities
    getEffectiveTheme,
    isDarkMode,
    
    // Available options
    themes: ['light', 'dark', 'auto'],
    colorSchemes: ['purple', 'blue', 'green', 'red', 'orange', 'cyber', 'ocean', 'sunset']
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};