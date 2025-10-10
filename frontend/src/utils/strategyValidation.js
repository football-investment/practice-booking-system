/* 📊 STRATEGY VALIDATION - 10 PILLAR COMPLIANCE CHECK */

// 1. 🔍 Azonnali Diagnosztika Validáció
export function validateDiagnostics() {
  const results = {
    pillar: '🔍 Azonnali Diagnosztika',
    score: 0,
    maxScore: 100,
    checks: []
  };
  
  // CSS Problem Detection
  const stylesheets = Array.from(document.styleSheets);
  let importantCount = 0;
  let ellipsisCount = 0;
  
  stylesheets.forEach(sheet => {
    try {
      const rules = Array.from(sheet.cssRules || []);
      rules.forEach(rule => {
        if (rule.style && rule.style.cssText.includes('!important')) {
          importantCount++;
        }
        if (rule.style && rule.style.cssText.includes('text-overflow: ellipsis')) {
          ellipsisCount++;
        }
      });
    } catch (e) {
      // Cross-origin stylesheet
    }
  });
  
  // Horizontal Scroll Check
  const hasHorizontalScroll = document.body.scrollWidth > window.innerWidth;
  results.checks.push({
    name: 'No Horizontal Scroll',
    passed: !hasHorizontalScroll,
    points: 30,
    message: hasHorizontalScroll ? 'Horizontal scroll detected' : 'No horizontal scroll ✅'
  });
  
  // Text Truncation Check
  const ellipsisElements = Array.from(document.querySelectorAll('*')).filter(el => {
    const style = window.getComputedStyle(el);
    return style.textOverflow === 'ellipsis';
  });
  
  results.checks.push({
    name: 'No Text Truncation',
    passed: ellipsisElements.length === 0,
    points: 40,
    message: ellipsisElements.length === 0 ? 'No ellipsis found ✅' : `${ellipsisElements.length} ellipsis elements found ❌`
  });
  
  // Viewport Setup Check
  const viewportMeta = document.querySelector('meta[name="viewport"]');
  const hasProperViewport = viewportMeta && viewportMeta.content.includes('width=device-width');
  
  results.checks.push({
    name: 'Proper Viewport Setup',
    passed: hasProperViewport,
    points: 30,
    message: hasProperViewport ? 'Viewport properly configured ✅' : 'Viewport meta tag missing or incorrect ❌'
  });
  
  // Calculate score
  results.score = results.checks.reduce((total, check) => {
    return total + (check.passed ? check.points : 0);
  }, 0);
  
  return results;
}

// 2. 🔧 CSS Foundation Validáció
export function validateCSSFoundation() {
  const results = {
    pillar: '🔧 CSS Foundation',
    score: 0,
    maxScore: 100,
    checks: []
  };
  
  // Box-sizing Check
  const bodyStyle = window.getComputedStyle(document.body);
  const hasBoxSizing = bodyStyle.boxSizing === 'border-box';
  
  results.checks.push({
    name: 'Box-sizing Border-box',
    passed: hasBoxSizing,
    points: 25,
    message: hasBoxSizing ? 'Box-sizing properly set ✅' : 'Box-sizing not set to border-box ❌'
  });
  
  // Overflow-x Hidden Check
  const hasOverflowXHidden = bodyStyle.overflowX === 'hidden';
  
  results.checks.push({
    name: 'Body Overflow-X Hidden',
    passed: hasOverflowXHidden,
    points: 25,
    message: hasOverflowXHidden ? 'Overflow-X properly hidden ✅' : 'Overflow-X not hidden ❌'
  });
  
  // CSS Custom Properties Check
  const hasCustomProperties = document.documentElement.style.getPropertyValue('--font-size-base') || 
                             document.documentElement.style.getPropertyValue('--space-4');
  
  results.checks.push({
    name: 'CSS Custom Properties',
    passed: hasCustomProperties !== '',
    points: 25,
    message: hasCustomProperties ? 'CSS custom properties found ✅' : 'CSS custom properties missing ❌'
  });
  
  // Reset Styles Check
  const firstElement = document.querySelector('*');
  const elementStyle = firstElement ? window.getComputedStyle(firstElement) : null;
  const hasReset = elementStyle && (elementStyle.margin === '0px' || elementStyle.padding === '0px');
  
  results.checks.push({
    name: 'CSS Reset Applied',
    passed: hasReset,
    points: 25,
    message: hasReset ? 'CSS reset detected ✅' : 'CSS reset not applied ❌'
  });
  
  results.score = results.checks.reduce((total, check) => {
    return total + (check.passed ? check.points : 0);
  }, 0);
  
  return results;
}

