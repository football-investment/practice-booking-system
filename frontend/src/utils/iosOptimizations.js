/**
 * iOS Safari Optimization Utilities
 * Handles iOS-specific JavaScript optimizations for better performance and UX
 */

class iOSOptimizations {
  constructor() {
    this.isIOS = this.detectIOS();
    this.isSafari = this.detectSafari();
    this.deviceType = this.getDeviceType();
    
    if (this.isIOS || this.isSafari) {
      this.init();
    }
  }

  /**
   * Detect if device is iOS
   */
  detectIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  }

  /**
   * Detect if browser is Safari (including mobile Safari)
   */
  detectSafari() {
    const ua = navigator.userAgent;
    return /Safari/.test(ua) && !/Chrome|Chromium|Edge/.test(ua);
  }

  /**
   * Get specific device type for targeted optimizations
   */
  getDeviceType() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const maxDimension = Math.max(width, height);
    const minDimension = Math.min(width, height);

    // iPhone SE and similar small devices
    if (minDimension <= 375) {
      return 'iphone-se';
    }
    // iPhone 12/13/14 standard
    else if (minDimension <= 390) {
      return 'iphone-standard';
    }
    // iPhone Plus/Pro models
    else if (minDimension <= 428) {
      return 'iphone-plus';
    }
    // iPad mini
    else if (minDimension <= 768) {
      return 'ipad-mini';
    }
    // iPad standard
    else if (minDimension <= 834) {
      return 'ipad';
    }
    // iPad Pro
    else if (minDimension <= 1024) {
      return 'ipad-pro';
    }
    // iPad Pro large
    else {
      return 'ipad-pro-large';
    }
  }

  /**
   * Initialize iOS optimizations
   */
  init() {
    this.setupViewportFixes();
    this.setupScrollOptimizations();
    this.setupTouchOptimizations();
    this.setupPerformanceOptimizations();
    this.setupAccessibilityEnhancements();
    
    console.log(`🍎 iOS optimizations initialized for ${this.deviceType}`);
  }

  /**
   * Fix iOS Safari viewport issues
   */
  setupViewportFixes() {
    // Fix for iOS Safari viewport height issues
    const setVH = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
    };

    setVH();
    window.addEventListener('resize', setVH);
    window.addEventListener('orientationchange', () => {
      setTimeout(setVH, 100); // Delay to ensure proper measurement
    });

    // Add device type to body for CSS targeting
    document.body.setAttribute('data-device-type', this.deviceType);
    document.body.setAttribute('data-ios', 'true');
    
    if (this.isSafari) {
      document.body.setAttribute('data-safari', 'true');
    }
  }

  /**
   * Optimize scrolling behavior for iOS
   */
  setupScrollOptimizations() {
    // Enable momentum scrolling for specific elements
    const scrollableElements = document.querySelectorAll(
      '.modal-body, .table-responsive, .filter-tabs, .scrollable'
    );
    
    scrollableElements.forEach(element => {
      element.style.webkitOverflowScrolling = 'touch';
      element.style.overflowScrolling = 'touch';
    });

    // Prevent scroll chaining on modals
    document.addEventListener('touchmove', (e) => {
      const target = e.target.closest('.modal-content');
      if (target) {
        const scrollTop = target.scrollTop;
        const scrollHeight = target.scrollHeight;
        const height = target.clientHeight;
        const deltaY = e.touches[0].clientY - (e.touches[0].previousY || e.touches[0].clientY);

        if (deltaY < 0 && scrollTop + height >= scrollHeight) {
          e.preventDefault();
        } else if (deltaY > 0 && scrollTop <= 0) {
          e.preventDefault();
        }
      }
    }, { passive: false });
  }

  /**
   * Optimize touch interactions
   */
  setupTouchOptimizations() {
    // Prevent double-tap zoom on buttons and interactive elements
    const interactiveElements = document.querySelectorAll(
      'button, .btn, .tab, .card, input[type="submit"], input[type="button"]'
    );
    
    interactiveElements.forEach(element => {
      element.style.touchAction = 'manipulation';
      element.addEventListener('touchstart', () => {}, { passive: true });
    });

    // Improve form input behavior
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
      // Prevent zoom on input focus
      if (input.type !== 'range') {
        const currentFontSize = parseInt(window.getComputedStyle(input).fontSize);
        if (currentFontSize < 16) {
          input.style.fontSize = '16px';
        }
      }

      // Handle keyboard appearance
      input.addEventListener('focus', () => {
        this.handleKeyboardAppearance(true);
      });

      input.addEventListener('blur', () => {
        this.handleKeyboardAppearance(false);
      });
    });
  }

  /**
   * Handle virtual keyboard appearance
   */
  handleKeyboardAppearance(isVisible) {
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
      if (isVisible) {
        // Adjust viewport when keyboard appears
        viewport.setAttribute('content', 
          'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'
        );
        document.body.classList.add('keyboard-open');
      } else {
        // Restore viewport when keyboard hides
        setTimeout(() => {
          viewport.setAttribute('content', 
            'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes'
          );
          document.body.classList.remove('keyboard-open');
        }, 300);
      }
    }
  }

  /**
   * Performance optimizations for iOS
   */
  setupPerformanceOptimizations() {
    // Reduce animations on low-power mode
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.body.classList.add('reduced-motion');
    }

    // Optimize rendering for Retina displays
    if (window.devicePixelRatio > 1) {
      document.body.classList.add('retina-display');
    }

    // Debounce resize events
    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        this.handleResize();
      }, 100);
    });

    // Lazy load images more aggressively on mobile
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
              imageObserver.unobserve(img);
            }
          }
        });
      }, {
        rootMargin: '50px'
      });

      document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
      });
    }
  }

  /**
   * Handle resize events
   */
  handleResize() {
    // Update device type if orientation changed significantly
    const newDeviceType = this.getDeviceType();
    if (newDeviceType !== this.deviceType) {
      this.deviceType = newDeviceType;
      document.body.setAttribute('data-device-type', this.deviceType);
    }

    // Trigger custom resize event for components
    window.dispatchEvent(new CustomEvent('iosResize', {
      detail: { deviceType: this.deviceType }
    }));
  }

  /**
   * Accessibility enhancements for iOS
   */
  setupAccessibilityEnhancements() {
    // Improve VoiceOver support
    const focusableElements = document.querySelectorAll(
      'button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'
    );

    focusableElements.forEach(element => {
      if (!element.getAttribute('aria-label') && !element.getAttribute('aria-labelledby')) {
        const textContent = element.textContent.trim();
        if (textContent) {
          element.setAttribute('aria-label', textContent);
        }
      }
    });

    // Enhance form labels
    const labels = document.querySelectorAll('label');
    labels.forEach(label => {
      const forAttr = label.getAttribute('for');
      if (forAttr) {
        const input = document.getElementById(forAttr);
        if (input && !input.getAttribute('aria-label')) {
          input.setAttribute('aria-label', label.textContent.trim());
        }
      }
    });
  }

  /**
   * Add iOS-specific CSS classes based on device
   */
  addDeviceClasses() {
    const classes = [`ios-${this.deviceType}`];
    
    if (this.deviceType.includes('iphone')) {
      classes.push('ios-iphone');
    } else if (this.deviceType.includes('ipad')) {
      classes.push('ios-ipad');
    }

    document.body.classList.add(...classes);
  }

  /**
   * Optimize modal behavior for iOS
   */
  optimizeModals() {
    const modals = document.querySelectorAll('.modal, .modal-overlay');
    
    modals.forEach(modal => {
      // Prevent background scroll when modal is open
      modal.addEventListener('show', () => {
        document.body.style.position = 'fixed';
        document.body.style.top = `-${window.scrollY}px`;
        document.body.style.width = '100%';
      });

      modal.addEventListener('hide', () => {
        const scrollY = document.body.style.top;
        document.body.style.position = '';
        document.body.style.top = '';
        document.body.style.width = '';
        window.scrollTo(0, parseInt(scrollY || '0') * -1);
      });
    });
  }

  /**
   * Get current device orientation
   */
  getOrientation() {
    return window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
  }

  /**
   * Check if device is in Safe Area (for notched devices)
   */
  hasSafeArea() {
    const safeAreaTop = parseInt(getComputedStyle(document.documentElement)
      .getPropertyValue('--sat') || '0');
    return safeAreaTop > 20; // Likely has notch if safe area top > 20px
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.iOSOptimizations = new iOSOptimizations();
  });
} else {
  window.iOSOptimizations = new iOSOptimizations();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = iOSOptimizations;
}

export default iOSOptimizations;