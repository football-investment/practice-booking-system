// Debug script to check what dashboard component is actually loading
console.log('=== DASHBOARD DEBUG SCRIPT ===');

// Check if UnifiedDashboard class exists
const unifiedDashboard = document.querySelector('.unified-dashboard');
const studentDashboard = document.querySelector('.student-dashboard-container, .student-dashboard');
const navigationSidebar = document.querySelector('.navigation-sidebar');

console.log('Dashboard components found:');
console.log('- UnifiedDashboard:', !!unifiedDashboard);
console.log('- StudentDashboard:', !!studentDashboard);
console.log('- NavigationSidebar:', !!navigationSidebar);

// Check for the broken text elements
const brokenTextElements = document.querySelectorAll('*');
let brokenTexts = [];

brokenTextElements.forEach(el => {
  const text = el.textContent || '';
  if (text.match(/d\s*a\s*s\s*h.*b\s*o\s*a\s*r\s*d|s\s*c\s*h\s*o\s*o\s*l|f\s*o\s*r\s*u\s*m/i)) {
    brokenTexts.push({
      element: el,
      text: text,
      classes: el.className,
      tag: el.tagName
    });
  }
});

console.log('Broken text elements found:', brokenTexts.length);
brokenTexts.forEach((item, index) => {
  console.log(`${index + 1}. ${item.tag}.${item.classes}: "${item.text}"`);
});

// Check what CSS files are loaded
const stylesheets = Array.from(document.styleSheets);
console.log('Loaded stylesheets:');
stylesheets.forEach(sheet => {
  try {
    console.log('- ' + (sheet.href || 'inline'));
  } catch (e) {
    console.log('- [cross-origin stylesheet]');
  }
});

// Check for specific CSS rules
function checkCSSRule(selector) {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    const computedStyle = getComputedStyle(elements[0]);
    return {
      whiteSpace: computedStyle.whiteSpace,
      overflow: computedStyle.overflow,
      textOverflow: computedStyle.textOverflow,
      display: computedStyle.display,
      flexWrap: computedStyle.flexWrap
    };
  }
  return null;
}

console.log('CSS properties check:');
console.log('- .nav-label:', checkCSSRule('.nav-label'));
console.log('- .nav-button:', checkCSSRule('.nav-button'));
console.log('- .navigation-sidebar:', checkCSSRule('.navigation-sidebar'));

// Check if webpack hot reload is working
console.log('Webpack HMR active:', !!module.hot);

console.log('=== END DASHBOARD DEBUG ===');