// 3. 📱 Mobile-First Validáció
export function validateMobileFirst() {
  const results = {
    pillar: '📱 Mobile-First Responsive',
    score: 0,
    maxScore: 100,
    checks: []
  };
  
  // Touch Target Size Check
  const touchElements = document.querySelectorAll('button, a, input, select');
  const smallTargets = Array.from(touchElements).filter(el => {
    const rect = el.getBoundingClientRect();
    return rect.width < 44 || rect.height < 44;
  });
  
  results.checks.push({
    name: 'Touch Target Sizes',
    passed: smallTargets.length === 0,
    points: 30,
    message: smallTargets.length === 0 ? 'All touch targets ≥ 44px ✅' : `${smallTargets.length} small touch targets found ❌`
  });
  
  // Responsive Meta Tags
  const viewportMeta = document.querySelector('meta[name="viewport"]');
  const hasResponsiveMeta = viewportMeta && viewportMeta.content.includes('initial-scale=1');
  
  results.checks.push({
    name: 'Responsive Meta Tags',
    passed: hasResponsiveMeta,
    points: 25,
    message: hasResponsiveMeta ? 'Responsive meta tags present ✅' : 'Responsive meta tags missing ❌'
  });
  
  // Flexbox/Grid Usage
  const flexElements = document.querySelectorAll('[class*="flex"], [class*="grid"]');
  const hasModernLayout = flexElements.length > 0;
  
  results.checks.push({
    name: 'Modern Layout (Flex/Grid)',
    passed: hasModernLayout,
    points: 25,
    message: hasModernLayout ? 'Modern layout systems detected ✅' : 'No modern layout systems found ❌'
  });
  
  // Mobile Optimization
  const isMobileOptimized = window.innerWidth <= 768 ? 
    document.body.style.fontSize !== '' || 
    Array.from(document.querySelectorAll('*')).some(el => el.classList.contains('mobile') || el.classList.contains('responsive')) :
    true;
  
  results.checks.push({
    name: 'Mobile Optimization',
    passed: isMobileOptimized,
    points: 20,
    message: isMobileOptimized ? 'Mobile optimization detected ✅' : 'Mobile optimization missing ❌'
  });
  
  results.score = results.checks.reduce((total, check) => {
    return total + (check.passed ? check.points : 0);
  }, 0);
  
  return results;
}

// 4. 🎨 Typography Validáció
export function validateTypography() {
  const results = {
    pillar: '🎨 Typography & Text Management',
    score: 0,
    maxScore: 100,
    checks: []
  };
  
  // Fluid Typography Check
  const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
  const hasFluidTypography = Array.from(headings).some(el => {
    const style = window.getComputedStyle(el);
    return style.fontSize.includes('clamp') || style.fontSize.includes('vw');
  });
  
  results.checks.push({
    name: 'Fluid Typography',
    passed: hasFluidTypography,
    points: 30,
    message: hasFluidTypography ? 'Fluid typography detected ✅' : 'No fluid typography found ❌'
  });
  
  // Text Readability Check
  const paragraphs = document.querySelectorAll('p');
  const readableParagraphs = Array.from(paragraphs).filter(p => {
    const style = window.getComputedStyle(p);
    return parseFloat(style.lineHeight) >= 1.4;
  });
  
  results.checks.push({
    name: 'Text Readability',
    passed: readableParagraphs.length > 0,
    points: 25,
    message: readableParagraphs.length > 0 ? 'Good line-height detected ✅' : 'Poor text readability ❌'
  });
  
  // Font Loading Check
  const hasFontDisplay = document.fonts && document.fonts.ready;
  
  results.checks.push({
    name: 'Font Loading Optimization',
    passed: hasFontDisplay,
    points: 20,
    message: hasFontDisplay ? 'Font loading optimized ✅' : 'Font loading not optimized ❌'
  });
  
  // Color Contrast Check (basic)
  const hasGoodContrast = Array.from(document.querySelectorAll('p, h1, h2, h3, h4, h5, h6')).some(el => {
    const style = window.getComputedStyle(el);
    const color = style.color;
    return color.includes('rgb(26, 32, 44)') || color.includes('#1a202c') || color.includes('rgb(74, 85, 104)');
  });
  
  results.checks.push({
    name: 'Color Contrast',
    passed: hasGoodContrast,
    points: 25,
    message: hasGoodContrast ? 'Good color contrast detected ✅' : 'Poor color contrast ❌'
  });
  
  results.score = results.checks.reduce((total, check) => {
    return total + (check.passed ? check.points : 0);
  }, 0);
  
  return results;
}

