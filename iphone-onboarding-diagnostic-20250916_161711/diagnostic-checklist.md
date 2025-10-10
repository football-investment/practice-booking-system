# iPhone Chrome Onboarding Diagnostic Checklist

## Issues to Test:
- [ ] **Scrolling Problems**: Page doesn't scroll smoothly or gets stuck
- [ ] **Field Accessibility**: Cannot tap/focus on nickname or other input fields  
- [ ] **Viewport Issues**: Content is cut off or not properly sized
- [ ] **Touch Targets**: Buttons/inputs too small or unresponsive
- [ ] **Keyboard Focus**: Input fields don't focus properly when tapped

## Test Steps:

### 1. Device Setup
- [ ] iPhone device (preferably iPhone 12 Pro Max or similar)
- [ ] Chrome browser installed and updated
- [ ] Network connection to 192.168.1.129:3000

### 2. Basic Navigation Test
- [ ] Open http://192.168.1.129:3000/student/onboarding in Chrome
- [ ] Verify page loads without errors
- [ ] Check if progress bar and step indicators are visible
- [ ] Test scrolling up and down on the page

### 3. Form Field Tests
- [ ] Navigate to Profile step (Step 4)
- [ ] Tap on "Becenév (nickname)" field
- [ ] Verify field gets focus (cursor appears)
- [ ] Type some text and verify it appears
- [ ] Tap on other fields (phone, emergency contact, etc.)
- [ ] Check if all fields are accessible and scrollable

### 4. Scrolling Tests  
- [ ] Scroll to different sections of the onboarding
- [ ] Verify smooth scrolling behavior
- [ ] Check if content doesn't get cut off
- [ ] Test sticky navigation at bottom

### 5. Step Navigation
- [ ] Use "Következő" (Next) and "Előző" (Previous) buttons
- [ ] Verify page scrolls to top after step changes
- [ ] Check if all steps are accessible

## Expected Behaviors:

### ✅ Working Correctly:
- Smooth touch scrolling with momentum
- All input fields focusable and typable
- Step navigation with auto-scroll to top
- Proper viewport sizing (no horizontal scroll)
- Touch targets minimum 44x44px

### ❌ Issues to Fix:
- Page doesn't scroll or scrolling is jerky
- Cannot tap or focus input fields
- Content overflows viewport
- Navigation buttons not accessible
- Keyboard covers input fields without adjustment

## Diagnostic Commands:

### Browser Console Tests:
```javascript
// Test iPhone Chrome detection
console.log('iPhone:', /iPhone/.test(navigator.userAgent));
console.log('Chrome:', navigator.userAgent.includes('chrome'));

// Test viewport
console.log('Viewport:', window.innerWidth, 'x', window.innerHeight);

// Test scrolling
console.log('Scroll position:', window.scrollY);
console.log('Scroll height:', document.body.scrollHeight);

// Test CSS support
console.log('Supports touch-action:', CSS.supports('touch-action', 'manipulation'));
console.log('Supports safe-area:', CSS.supports('padding', 'env(safe-area-inset-top)'));
```

## Solutions Applied:

### CSS Fixes:
- `align-items: flex-start` instead of `center` for scrollable layout
- `overflow-y: auto` with `-webkit-overflow-scrolling: touch`
- `min-height: 48px` for iPhone touch targets
- `font-size: 16px !important` to prevent zoom on input focus
- `position: sticky` navigation for always-accessible controls

### JavaScript Fixes:
- iPhone Chrome detection with specific optimizations
- Scroll-to-top functionality on step changes
- Enhanced viewport handling for iPhone
- Input focus management to prevent viewport jumping

### Viewport Optimization:
- `viewport-fit=cover` for notched iPhones
- `user-scalable=no` to prevent zoom issues
- Safe area inset support for proper padding
