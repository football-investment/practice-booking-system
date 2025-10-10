import React from 'react';
import './SimpleDashboard.css';

const SimpleDashboard = ({ data, userRole }) => {
  return (
    <div className="simple-dashboard">
      <div className="dashboard-cards">
        <div className="dashboard-card">
          <div className="card-icon">📚</div>
          <div className="card-content">
            <div className="card-number">3</div>
            <div className="card-label">Active Tracks</div>
          </div>
        </div>
        
        <div className="dashboard-card">
          <div className="card-icon">✅</div>
          <div className="card-content">
            <div className="card-number">12</div>
            <div className="card-label">Completed Modules</div>
          </div>
        </div>
        
        <div className="dashboard-card">
          <div className="card-icon">📅</div>
          <div className="card-content">
            <div className="card-number">2</div>
            <div className="card-label">Upcoming Sessions</div>
          </div>
        </div>
        
        <div className="dashboard-card">
          <div className="card-icon">🏆</div>
          <div className="card-content">
            <div className="card-number">1</div>
            <div className="card-label">Certificates Earned</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleDashboard;