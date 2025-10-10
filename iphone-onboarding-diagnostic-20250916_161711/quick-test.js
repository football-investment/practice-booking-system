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
