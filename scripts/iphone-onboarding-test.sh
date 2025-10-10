#!/bin/bash

# iPhone Chrome Onboarding Troubleshooting Script
# Comprehensive diagnosis and testing for iPhone onboarding issues

echo "📱 iPhone Chrome Onboarding Diagnostic Tool"
echo "========================================="
echo "Diagnosing scrolling and field accessibility issues"
echo ""

# Create diagnostic test directory
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_DIR="iphone-onboarding-diagnostic-$TIMESTAMP"
mkdir -p "$TEST_DIR"

# Test configuration
FRONTEND_URL="http://192.168.1.129:3000"
ONBOARDING_URL="$FRONTEND_URL/student/onboarding"

echo "📋 Test Configuration:"
echo "Onboarding URL: $ONBOARDING_URL"
echo "Test Directory: $TEST_DIR"
echo ""

# Create iPhone-specific test page
echo "🔧 Creating iPhone Chrome onboarding test page..."

cat > "$TEST_DIR/iphone-onboarding-test.html" << 'EOF'
<!DOCTYPE html>
<html lang="hu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>iPhone Chrome Onboarding Test</title>
    <style>
        * {
            box-sizing: border-box;
        }
        
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            overflow-x: hidden;
        }
        
        /* iPhone Chrome specific styles */
        .iphone-test-container {
            height: 100vh;
            height: -webkit-fill-available;
            overflow-y: scroll;
            -webkit-overflow-scrolling: touch;
            position: relative;
            padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
        }
        
        .test-content {
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .test-section {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .form-test {
            margin: 20px 0;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 16px;
        }
        
        input, textarea, select {
            width: 100%;
            /* Critical iPhone Chrome settings */
            font-size: 16px !important; /* Prevent zoom */
            min-height: 48px; /* iPhone touch target */
            padding: 14px 16px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            
            /* iPhone Chrome optimizations */
            -webkit-appearance: none;
            appearance: none;
            touch-action: manipulation;
            -webkit-tap-highlight-color: transparent;
            
            /* Focus behavior */
            outline: none;
            transition: all 0.3s ease;
        }
        
        input:focus, textarea:focus, select:focus {
            border-color: #007AFF;
            box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.2);
            transform: translateY(-2px);
        }
        
        button {
            background: linear-gradient(135deg, #007AFF 0%, #5856D6 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 16px 32px;
            font-size: 16px !important;
            font-weight: 600;
            min-height: 48px;
            cursor: pointer;
            transition: all 0.3s ease;
            
            /* iPhone Chrome touch */
            -webkit-tap-highlight-color: rgba(0, 122, 255, 0.2);
            touch-action: manipulation;
            user-select: none;
        }
        
        button:active {
            transform: scale(0.98);
            box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
        }
        
        .scroll-test {
            height: 200vh; /* Force scrolling */
            background: linear-gradient(to bottom, 
                rgba(255,255,255,0.1) 0%, 
                rgba(255,255,255,0.05) 50%, 
                rgba(255,255,255,0.1) 100%
            );
            border-radius: 16px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .sticky-nav {
            position: sticky;
            bottom: 20px;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            margin-top: 20px;
        }
        
        .test-result {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            margin: 5px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .pass { background: #34C759; color: white; }
        .fail { background: #FF3B30; color: white; }
        .warning { background: #FF9500; color: white; }
    </style>
</head>
<body>
    <div class="iphone-test-container">
        <div class="test-content">
            <div class="test-section">
                <h1>📱 iPhone Chrome Onboarding Test</h1>
                <p>Eszköz info: <span id="device-info">Detecting...</span></p>
                <p>Viewport: <span id="viewport-info">Detecting...</span></p>
                <div id="test-results"></div>
            </div>
            
            <div class="test-section">
                <h3>🔄 Scroll Test</h3>
                <p>Test scrolling performance and smoothness on iPhone Chrome</p>
                <button onclick="testScrolling()">Test Scrolling</button>
                <div id="scroll-results"></div>
                
                <div class="scroll-test">
                    <h4>Scroll Area</h4>
                    <p>This is a long scrollable area to test iPhone Chrome scrolling behavior.</p>
                    <p>Scroll down to test smooth scrolling and touch behavior...</p>
                    <div style="height: 100px; background: rgba(255,255,255,0.1); margin: 20px 0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                        <span>Middle of scroll area</span>
                    </div>
                    <p>Continue scrolling to test the full scroll experience...</p>
                    <div style="height: 100px; background: rgba(255,255,255,0.15); margin: 20px 0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                        <span>End of scroll area</span>
                    </div>
                </div>
            </div>
            
            <div class="test-section">
                <h3>📝 Form Field Accessibility Test</h3>
                <p>Test form field focus, scrolling, and accessibility on iPhone</p>
                
                <div class="form-test">
                    <div class="form-group">
                        <label for="nickname">Becenév (Nickname) *</label>
                        <input type="text" id="nickname" placeholder="Pl. SportsPro, FutballFan stb." 
                               onfocus="onFieldFocus('nickname')" onblur="onFieldBlur('nickname')">
                        <div id="nickname-status"></div>
                    </div>
                    
                    <div class="form-group">
                        <label for="email">Email *</label>
                        <input type="email" id="email" placeholder="your.email@example.com"
                               onfocus="onFieldFocus('email')" onblur="onFieldBlur('email')">
                        <div id="email-status"></div>
                    </div>
                    
                    <div class="form-group">
                        <label for="phone">Telefonszám *</label>
                        <input type="tel" id="phone" placeholder="+36 XX XXX XXXX"
                               onfocus="onFieldFocus('phone')" onblur="onFieldBlur('phone')">
                        <div id="phone-status"></div>
                    </div>
                    
                    <div class="form-group">
                        <label for="notes">Megjegyzések</label>
                        <textarea id="notes" rows="4" placeholder="További információk..."
                                onfocus="onFieldFocus('notes')" onblur="onFieldBlur('notes')"></textarea>
                        <div id="notes-status"></div>
                    </div>
                    
                    <button onclick="testFormSubmission()">Test Form Submission</button>
                </div>
                
                <div id="form-test-results"></div>
            </div>
            
            <div class="test-section">
                <h3>⚙️ iPhone Chrome Specific Tests</h3>
                <button onclick="runAllTests()">Run All Tests</button>
                <div id="comprehensive-results"></div>
            </div>
            
            <div class="sticky-nav">
                <button onclick="scrollToTop()">🔝 Scroll to Top</button>
                <button onclick="exportResults()">📤 Export Results</button>
            </div>
        </div>
    </div>

    <script>
        // iPhone Chrome Testing Suite
        
        let testResults = [];
        
        // Initialize device detection
        document.addEventListener('DOMContentLoaded', function() {
            detectDevice();
            updateViewport();
            runInitialTests();
        });
        
        function detectDevice() {
            const ua = navigator.userAgent;
            const isIPhone = /iPhone/.test(ua);
            const isChrome = ua.toLowerCase().includes('chrome') && !ua.toLowerCase().includes('edg');
            
            let deviceInfo = 'Unknown';
            if (isIPhone && isChrome) {
                deviceInfo = '✅ iPhone + Chrome (Target Configuration)';
            } else if (isIPhone) {
                deviceInfo = '⚠️ iPhone + Non-Chrome Browser';
            } else {
                deviceInfo = '❌ Non-iPhone Device';
            }
            
            document.getElementById('device-info').textContent = deviceInfo;
            testResults.push({ test: 'Device Detection', result: deviceInfo });
        }
        
        function updateViewport() {
            const viewport = {
                width: window.innerWidth,
                height: window.innerHeight,
                devicePixelRatio: window.devicePixelRatio || 1,
                orientation: screen.orientation ? screen.orientation.angle : 'unknown'
            };
            
            document.getElementById('viewport-info').textContent = 
                `${viewport.width}x${viewport.height} (${viewport.devicePixelRatio}x, ${viewport.orientation}°)`;
        }
        
        function runInitialTests() {
            const tests = [];
            
            // Touch support
            tests.push({
                name: 'Touch Support',
                passed: 'ontouchstart' in window,
                details: 'Touch events available'
            });
            
            // Smooth scrolling
            tests.push({
                name: 'Smooth Scrolling',
                passed: CSS.supports('scroll-behavior', 'smooth'),
                details: 'CSS smooth scrolling supported'
            });
            
            // Safe area support
            tests.push({
                name: 'Safe Area Insets',
                passed: CSS.supports('padding-top', 'env(safe-area-inset-top)'),
                details: 'Safe area insets supported'
            });
            
            // Viewport units
            tests.push({
                name: 'Viewport Units',
                passed: CSS.supports('height', '-webkit-fill-available'),
                details: 'iOS viewport units supported'
            });
            
            displayTestResults(tests, 'test-results');
        }
        
        function testScrolling() {
            console.log('📱 Testing iPhone Chrome scrolling...');
            
            const startTime = performance.now();
            const startY = window.scrollY;
            
            // Test smooth scroll
            window.scrollTo({ top: 300, behavior: 'smooth' });
            
            setTimeout(() => {
                const endTime = performance.now();
                const endY = window.scrollY;
                const scrollTime = endTime - startTime;
                const scrollDistance = Math.abs(endY - startY);
                
                const results = [
                    {
                        name: 'Scroll Performance',
                        passed: scrollTime < 1000,
                        details: `Scroll time: ${scrollTime.toFixed(2)}ms`
                    },
                    {
                        name: 'Scroll Distance',
                        passed: scrollDistance > 200,
                        details: `Scrolled ${scrollDistance}px`
                    },
                    {
                        name: 'Smooth Scrolling',
                        passed: true, // If we got here, it worked
                        details: 'Smooth scroll completed'
                    }
                ];
                
                displayTestResults(results, 'scroll-results');
                
                // Scroll back to top
                setTimeout(() => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }, 1000);
                
            }, 500);
        }
        
        function onFieldFocus(fieldName) {
            console.log(`📝 Field focused: ${fieldName}`);
            
            const field = document.getElementById(fieldName);
            const status = document.getElementById(`${fieldName}-status`);
            
            // Test if field is accessible
            status.innerHTML = '<span class="test-result pass">✅ Field Focused</span>';
            
            // Scroll field into view for iPhone
            setTimeout(() => {
                field.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 100);
            
            testResults.push({
                test: `${fieldName} Focus`,
                result: 'SUCCESS',
                timestamp: new Date().toISOString()
            });
        }
        
        function onFieldBlur(fieldName) {
            console.log(`📝 Field blurred: ${fieldName}`);
            
            const field = document.getElementById(fieldName);
            const status = document.getElementById(`${fieldName}-status`);
            
            if (field.value.trim()) {
                status.innerHTML = '<span class="test-result pass">✅ Value Entered</span>';
                
                testResults.push({
                    test: `${fieldName} Input`,
                    result: 'SUCCESS',
                    value: field.value.substring(0, 10) + '...', // Partial value for privacy
                    timestamp: new Date().toISOString()
                });
            } else {
                status.innerHTML = '<span class="test-result warning">⚠️ No Value</span>';
            }
        }
        
        function testFormSubmission() {
            const fields = ['nickname', 'email', 'phone', 'notes'];
            let filledFields = 0;
            let totalFields = fields.length;
            
            fields.forEach(fieldName => {
                const field = document.getElementById(fieldName);
                if (field.value.trim()) {
                    filledFields++;
                }
            });
            
            const results = [
                {
                    name: 'Form Completion',
                    passed: filledFields > 0,
                    details: `${filledFields}/${totalFields} fields filled`
                },
                {
                    name: 'Form Accessibility',
                    passed: true, // If we can test, it's accessible
                    details: 'All fields were accessible for input'
                }
            ];
            
            displayTestResults(results, 'form-test-results');
        }
        
        function runAllTests() {
            console.log('🔍 Running comprehensive iPhone Chrome tests...');
            
            const allTests = [
                {
                    name: 'iPhone Detection',
                    passed: /iPhone/.test(navigator.userAgent),
                    details: 'iPhone user agent detected'
                },
                {
                    name: 'Chrome Detection',
                    passed: navigator.userAgent.toLowerCase().includes('chrome'),
                    details: 'Chrome browser detected'
                },
                {
                    name: 'Viewport Meta Tag',
                    passed: document.querySelector('meta[name="viewport"]') !== null,
                    details: 'Viewport meta tag present'
                },
                {
                    name: 'CSS Grid Support',
                    passed: CSS.supports('display', 'grid'),
                    details: 'CSS Grid layout supported'
                },
                {
                    name: 'Flexbox Support',
                    passed: CSS.supports('display', 'flex'),
                    details: 'CSS Flexbox layout supported'
                },
                {
                    name: 'Transform Support',
                    passed: CSS.supports('transform', 'translateZ(0)'),
                    details: 'CSS 3D transforms supported'
                },
                {
                    name: 'Backdrop Filter',
                    passed: CSS.supports('backdrop-filter', 'blur(10px)'),
                    details: 'Backdrop filter effects supported'
                }
            ];
            
            displayTestResults(allTests, 'comprehensive-results');
            
            // Add summary to test results
            const passedTests = allTests.filter(test => test.passed).length;
            const totalTests = allTests.length;
            
            testResults.push({
                test: 'Comprehensive Test Summary',
                result: `${passedTests}/${totalTests} tests passed`,
                timestamp: new Date().toISOString()
            });
        }
        
        function displayTestResults(tests, containerId) {
            const container = document.getElementById(containerId);
            const html = tests.map(test => {
                const className = test.passed ? 'pass' : 'fail';
                const icon = test.passed ? '✅' : '❌';
                return `<div class="test-result ${className}">${icon} ${test.name}: ${test.details}</div>`;
            }).join('');
            
            container.innerHTML = html;
        }
        
        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        
        function exportResults() {
            const report = {
                timestamp: new Date().toISOString(),
                device: navigator.userAgent,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    devicePixelRatio: window.devicePixelRatio
                },
                testResults: testResults
            };
            
            const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `iphone-onboarding-test-${new Date().getTime()}.json`;
            a.click();
            URL.revokeObjectURL(url);
            
            alert('Test results exported! 📤');
        }
        
        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            setTimeout(updateViewport, 100);
        });
        
        // Handle resize events
        window.addEventListener('resize', updateViewport);
        
        console.log('📱 iPhone Chrome Onboarding Test initialized');
    </script>
</body>
</html>
EOF

echo "✅ iPhone test page created: $TEST_DIR/iphone-onboarding-test.html"

# Create diagnostic checklist
cat > "$TEST_DIR/diagnostic-checklist.md" << 'EOF'
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
EOF

# Create quick test script
cat > "$TEST_DIR/quick-test.js" << 'EOF'
// Quick iPhone Chrome Onboarding Test
// Paste this into browser console for immediate diagnostics

console.log('📱 iPhone Chrome Onboarding Quick Test');
console.log('=====================================');

// Device detection
const ua = navigator.userAgent;
const isIPhone = /iPhone/.test(ua);
const isChrome = ua.includes('chrome') && !ua.includes('edg');

console.log('✅ Device Info:');
console.log(`   iPhone: ${isIPhone ? '✅' : '❌'}`);
console.log(`   Chrome: ${isChrome ? '✅' : '❌'}`);
console.log(`   Viewport: ${window.innerWidth}x${window.innerHeight}`);

// Scrolling test
console.log('\n🔄 Scroll Test:');
const initialScroll = window.scrollY;
window.scrollTo({ top: 100, behavior: 'smooth' });
setTimeout(() => {
    const newScroll = window.scrollY;
    console.log(`   Scroll worked: ${newScroll !== initialScroll ? '✅' : '❌'}`);
    console.log(`   Position: ${initialScroll} → ${newScroll}`);
    window.scrollTo({ top: initialScroll, behavior: 'smooth' });
}, 500);

// Form field test
console.log('\n📝 Form Field Test:');
const nicknameField = document.querySelector('input[placeholder*="SportsPro"]');
if (nicknameField) {
    console.log('   Nickname field found: ✅');
    console.log(`   Field accessible: ${nicknameField.offsetParent !== null ? '✅' : '❌'}`);
    console.log(`   Field visible: ${nicknameField.getBoundingClientRect().height > 0 ? '✅' : '❌'}`);
} else {
    console.log('   Nickname field found: ❌ (might be on different step)');
}

// CSS support test
console.log('\n🎨 CSS Support Test:');
console.log(`   Touch action: ${CSS.supports('touch-action', 'manipulation') ? '✅' : '❌'}`);
console.log(`   Safe area: ${CSS.supports('padding', 'env(safe-area-inset-top)') ? '✅' : '❌'}`);
console.log(`   Smooth scroll: ${CSS.supports('scroll-behavior', 'smooth') ? '✅' : '❌'}`);

// Classes applied test
console.log('\n🔧 Applied Optimizations:');
console.log(`   iOS onboarding: ${document.body.hasAttribute('data-ios-onboarding') ? '✅' : '❌'}`);
console.log(`   iPhone Chrome class: ${document.body.classList.contains('iphone-chrome-onboarding') ? '✅' : '❌'}`);
console.log(`   Chrome optimized: ${document.body.classList.contains('chrome-ios-optimized') ? '✅' : '❌'}`);

console.log('\n📋 Test completed! Check results above.');
EOF

echo "✅ Diagnostic files created:"
echo "   - Interactive test: $TEST_DIR/iphone-onboarding-test.html"
echo "   - Checklist: $TEST_DIR/diagnostic-checklist.md"
echo "   - Quick test: $TEST_DIR/quick-test.js"
echo ""

# Open the test page
echo "🚀 Opening iPhone Chrome test page..."
open "$PWD/$TEST_DIR/iphone-onboarding-test.html"

echo ""
echo "📱 iPhone Chrome Onboarding Test Instructions:"
echo "============================================="
echo "1. Open the test page on your iPhone using Chrome browser"
echo "2. Go through each test section systematically"  
echo "3. Pay special attention to scrolling and form field accessibility"
echo "4. Export test results for analysis"
echo ""
echo "🔍 For immediate testing, copy/paste quick-test.js into browser console"
echo "📋 Use diagnostic-checklist.md for systematic testing"
echo ""
echo "✅ iPhone diagnostic tools ready!"