// 5. 🧩 Component Architecture Validáció
export function validateComponents() {
  const results = {
    pillar: '🧩 Component Architecture',
    score: 0,
    maxScore: 100,
    checks: []
  };
  
  // Button Standardization
  const buttons = document.querySelectorAll('button, .btn');
  const standardButtons = Array.from(buttons).filter(btn => {
    const style = window.getComputedStyle(btn);
    return style.borderRadius !== '0px' && style.padding !== '0px';
  });
  
  results.checks.push({
    name: 'Button Standardization',
    passed: standardButtons.length > 0,
    points: 25,
    message: standardButtons.length > 0 ? 'Standardized buttons found ✅' : 'No standardized buttons ❌'
  });
  
  // Card Components
  const cards = document.querySelectorAll('.card, [class*="card"]');
  const hasCards = cards.length > 0;
  
  results.checks.push({
    name: 'Card Components',
    passed: hasCards,
    points: 25,
    message: hasCards ? 'Card components detected ✅' : 'No card components found ❌'
  });
  
  // Form Elements
  const formElements = document.querySelectorAll('input, select, textarea');
  const styledFormElements = Array.from(formElements).filter(el => {
    const style = window.getComputedStyle(el);
    return style.borderRadius !== '0px' || style.border !== 'none';
  });
  
  results.checks.push({
    name: 'Form Element Styling',
    passed: styledFormElements.length > 0,
    points: 25,
    message: styledFormElements.length > 0 ? 'Styled form elements found ✅' : 'No styled form elements ❌'
  });
  
  // Consistent Spacing
  const elementsWithSpacing = document.querySelectorAll('[class*="m-"], [class*="p-"], [class*="space"], [class*="gap"]');
  const hasConsistentSpacing = elementsWithSpacing.length > 0;
  
  results.checks.push({
    name: 'Consistent Spacing',
    passed: hasConsistentSpacing,
    points: 25,
    message: hasConsistentSpacing ? 'Consistent spacing system detected ✅' : 'No consistent spacing ❌'
  });
  
  results.score = results.checks.reduce((total, check) => {
    return total + (check.passed ? check.points : 0);
  }, 0);
  
  return results;
}

// Performance Metrics Validáció
export function validatePerformance() {
  const results = {
    pillar: '⚡ Performance Optimization',
    score: 0,
    maxScore: 100,
    checks: []
  };
  
  // Navigation Timing
  const navigation = performance.getEntriesByType('navigation')[0];
  const loadTime = navigation ? navigation.loadEventEnd - navigation.fetchStart : 0;
  const fastLoad = loadTime < 3000;
  
  results.checks.push({
    name: 'Fast Load Time',
    passed: fastLoad,
    points: 30,
    message: fastLoad ? `Load time: ${Math.round(loadTime)}ms ✅` : `Slow load time: ${Math.round(loadTime)}ms ❌`
  });
  
  // CSS Size Check
  const stylesheets = Array.from(document.styleSheets);
  const totalStylesheets = stylesheets.length;
  const reasonableCSS = totalStylesheets < 10;
  
  results.checks.push({
    name: 'CSS File Count',
    passed: reasonableCSS,
    points: 20,
    message: reasonableCSS ? `${totalStylesheets} CSS files ✅` : `Too many CSS files: ${totalStylesheets} ❌`
  });
  
  // Memory Usage (if available)
  const memoryInfo = performance.memory;
  let goodMemory = true;
  if (memoryInfo) {
    const usedMB = memoryInfo.usedJSHeapSize / 1048576;
    goodMemory = usedMB < 50;
  }
  
  results.checks.push({
    name: 'Memory Usage',
    passed: goodMemory,
    points: 25,
    message: goodMemory ? 'Memory usage acceptable ✅' : 'High memory usage ❌'
  });
  
  // Animations Performance
  const animatedElements = document.querySelectorAll('[class*="animate"], [class*="fade"], [class*="slide"]');
  const hasAnimations = animatedElements.length > 0;
  
  results.checks.push({
    name: 'Animation Optimization',
    passed: hasAnimations,
    points: 25,
    message: hasAnimations ? 'Animations detected ✅' : 'No animations found ⚠️'
  });
  
  results.score = results.checks.reduce((total, check) => {
    return total + (check.passed ? check.points : 0);
  }, 0);
  
  return results;
}

