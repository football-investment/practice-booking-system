import React, { useState } from 'react';
import EnrollmentQuizModal from '../components/student/EnrollmentQuizModal';
import './ModalTestPage.css';

const ModalTestPage = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Mock project data for testing
  const mockProject = {
    id: 1,
    title: "Test Project - Enrollment Modal",
    description: "This is a test project for debugging the enrollment quiz modal",
    max_participants: 10,
    current_participants: 5,
    xp_reward: 100,
    status: "active"
  };

  const openModal = () => {
    console.log('🚀 Opening modal...');
    console.log('Modal state before:', isModalOpen);
    setIsModalOpen(true);
    
    // Update debug info
    setTimeout(() => {
      const bodyOverflow = document.body.style.overflow;
      const debugElement = document.getElementById('body-overflow-debug');
      if (debugElement) {
        debugElement.textContent = bodyOverflow || 'default';
      }
      console.log('🔍 Body overflow style:', bodyOverflow);
      console.log('🔍 Modal elements in DOM:', document.querySelectorAll('.modal-overlay').length);
    }, 100);
  };

  const closeModal = () => {
    console.log('❌ Closing modal...');
    console.log('Modal state before:', isModalOpen);
    setIsModalOpen(false);
    
    // Update debug info
    setTimeout(() => {
      const bodyOverflow = document.body.style.overflow;
      const debugElement = document.getElementById('body-overflow-debug');
      if (debugElement) {
        debugElement.textContent = bodyOverflow || 'default';
      }
      console.log('🔍 Body overflow after close:', bodyOverflow);
    }, 100);
  };

  return (
    <div className="modal-test-page">
      <div className="test-header">
        <h1>🧪 Modal Test Page</h1>
        <p>Isolated testing environment for EnrollmentQuizModal debugging</p>
      </div>

      <div className="test-content">
        <div className="test-section">
          <h2>Modal State: {isModalOpen ? '🟢 OPEN' : '🔴 CLOSED'}</h2>
          
          <div className="test-controls">
            <button 
              onClick={openModal}
              className="test-btn primary"
              disabled={isModalOpen}
            >
              🚀 Open Enrollment Modal
            </button>
            
            <button 
              onClick={closeModal}
              className="test-btn secondary"
              disabled={!isModalOpen}
            >
              ❌ Close Modal (Direct)
            </button>
          </div>
        </div>

        <div className="test-info">
          <h3>🔍 Debug Information</h3>
          <div className="debug-panel">
            <div className="debug-item">
              <strong>Modal Open State:</strong> 
              <span className={isModalOpen ? 'status-open' : 'status-closed'}>
                {isModalOpen ? 'TRUE' : 'FALSE'}
              </span>
            </div>
            <div className="debug-item">
              <strong>Body Overflow:</strong> 
              <span id="body-overflow-debug">
                {typeof document !== 'undefined' ? document.body.style.overflow || 'default' : 'N/A'}
              </span>
            </div>
            <div className="debug-item">
              <strong>Test Project ID:</strong> 
              <span>{mockProject.id}</span>
            </div>
          </div>
        </div>

        <div className="test-instructions">
          <h3>📋 Testing Checklist</h3>
          <ul>
            <li>✅ Click "Open Enrollment Modal" button</li>
            <li>🔍 Verify modal appears as overlay (not inline)</li>
            <li>🎯 Check backdrop blur and dark overlay</li>
            <li>📱 Test click outside modal to close</li>
            <li>⌨️ Test Escape key to close</li>
            <li>🔒 Verify body scroll is locked when modal open</li>
            <li>📊 Check console for any errors</li>
          </ul>
        </div>
      </div>

      {/* The actual modal component being tested */}
      <EnrollmentQuizModal
        isOpen={isModalOpen}
        onClose={closeModal}
        project={mockProject}
      />
    </div>
  );
};

export default ModalTestPage;