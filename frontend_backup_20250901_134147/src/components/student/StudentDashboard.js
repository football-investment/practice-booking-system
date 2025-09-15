import React, { useState, useEffect } from "react";
import { apiService } from "../../services/apiService";
import { useAuth } from "../../contexts/AuthContext";
import BookingModal from "./BookingModal";
import ProfileModal from "./ProfileModal";
import FeedbackModal from "./FeedbackModal";
import CheckinModal from "./CheckinModal";
import "./StudentDashboard.css";

const StudentDashboard = () => {
  const { user, logout } = useAuth();

  // Core State
  const [bookings, setBookings] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeSemester, setActiveSemester] = useState(null);

  // Statistics State
  const [statistics, setStatistics] = useState({
    totalUsers: 0,
    totalSessions: 0,
    availableSessions: 0,
    myBookings: 0,
  });
  const [statisticsLoading, setStatisticsLoading] = useState(false);

  // Modal States
  const [selectedSession, setSelectedSession] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [showCheckinModal, setShowCheckinModal] = useState(false);
  const [showBookingHistoryModal, setShowBookingHistoryModal] = useState(false);

  // Message States
  const [successMessage, setSuccessMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    loadStudentData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(loadStudentData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStudentData = async () => {
    try {
      setLoading(true);
      setStatisticsLoading(true);
      setError(null);

      // Load active semester first
      const activeSemesterData = await apiService.getActiveSemester();
      setActiveSemester(activeSemesterData);

      const [bookingsData, sessionsData, statisticsData] = await Promise.all([
        apiService.getMyBookings(),
        activeSemesterData
          ? apiService.getSessions({ semester_id: activeSemesterData.id })
          : apiService.getSessions(),
        activeSemesterData
          ? apiService.getStatistics(activeSemesterData.id)
          : apiService.getStatistics(),
      ]);

      setBookings(bookingsData || []);
      setSessions(sessionsData || []);

      // Enhanced statistics
      setStatistics({
        totalUsers: statisticsData?.totalUsers || 0,
        totalSessions:
          statisticsData?.totalSessions || sessionsData?.length || 0,
        availableSessions: (sessionsData || []).filter(
          (session) => session.status === "available" || !session.is_full
        ).length,
        myBookings: bookingsData?.length || 0,
      });
    } catch (err) {
      console.error("Error loading student data:", err);
      setError("Failed to load dashboard data");
      setErrorMessage(
        "Failed to load dashboard data. Please refresh the page."
      );
    } finally {
      setLoading(false);
      setStatisticsLoading(false);
    }
  };

  const handleBookSession = async (session) => {
    try {
      await apiService.bookSession(session.id);
      setSuccessMessage(`Successfully booked: ${session.name}`);
      setSelectedSession(null);
      loadStudentData(); // Refresh data
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || "Failed to book session");
    }
  };

  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm("Are you sure you want to cancel this booking?"))
      return;

    try {
      await apiService.cancelBooking(bookingId);
      setSuccessMessage("Booking cancelled successfully");
      loadStudentData(); // Refresh data
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || "Failed to cancel booking");
    }
  };

  const clearMessages = () => {
    setSuccessMessage(null);
    setErrorMessage(null);
  };

  useEffect(() => {
    if (successMessage || errorMessage) {
      const timer = setTimeout(clearMessages, 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage, errorMessage]);

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-container">
        <div className="error-message">
          <h3>Error Loading Dashboard</h3>
          <p>{error}</p>
          <button onClick={loadStudentData} className="btn btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="header">
        <h1>Student Dashboard</h1>
        <div className="user-info">
          <div className="avatar" onClick={() => setShowProfileModal(true)}>
            {user?.name?.charAt(0)?.toUpperCase() || "S"}
          </div>
          <div>
            <div className="user-name">Welcome, {user?.name || "Student"}!</div>
            <div className="user-role">Role: {user?.role || "student"}</div>
            <div className="user-role">
              Email: {user?.email || "student@example.com"}
            </div>
          </div>
          <button onClick={logout} className="btn btn-danger">
            Logout
          </button>
        </div>
      </div>

      {/* Messages */}
      {successMessage && (
        <div className="success-message">
          ✅ {successMessage}
          <button onClick={clearMessages} className="close-button">
            &times;
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="error-message">
          ❌ {errorMessage}
          <button onClick={clearMessages} className="close-button">
            &times;
          </button>
        </div>
      )}

      {/* Statistics Cards */}
      <div className="quick-stats">
        <div className="stat-card">
          {statisticsLoading ? (
            <div className="loading-spinner"></div>
          ) : (
            <>
              <span className="stat-title">Total Users</span>
              <span className="stat-value">{statistics.totalUsers}</span>
              <span className="stat-change">System wide</span>
            </>
          )}
        </div>

        <div className="stat-card">
          {statisticsLoading ? (
            <div className="loading-spinner"></div>
          ) : (
            <>
              <span className="stat-title">Total Sessions</span>
              <span className="stat-value">{statistics.totalSessions}</span>
              <span className="stat-change">All sessions</span>
            </>
          )}
        </div>

        <div className="stat-card">
          {statisticsLoading ? (
            <div className="loading-spinner"></div>
          ) : (
            <>
              <span className="stat-title">Available Sessions</span>
              <span className="stat-value">{statistics.availableSessions}</span>
              <span className="stat-change">Ready to book</span>
            </>
          )}
        </div>

        <div className="stat-card">
          {statisticsLoading ? (
            <div className="loading-spinner"></div>
          ) : (
            <>
              <span className="stat-title">My Bookings</span>
              <span className="stat-value">{statistics.myBookings}</span>
              <span className="stat-change">Your bookings</span>
            </>
          )}
        </div>
      </div>

      <div className="main-content">
        {/* Available Sessions */}
        <div className="content-card">
          <div className="content-card-header">
            <h2>🏛️ Available Sessions</h2>
            <button onClick={loadStudentData} className="btn btn-secondary">
              🔄 Refresh
            </button>
          </div>

          <div className="content-card-body">
            {sessions.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📚</div>
                <h3>No Sessions Available</h3>
                <p>No sessions are currently available for booking.</p>
              </div>
            ) : (
              sessions.map((session) => (
                <div key={session.id} className="session-item">
                  <div className="session-info">
                    <h3>{session.name}</h3>
                    <div className="session-meta">
                      <span>
                        📅 Date: {new Date(session.date).toLocaleDateString()}
                      </span>
                      <span>
                        🕐 Mode: {session.mode?.toUpperCase() || "OFFLINE"}
                      </span>
                      <span>👥 Capacity: {session.capacity}</span>
                    </div>
                  </div>
                  <div className="session-actions">
                    <span
                      className={`status-badge ${
                        session.is_full ? "status-full" : "status-available"
                      }`}
                    >
                      {session.is_full ? "FULL" : "AVAILABLE"}
                    </span>
                    <button
                      className="btn btn-primary"
                      disabled={session.is_full}
                      onClick={() => handleBookSession(session)}
                    >
                      📝 Book
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="sidebar">
          {/* Quick Actions */}
          <div className="quick-actions-card">
            <div className="quick-actions-header">
              <h3>⚡ Quick Actions</h3>
            </div>
            <div className="quick-actions-body">
              <div className="action-buttons">
                <button
                  className="btn btn-primary"
                  onClick={() => setShowProfileModal(true)}
                >
                  👤 Profile Settings
                </button>
                <button
                  className="btn btn-success"
                  onClick={() => setShowFeedbackModal(true)}
                >
                  💬 Give Feedback
                </button>
                <button
                  className="btn btn-outline"
                  onClick={() => setShowCheckinModal(true)}
                >
                  ✅ Check In
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowBookingHistoryModal(true)}
                >
                  📋 Booking History
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* My Bookings */}
      <div className="content-card">
        <div className="content-card-header">
          <h2>📝 My Bookings</h2>
        </div>

        <div className="content-card-body">
          {bookings.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <h3>No Bookings Yet</h3>
              <p>
                You haven't booked any sessions yet. Book a session from the
                available sessions above!
              </p>
            </div>
          ) : (
            bookings.map((booking) => (
              <div key={booking.id} className="booking-item">
                <div className="booking-info">
                  <h4>
                    {booking.session?.name || `Session ${booking.session_id}`}
                  </h4>
                  <div className="booking-meta">
                    Status:{" "}
                    <span className={`status-badge status-${booking.status}`}>
                      {booking.status?.toUpperCase()}
                    </span>
                  </div>
                  <div className="booking-meta">
                    Booked: {new Date(booking.booked_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="booking-actions">
                  {booking.status === "confirmed" && (
                    <button
                      className="btn btn-danger"
                      onClick={() => handleCancelBooking(booking.id)}
                    >
                      ❌ Cancel
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Modals */}
      {selectedSession && (
        <BookingModal
          session={selectedSession}
          onClose={() => setSelectedSession(null)}
          onBook={handleBookSession}
        />
      )}

      {showProfileModal && (
        <ProfileModal user={user} onClose={() => setShowProfileModal(false)} />
      )}

      {showFeedbackModal && (
        <FeedbackModal onClose={() => setShowFeedbackModal(false)} />
      )}

      {showCheckinModal && (
        <CheckinModal
          bookings={bookings}
          onClose={() => setShowCheckinModal(false)}
        />
      )}
    </div>
  );
};

export default StudentDashboard;