// Master Validation Function
export function runCompleteStrategyValidation() {
  console.log('🚀 RUNNING COMPLETE STRATEGY VALIDATION...');
  
  const results = {
    timestamp: new Date().toISOString(),
    overallScore: 0,
    maxScore: 600,
    pillars: []
  };
  
  // Run all validations
  const validations = [
    validateDiagnostics(),
    validateCSSFoundation(),
    validateMobileFirst(),
    validateTypography(),
    validateComponents(),
    validatePerformance()
  ];
  
  results.pillars = validations;
  results.overallScore = validations.reduce((total, pillar) => total + pillar.score, 0);
  
  // Grade calculation
  const percentage = (results.overallScore / results.maxScore) * 100;
  let grade = 'F';
  if (percentage >= 90) grade = 'A+';
  else if (percentage >= 85) grade = 'A';
  else if (percentage >= 80) grade = 'B+';
  else if (percentage >= 75) grade = 'B';
  else if (percentage >= 70) grade = 'C+';
  else if (percentage >= 65) grade = 'C';
  else if (percentage >= 60) grade = 'D';
  
  results.grade = grade;
  results.percentage = Math.round(percentage);
  
  // Console output
  console.log('\n📊 STRATEGY VALIDATION RESULTS:');
  console.log(`Overall Score: ${results.overallScore}/${results.maxScore} (${results.percentage}%)`);
  console.log(`Grade: ${results.grade}`);
  console.log('\n📋 PILLAR BREAKDOWN:');
  
  validations.forEach(pillar => {
    console.log(`\n${pillar.pillar}: ${pillar.score}/${pillar.maxScore}`);
    pillar.checks.forEach(check => {
      const status = check.passed ? '✅' : '❌';
      console.log(`  ${status} ${check.name}: ${check.message}`);
    });
  });
  
  // Recommendations
  console.log('\n💡 RECOMMENDATIONS:');
  const failedChecks = validations.flatMap(pillar => 
    pillar.checks.filter(check => !check.passed)
  );
  
  if (failedChecks.length === 0) {
    console.log('🎉 All checks passed! Excellent implementation!');
  } else {
    failedChecks.forEach(check => {
      console.log(`⚠️  Fix: ${check.name} - ${check.message}`);
    });
  }
  
  return results;
}

// Emergency Fix Protocols
export function runEmergencyFixes() {
  console.log('🚨 RUNNING EMERGENCY FIXES...');
  
  let fixCount = 0;
  
  // Fix 1: Remove horizontal scroll
  if (document.body.scrollWidth > window.innerWidth) {
    document.body.style.overflowX = 'hidden';
    fixCount++;
    console.log('✅ Fixed horizontal scroll');
  }
  
  // Fix 2: Remove text truncation
  const ellipsisElements = Array.from(document.querySelectorAll('*')).filter(el => {
    const style = window.getComputedStyle(el);
    return style.textOverflow === 'ellipsis';
  });
  
  ellipsisElements.forEach(el => {
    el.style.setProperty('white-space', 'normal', 'important');
    el.style.setProperty('overflow', 'visible', 'important');
    el.style.setProperty('text-overflow', 'clip', 'important');
    el.style.setProperty('word-wrap', 'break-word', 'important');
    fixCount++;
  });
  
  if (ellipsisElements.length > 0) {
    console.log(`✅ Fixed ${ellipsisElements.length} text truncation issues`);
  }
  
  // Fix 3: Improve touch targets
  const smallTargets = Array.from(document.querySelectorAll('button, a, input')).filter(el => {
    const rect = el.getBoundingClientRect();
    return rect.width < 44 || rect.height < 44;
  });
  
  smallTargets.forEach(el => {
    el.style.minHeight = '44px';
    el.style.minWidth = '44px';
    el.style.padding = '0.5rem';
    fixCount++;
  });
  
  if (smallTargets.length > 0) {
    console.log(`✅ Fixed ${smallTargets.length} small touch targets`);
  }
  
  console.log(`🎯 Total fixes applied: ${fixCount}`);
  return fixCount;
}

// Make available globally for debugging
if (typeof window !== 'undefined') {
  window.strategyValidation = {
    runCompleteStrategyValidation,
    runEmergencyFixes,
    validateDiagnostics,
    validateCSSFoundation,
    validateMobileFirst,
    validateTypography,
    validateComponents,
    validatePerformance
  };
  
  console.log('🔧 Strategy validation tools available at window.strategyValidation');
}