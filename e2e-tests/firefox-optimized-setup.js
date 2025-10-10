// @ts-check
/**
 * Advanced Firefox E2E Test Setup & Optimization
 * Addresses Firefox-specific stability issues and database setup
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

class FirefoxE2EOptimizer {
  constructor() {
    this.projectRoot = path.resolve(__dirname, '..');
    this.backendProcess = null;
    this.frontendProcess = null;
    this.dbInitialized = false;
  }

  /**
   * Advanced Firefox browser configuration for E2E testing
   */
  getFirefoxConfig() {
    return {
      name: 'firefox-optimized',
      use: {
        // Browser-specific optimizations
        browserName: 'firefox',
        headless: process.env.CI === 'true',
        
        // Advanced Firefox timeout optimizations
        actionTimeout: 25000,        // Extended for Firefox rendering delays
        navigationTimeout: 50000,     // Extended for Firefox navigation
        
        // Firefox-specific expect timeout
        expect: { 
          timeout: 20000,
          toHaveURL: { timeout: 25000 },
          toBeVisible: { timeout: 18000 }
        },
        
        // Firefox launch optimizations
        launchOptions: {
          firefoxUserPrefs: {
            // Disable media permissions for automation
            'media.navigator.streams.fake': true,
            'media.navigator.permission.disabled': true,
            
            // Optimize for automation
            'dom.webdriver.enabled': false,
            'useAutomationExtension': false,
            
            // Security settings for localhost testing
            'security.tls.insecure_fallback_hosts': 'localhost',
            'network.cookie.sameSite.laxByDefault': false,
            
            // Performance optimizations
            'dom.ipc.processCount': 1,
            'browser.tabs.remote.autostart': false,
            'layers.acceleration.disabled': true,
            
            // Disable Firefox features that can interfere with tests
            'browser.safebrowsing.enabled': false,
            'browser.safebrowsing.malware.enabled': false,
            'datareporting.healthreport.uploadEnabled': false,
            'datareporting.policy.dataSubmissionEnabled': false,
            
            // Network optimizations
            'network.http.max-connections': 40,
            'network.http.max-connections-per-server': 8,
            'network.prefetch-next': false
          },
          
          // Additional Firefox args for CI/automation
          args: process.env.CI ? [
            '--disable-dev-shm-usage',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
          ] : []
        },
        
        // Video recording for debugging Firefox issues
        video: process.env.CI ? 'retain-on-failure' : 'off',
        screenshot: 'only-on-failure',
        
        // Context options for better reliability
        viewport: { width: 1280, height: 720 },
        ignoreHTTPSErrors: true,
        acceptDownloads: false,
        
        // Enhanced debugging for Firefox
        trace: process.env.DEBUG ? 'on' : 'retain-on-failure'
      }
    };
  }

  /**
   * Initialize database with proper schema and test data
   */
  async initializeDatabase() {
    if (this.dbInitialized) {
      console.log('✅ Database already initialized');
      return;
    }

    console.log('🔧 Initializing database for E2E testing...');
    
    try {
      // Run Alembic migrations to create all tables
      console.log('📊 Running database migrations...');
      execSync('alembic upgrade head', {
        cwd: this.projectRoot,
        stdio: 'inherit',
        env: { ...process.env, PYTHONPATH: this.projectRoot }
      });

      // Create test users and data
      console.log('👤 Creating test users...');
      await this.createTestUsers();
      
      // Create test sessions
      console.log('📅 Creating test sessions...');
      await this.createTestSessions();

      this.dbInitialized = true;
      console.log('✅ Database initialization complete');
      
    } catch (error) {
      console.error('❌ Database initialization failed:', error.message);
      throw error;
    }
  }

  /**
   * Create test users for E2E testing
   */
  async createTestUsers() {
    const createUsersScript = `
from app.database import get_db
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.core.security import get_password_hash
from datetime import datetime, timezone, timedelta

db = next(get_db())

# Create test semester if it doesn't exist
test_semester = db.query(Semester).filter(Semester.name == 'E2E Test Semester').first()
if not test_semester:
    test_semester = Semester(
        name='E2E Test Semester',
        start_date=datetime.now(timezone.utc) - timedelta(days=30),
        end_date=datetime.now(timezone.utc) + timedelta(days=120)
    )
    db.add(test_semester)
    db.commit()
    print(f'✅ Created test semester: {test_semester.name}')

# Create E2E test student user
test_student = db.query(User).filter(User.email == 'emma.fresh@student.com').first()
if not test_student:
    test_student = User(
        name='Emma Fresh',
        email='emma.fresh@student.com',
        password_hash=get_password_hash('student123'),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,  # Important for E2E tests
        created_at=datetime.now(timezone.utc)
    )
    db.add(test_student)
    db.commit()
    db.refresh(test_student)
    print(f'✅ Created E2E test student: {test_student.name} ({test_student.email})')
else:
    # Ensure onboarding is completed
    test_student.onboarding_completed = True
    db.commit()
    print(f'✅ E2E test student exists: {test_student.name}')

# Create test instructor
test_instructor = db.query(User).filter(User.email == 'instructor.e2e@example.com').first()
if not test_instructor:
    test_instructor = User(
        name='E2E Test Instructor',
        email='instructor.e2e@example.com',
        password_hash=get_password_hash('instructor123'),
        role=UserRole.INSTRUCTOR,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(test_instructor)
    db.commit()
    db.refresh(test_instructor)
    print(f'✅ Created E2E test instructor: {test_instructor.name}')

db.close()
print('✅ All test users created/verified')
`;

    execSync(`python3 -c "${createUsersScript}"`, {
      cwd: this.projectRoot,
      env: { ...process.env, PYTHONPATH: this.projectRoot }
    });
  }

  /**
   * Create test sessions for booking tests
   */
  async createTestSessions() {
    const createSessionsScript = `
from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.user import User, UserRole
from app.models.semester import Semester
from datetime import datetime, timezone, timedelta

db = next(get_db())

# Get test instructor and semester
instructor = db.query(User).filter(User.email == 'instructor.e2e@example.com').first()
semester = db.query(Semester).filter(Semester.name == 'E2E Test Semester').first()

if not instructor or not semester:
    print('❌ Required instructor or semester not found')
    db.close()
    exit(1)

# Create future sessions for booking tests
now = datetime.now(timezone.utc)
test_sessions = [
    {
        'title': 'E2E Test Session - Available',
        'description': 'Test session for automated booking',
        'date_start': now + timedelta(days=7),
        'date_end': now + timedelta(days=7, hours=2),
        'capacity': 20,
        'location': 'E2E Test Room 1'
    },
    {
        'title': 'E2E Test Session - Large Capacity',
        'description': 'Test session with high capacity',
        'date_start': now + timedelta(days=14),
        'date_end': now + timedelta(days=14, hours=1.5),
        'capacity': 50,
        'location': 'E2E Test Room 2'
    },
    {
        'title': 'E2E Test Session - Soon',
        'description': 'Test session starting soon',
        'date_start': now + timedelta(hours=3),
        'date_end': now + timedelta(hours=5),
        'capacity': 15,
        'location': 'E2E Test Room 3'
    }
]

created_count = 0
for session_data in test_sessions:
    # Check if session already exists
    existing = db.query(SessionModel).filter(
        SessionModel.title == session_data['title']
    ).first()
    
    if not existing:
        session = SessionModel(
            title=session_data['title'],
            description=session_data['description'],
            instructor_id=instructor.id,
            semester_id=semester.id,
            date_start=session_data['date_start'],
            date_end=session_data['date_end'],
            capacity=session_data['capacity'],
            location=session_data['location']
        )
        db.add(session)
        created_count += 1

if created_count > 0:
    db.commit()
    print(f'✅ Created {created_count} test sessions')
else:
    print('✅ Test sessions already exist')

db.close()
`;

    execSync(`python3 -c "${createSessionsScript}"`, {
      cwd: this.projectRoot,
      env: { ...process.env, PYTHONPATH: this.projectRoot }
    });
  }

  /**
   * Start backend with database initialization
   */
  async startBackend() {
    console.log('🚀 Starting optimized backend for Firefox E2E testing...');
    
    // Initialize database first
    await this.initializeDatabase();
    
    return new Promise((resolve, reject) => {
      this.backendProcess = spawn('./start_backend.sh', [], {
        cwd: this.projectRoot,
        stdio: 'pipe',
        env: { ...process.env, PYTHONPATH: this.projectRoot }
      });

      let startupTimeout = setTimeout(() => {
        reject(new Error('Backend startup timeout'));
      }, 30000);

      this.backendProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log('Backend:', output.trim());
        
        // Look for startup completion indicators
        if (output.includes('Application startup complete') || 
            output.includes('Uvicorn running')) {
          clearTimeout(startupTimeout);
          resolve();
        }
      });

      this.backendProcess.stderr.on('data', (data) => {
        console.log('Backend stderr:', data.toString().trim());
      });

      this.backendProcess.on('error', (error) => {
        clearTimeout(startupTimeout);
        reject(error);
      });
    });
  }

  /**
   * Start frontend optimized for Firefox testing
   */
  async startFrontend() {
    console.log('🎨 Starting frontend for Firefox E2E testing...');
    
    return new Promise((resolve, reject) => {
      this.frontendProcess = spawn('npm', ['start'], {
        cwd: path.join(this.projectRoot, 'frontend'),
        stdio: 'pipe',
        env: { 
          ...process.env, 
          PORT: '3000',
          HOST: '0.0.0.0',
          FAST_REFRESH: 'false',
          GENERATE_SOURCEMAP: 'false'
        }
      });

      let startupTimeout = setTimeout(() => {
        reject(new Error('Frontend startup timeout'));
      }, 60000);

      this.frontendProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log('Frontend:', output.trim());
        
        if (output.includes('webpack compiled') || 
            output.includes('compiled successfully')) {
          clearTimeout(startupTimeout);
          // Wait additional 2 seconds for full startup
          setTimeout(resolve, 2000);
        }
      });

      this.frontendProcess.stderr.on('data', (data) => {
        const output = data.toString();
        // Only log actual errors, not warnings
        if (output.includes('ERROR') || output.includes('Failed')) {
          console.log('Frontend stderr:', output.trim());
        }
      });

      this.frontendProcess.on('error', (error) => {
        clearTimeout(startupTimeout);
        reject(error);
      });
    });
  }

  /**
   * Firefox-specific test health check
   */
  async waitForServices() {
    console.log('🔍 Performing Firefox-optimized health checks...');
    
    const checkService = async (url, name, maxRetries = 10) => {
      for (let i = 0; i < maxRetries; i++) {
        try {
          const response = await fetch(url);
          if (response.ok) {
            console.log(`✅ ${name} health check passed`);
            return true;
          }
        } catch (error) {
          // Service not ready yet
        }
        
        console.log(`⏳ Waiting for ${name}... (${i + 1}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
      throw new Error(`${name} health check failed after ${maxRetries} attempts`);
    };

    // Check backend
    await checkService('http://localhost:8000/api/v1/debug/health', 'Backend API');
    
    // Check frontend
    await checkService('http://localhost:3000', 'Frontend');
    
    console.log('✅ All services ready for Firefox E2E testing');
  }

  /**
   * Start all services for Firefox E2E testing
   */
  async startAll() {
    try {
      console.log('🦊 Starting Firefox-optimized E2E test environment...');
      
      // Start services in parallel for faster startup
      await Promise.all([
        this.startBackend(),
        this.startFrontend()
      ]);
      
      // Wait for services to be fully ready
      await this.waitForServices();
      
      console.log('🎉 Firefox E2E test environment ready!');
      console.log('🔗 Frontend: http://localhost:3000');
      console.log('🔗 Backend API: http://localhost:8000');
      console.log('📚 API Docs: http://localhost:8000/docs');
      
    } catch (error) {
      console.error('❌ Failed to start Firefox E2E environment:', error.message);
      await this.cleanup();
      throw error;
    }
  }

  /**
   * Cleanup processes
   */
  async cleanup() {
    console.log('🧹 Cleaning up Firefox E2E test environment...');
    
    if (this.backendProcess) {
      this.backendProcess.kill('SIGTERM');
      this.backendProcess = null;
    }
    
    if (this.frontendProcess) {
      this.frontendProcess.kill('SIGTERM');
      this.frontendProcess = null;
    }
    
    console.log('✅ Cleanup complete');
  }

  /**
   * Generate Firefox-optimized test helpers
   */
  getFirefoxTestHelpers() {
    return {
      // Firefox-aware timeout function
      getFirefoxTimeout: (page, baseTimeout = 10000) => {
        const isFirefox = page.context().browser().browserType().name() === 'firefox';
        return isFirefox ? Math.floor(baseTimeout * 1.5) : baseTimeout;
      },

      // Firefox-specific element waiting
      waitForElementFirefox: async (page, selector, options = {}) => {
        const isFirefox = page.context().browser().browserType().name() === 'firefox';
        const timeout = isFirefox ? (options.timeout || 15000) * 1.2 : (options.timeout || 10000);
        
        return await page.waitForSelector(selector, { ...options, timeout });
      },

      // Firefox-optimized login
      performFirefoxLogin: async (page, email = 'emma.fresh@student.com', password = 'student123') => {
        const isFirefox = page.context().browser().browserType().name() === 'firefox';
        const baseTimeout = isFirefox ? 20000 : 15000;
        
        await page.goto('/login');
        
        // Wait for login form with Firefox timeout
        await page.waitForSelector('[data-testid="email"]', { timeout: baseTimeout });
        
        // Fill credentials with Firefox-specific delays
        await page.fill('[data-testid="email"]', email);
        if (isFirefox) await page.waitForTimeout(100); // Small delay for Firefox
        
        await page.fill('[data-testid="password"]', password);
        if (isFirefox) await page.waitForTimeout(100);
        
        // Click login and wait for navigation
        await page.click('[data-testid="login-button"]');
        
        // Firefox-specific navigation wait
        await page.waitForURL(/\/student/, { timeout: baseTimeout });
        
        console.log('✅ Firefox-optimized login successful');
        return true;
      }
    };
  }
}

module.exports = { FirefoxE2EOptimizer };