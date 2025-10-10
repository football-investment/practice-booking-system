import React from 'react';
import SessionCard from '../student/SessionCard';
import './InstructorSessionCard.css';

const InstructorSessionCard = ({ 
  session, 
  onViewDetails, 
  onEdit, 
  onDelete,
  onAttendance,
  ...props 
}) => {
  return (
    <div className="instructor-session-card-wrapper">
      <SessionCard
        session={session}
        onViewDetails={onViewDetails}
        onBook={onAttendance} // Use the onBook prop for attendance tracking
        isBooking={false}
        {...props}
      />
      
      {/* Instructor Actions Overlay */}
      <div className="instructor-actions">
        <button 
          onClick={() => onEdit(session)}
          className="action-btn edit-btn"
          title="Edit Session"
        >
          ✏️
        </button>
        
        <button 
          onClick={() => onDelete(session.id)}
          className="action-btn delete-btn"
          title="Delete Session"
        >
          🗑️
        </button>
        
        <button 
          onClick={() => onAttendance(session)}
          className="action-btn attendance-btn"
          title="Manage Attendance"
        >
          📊
        </button>
      </div>
    </div>
  );
};

export default InstructorSessionCard;