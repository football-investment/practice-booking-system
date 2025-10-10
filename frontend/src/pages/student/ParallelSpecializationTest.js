import React from 'react';
import ParallelSpecializationSelector from '../../components/onboarding/ParallelSpecializationSelector';

const ParallelSpecializationTest = () => {
  const handleSelectionUpdate = (selectedSpecs) => {
    console.log('🎓 Selected specializations:', selectedSpecs);
  };

  const handleNext = () => {
    console.log('▶️ Next button clicked');
  };

  const handleBack = () => {
    console.log('◀️ Back button clicked');
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'var(--color-background, #f7fafc)',
      padding: '20px' 
    }}>
      <div style={{ 
        maxWidth: '1200px', 
        margin: '0 auto',
        background: 'white',
        borderRadius: '16px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        padding: '40px'
      }}>
        <div style={{ 
          textAlign: 'center', 
          marginBottom: '30px',
          borderBottom: '2px solid #e2e8f0',
          paddingBottom: '20px'
        }}>
          <h1 style={{ 
            color: '#1a202c', 
            fontSize: '2.5rem', 
            marginBottom: '10px',
            fontWeight: '700'
          }}>
            🎓 Párhuzamos Specializációs Teszt
          </h1>
          <p style={{ 
            color: '#718096', 
            fontSize: '1.2rem',
            margin: '0'
          }}>
            Teljes frontend komponens demonstráció
          </p>
        </div>

        <ParallelSpecializationSelector
          onSelectionUpdate={handleSelectionUpdate}
          onNext={handleNext}
          onBack={handleBack}
          hideNavigation={false}
          showProgressionInfo={true}
        />
        
        <div style={{
          marginTop: '40px',
          padding: '20px',
          background: '#f0f9ff',
          border: '2px solid #0ea5e9',
          borderRadius: '12px',
          color: '#0c4a6e'
        }}>
          <strong>🔧 Debug Info:</strong>
          <br />
          Nyisd meg a Developer Console-t (F12) a kiválasztott specializációk követéséhez.
          <br />
          API hívások valós időben történnek a backend-del.
        </div>
      </div>
    </div>
  );
};

export default ParallelSpecializationTest;