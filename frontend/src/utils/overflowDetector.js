/**
 * 🚨 OVERFLOW DETECTOR UTILITY
 * Detects and highlights elements causing layout overflow issues
 */

export const detectOverflow = () => {
  console.log('🚨 OVERFLOW DETECTOR RUNNING...');
  
  const allElements = document.querySelectorAll('.lfa-dashboard *');
  const overflowElements = [];
  
  allElements.forEach((element, index) => {
    const rect = element.getBoundingClientRect();
    const parent = element.parentElement;
    
    if (parent) {
      const parentRect = parent.getBoundingClientRect();
      
      // Check horizontal overflow
      if (rect.right > parentRect.right || rect.left < parentRect.left) {
        element.classList.add('debug-overflow');
        element.setAttribute('data-size', `W:${Math.round(rect.width)}px H:${Math.round(rect.height)}px`);
        element.classList.add('size-info');
        
        overflowElements.push({
          element,
          type: 'horizontal',
          elementWidth: rect.width,
          parentWidth: parentRect.width,
          overflow: rect.right - parentRect.right,
          tagName: element.tagName,
          className: element.className,
          index
        });
        
        console.log(`❌ HORIZONTAL OVERFLOW:`, {
          elementInfo: element.tagName + '.' + element.className,
          elementWidth: Math.round(rect.width),
          parentWidth: Math.round(parentRect.width),
          overflow: Math.round(rect.right - parentRect.right),
          domElement: element
        });
      }
      
      // Check vertical overflow
      if (rect.bottom > parentRect.bottom || rect.top < parentRect.top) {
        element.classList.add('debug-overflow');
        element.setAttribute('data-size', `W:${Math.round(rect.width)}px H:${Math.round(rect.height)}px`);
        element.classList.add('size-info');
        
        overflowElements.push({
          element,
          type: 'vertical',
          elementHeight: rect.height,
          parentHeight: parentRect.height,
          overflow: rect.bottom - parentRect.bottom,
          tagName: element.tagName,
          className: element.className,
          index
        });
        
        console.log(`❌ VERTICAL OVERFLOW:`, {
          elementInfo: element.tagName + '.' + element.className,
          elementHeight: Math.round(rect.height),
          parentHeight: Math.round(parentRect.height),
          overflow: Math.round(rect.bottom - parentRect.bottom),
          domElement: element
        });
      }
    }
  });
  
  // Summary report
  console.log(`📊 OVERFLOW DETECTION COMPLETE:`);
  console.log(`- Total elements checked: ${allElements.length}`);
  console.log(`- Overflow elements found: ${overflowElements.length}`);
  
  if (overflowElements.length === 0) {
    console.log('✅ NO OVERFLOW DETECTED!');
  } else {
    console.log('🚨 OVERFLOW ELEMENTS:');
    overflowElements.forEach((item, i) => {
      console.log(`${i + 1}. ${item.tagName}.${item.className} - ${item.type} overflow: ${Math.round(item.overflow)}px`);
    });
  }
  
  return overflowElements;
};

export const clearOverflowDebug = () => {
  const debugElements = document.querySelectorAll('.debug-overflow, .size-info');
  debugElements.forEach(el => {
    el.classList.remove('debug-overflow', 'size-info');
    el.removeAttribute('data-size');
  });
  console.log('🧹 OVERFLOW DEBUG CLEARED');
};

// Auto-run on page load if in development
if (process.env.NODE_ENV === 'development') {
  window.detectOverflow = detectOverflow;
  window.clearOverflowDebug = clearOverflowDebug;
  
  // Auto-detect after page loads
  setTimeout(() => {
    detectOverflow();
  }, 2000);
  
  console.log('🔧 OVERFLOW DETECTOR READY! Use window.detectOverflow() and window.clearOverflowDebug()');
}