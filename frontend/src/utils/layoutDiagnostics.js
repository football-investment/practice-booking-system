/* 🔧 LAYOUT DIAGNOSTICS & PERFORMANCE MONITORING */

// Layout Shift Detection
export function detectLayoutShifts() {
  if (!window.PerformanceObserver) {
    console.warn('PerformanceObserver not supported');
    return;
  }

  let cumulativeLayoutShift = 0;

  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) {
        cumulativeLayoutShift += entry.value;
        
        if (entry.value > 0.1) {
          console.warn('🚨 Significant Layout Shift detected:', {
            value: entry.value,
            sources: entry.sources,
            timestamp: entry.startTime
          });
        }
      }
    }
    
    console.log('📊 Cumulative Layout Shift:', cumulativeLayoutShift);
  });
  
  observer.observe({ type: 'layout-shift', buffered: true });
  
  return observer;
}

// Text Overflow Detection
export function detectTextOverflow() {
  const elements = document.querySelectorAll('*');
  const overflowingElements = [];
  
  elements.forEach(element => {
    if (element.scrollWidth > element.clientWidth || 
        element.scrollHeight > element.clientHeight) {
      
      const computedStyle = window.getComputedStyle(element);
      const textOverflow = computedStyle.textOverflow;
      const overflow = computedStyle.overflow;
      
      if (textOverflow === 'ellipsis' || overflow === 'hidden') {
        overflowingElements.push({
          element,
          textContent: element.textContent?.substring(0, 100) + '...',
          className: element.className,
          tagName: element.tagName,
          scrollWidth: element.scrollWidth,
          clientWidth: element.clientWidth,
          textOverflow,
          overflow
        });
      }
    }
  });
  
  if (overflowingElements.length > 0) {
    console.warn('🚨 Text overflow detected:', overflowingElements);
  }
  
  return overflowingElements;
}

// Viewport Analysis
export function analyzeViewport() {
  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight,
    devicePixelRatio: window.devicePixelRatio,
    orientation: screen.orientation?.type || 'unknown',
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    touchSupport: 'ontouchstart' in window,
    cookieEnabled: navigator.cookieEnabled,
    language: navigator.language,
    onlineStatus: navigator.onLine
  };
  
  console.log('📱 Viewport Analysis:', viewport);
  return viewport;
}

// Element Dimensions Analysis
export function analyzeElementDimensions(selector) {
  const elements = document.querySelectorAll(selector);
  const analysis = [];
  
  elements.forEach((element, index) => {
    const rect = element.getBoundingClientRect();
    const computedStyle = window.getComputedStyle(element);
    
    analysis.push({
      index,
      element,
      dimensions: {
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left
      },
      computedStyles: {
        display: computedStyle.display,
        position: computedStyle.position,
        overflow: computedStyle.overflow,
        textOverflow: computedStyle.textOverflow,
        whiteSpace: computedStyle.whiteSpace,
        wordWrap: computedStyle.wordWrap,
        boxSizing: computedStyle.boxSizing
      },
      content: element.textContent?.substring(0, 50) + '...'
    });
  });
  
  console.log(`📏 Element Analysis for "${selector}":`, analysis);
  return analysis;
}

// Performance Metrics
export function getPerformanceMetrics() {
  const metrics = {};
  
  // Navigation Timing
  if (performance.getEntriesByType) {
    const navigation = performance.getEntriesByType('navigation')[0];
    if (navigation) {
      metrics.navigationTiming = {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstPaint: navigation.domContentLoadedEventEnd - navigation.fetchStart,
        totalLoadTime: navigation.loadEventEnd - navigation.fetchStart
      };
    }
  }
  
  // Paint Timing
  if (performance.getEntriesByType) {
    const paintEntries = performance.getEntriesByType('paint');
    paintEntries.forEach(entry => {
      metrics[entry.name] = entry.startTime;
    });
  }
  
  // Memory Usage (if available)
  if (performance.memory) {
    metrics.memory = {
      usedJSHeapSize: performance.memory.usedJSHeapSize,
      totalJSHeapSize: performance.memory.totalJSHeapSize,
      jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
    };
  }
  
  console.log('⚡ Performance Metrics:', metrics);
  return metrics;
}

// CSS Rule Analysis
export function analyzeCSSRules() {
  const sheets = Array.from(document.styleSheets);
  const analysis = {
    totalSheets: sheets.length,
    totalRules: 0,
    importantRules: 0,
    unusedRules: [],
    conflictingRules: []
  };
  
  sheets.forEach(sheet => {
    try {
      const rules = Array.from(sheet.cssRules || sheet.rules || []);
      analysis.totalRules += rules.length;
      
      rules.forEach(rule => {
        if (rule.style) {
          // Count !important rules
          const styleText = rule.style.cssText;
          const importantMatches = styleText.match(/!important/g);
          if (importantMatches) {
            analysis.importantRules += importantMatches.length;
          }
        }
      });
    } catch (e) {
      console.warn('Cannot access stylesheet:', sheet.href, e);
    }
  });
  
  console.log('🎨 CSS Analysis:', analysis);
  return analysis;
}

