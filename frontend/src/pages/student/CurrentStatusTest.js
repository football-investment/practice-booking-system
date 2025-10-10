import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import CurrentSpecializationStatus from '../../components/onboarding/CurrentSpecializationStatus';
import AppHeader from '../../components/common/AppHeader';

const CurrentStatusTest = () => {
    const { user } = useAuth();

    const handleNext = () => {
        console.log('Next button clicked - proceeding to specialization selection');
        // This would normally navigate to the next step
    };

    return (
        <div className="current-status-test-page">
            <AppHeader />
            <div className="page-content">
                <CurrentSpecializationStatus 
                    onNext={handleNext}
                    hideNavigation={false}
                />
            </div>
        </div>
    );
};

export default CurrentStatusTest;