// Responsive Breakpoint Testing
export function testResponsiveBreakpoints() {
  const breakpoints = [
    { name: 'mobile', width: 375 },
    { name: 'mobile-large', width: 414 },
    { name: 'tablet', width: 768 },
    { name: 'tablet-large', width: 1024 },
    { name: 'desktop', width: 1200 },
    { name: 'desktop-large', width: 1440 },
    { name: 'desktop-xl', width: 1920 }
  ];
  
  const currentWidth = window.innerWidth;
  let currentBreakpoint = 'unknown';
  
  for (let i = breakpoints.length - 1; i >= 0; i--) {
    if (currentWidth >= breakpoints[i].width) {
      currentBreakpoint = breakpoints[i].name;
      break;
    }
  }
  
  const analysis = {
    currentWidth,
    currentHeight: window.innerHeight,
    currentBreakpoint,
    allBreakpoints: breakpoints,
    isPortrait: window.innerHeight > window.innerWidth
  };
  
  console.log('📐 Responsive Analysis:', analysis);
  return analysis;
}

// Text Truncation Fixer
export function fixTextTruncation(selector = '*') {
  const elements = document.querySelectorAll(selector);
  let fixedCount = 0;
  
  elements.forEach(element => {
    const computedStyle = window.getComputedStyle(element);
    
    if (computedStyle.textOverflow === 'ellipsis' || 
        computedStyle.overflow === 'hidden') {
      
      element.style.setProperty('white-space', 'normal', 'important');
      element.style.setProperty('overflow', 'visible', 'important');
      element.style.setProperty('text-overflow', 'clip', 'important');
      element.style.setProperty('word-wrap', 'break-word', 'important');
      element.style.setProperty('overflow-wrap', 'break-word', 'important');
      
      fixedCount++;
    }
  });
  
  console.log(`🔧 Fixed text truncation on ${fixedCount} elements`);
  return fixedCount;
}

// Development Helper - Visual Debug
export function enableVisualDebug() {
  const style = document.createElement('style');
  style.textContent = `
    .debug-visual * {
      outline: 1px solid rgba(255, 0, 0, 0.5) !important;
      background: rgba(255, 0, 0, 0.05) !important;
    }
    
    .debug-visual .spec-preview-card {
      outline: 2px solid blue !important;
      background: rgba(0, 0, 255, 0.1) !important;
    }
    
    .debug-visual .specialization-preview-enhanced {
      outline: 3px solid green !important;
      background: rgba(0, 255, 0, 0.1) !important;
    }
  `;
  
  document.head.appendChild(style);
  document.body.classList.add('debug-visual');
  
  console.log('🎨 Visual debug mode enabled');
  
  return () => {
    document.head.removeChild(style);
    document.body.classList.remove('debug-visual');
    console.log('🎨 Visual debug mode disabled');
  };
}

// Master Diagnostic Function
export function runComprehensiveDiagnostics() {
  console.log('🚀 Starting Comprehensive Frontend Diagnostics...');
  
  const results = {
    timestamp: new Date().toISOString(),
    viewport: analyzeViewport(),
    performance: getPerformanceMetrics(),
    responsive: testResponsiveBreakpoints(),
    css: analyzeCSSRules(),
    textOverflow: detectTextOverflow(),
    specializationCards: analyzeElementDimensions('.spec-preview-card'),
    specializationContainer: analyzeElementDimensions('.specialization-preview-enhanced')
  };
  
  // Start layout shift monitoring
  const layoutShiftObserver = detectLayoutShifts();
  
  console.log('✅ Comprehensive Diagnostics Complete:', results);
  
  return {
    results,
    layoutShiftObserver,
    fixTextTruncation: () => fixTextTruncation(),
    enableVisualDebug: enableVisualDebug
  };
}

// Auto-initialize in development
if (process.env.NODE_ENV === 'development') {
  window.layoutDiagnostics = {
    runComprehensiveDiagnostics,
    detectLayoutShifts,
    detectTextOverflow,
    analyzeViewport,
    analyzeElementDimensions,
    getPerformanceMetrics,
    analyzeCSSRules,
    testResponsiveBreakpoints,
    fixTextTruncation,
    enableVisualDebug
  };
  
  console.log('🔧 Layout Diagnostics available at window.layoutDiagnostics');
}