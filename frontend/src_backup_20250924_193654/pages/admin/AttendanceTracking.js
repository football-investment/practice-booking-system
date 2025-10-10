import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const AttendanceTracking = () => {
  const { logout } = useAuth();
  const [attendance, setAttendance] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [sessionFilter, setSessionFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');
  const [attendanceFilter, setAttendanceFilter] = useState('all');

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      console.log('Loading attendance tracking data...');
      
      const [attendanceResponse, sessionsResponse, usersResponse] = await Promise.all([
        apiService.getAttendance().catch(() => ({})),
        apiService.getSessions().catch(() => ({})),
        apiService.getUsers().catch(() => ({}))
      ]);
      
      console.log('Attendance API response:', attendanceResponse);
      console.log('Sessions API response:', sessionsResponse);
      console.log('Users API response:', usersResponse);
      
      // Extract data arrays from API response objects
      const attendanceData = attendanceResponse?.attendance || attendanceResponse?.data || attendanceResponse || [];
      const sessionsData = sessionsResponse?.sessions || sessionsResponse?.data || sessionsResponse || [];
      const usersData = usersResponse?.users || usersResponse?.data || usersResponse || [];
      
      setAttendance(attendanceData);
      setSessions(sessionsData);
      setUsers(usersData);
      
      console.log('Attendance tracking data loaded:', {
        attendance: attendanceData.length,
        sessions: sessionsData.length,
        users: usersData.length
      });
      
    } catch (err) {
      console.error('Failed to load attendance data:', err);
      setError('Failed to load attendance data');
    } finally {
      setLoading(false);
    }
  };

  const getUserName = (userId) => {
    const user = users.find(u => u.id === userId);
    return user?.full_name || user?.email || `User ${userId}`;
  };

  const getSessionName = (sessionId) => {
    const session = sessions.find(s => s.id === sessionId);
    return session?.title || `Session ${sessionId}`;
  };

  const filteredAttendance = attendance.filter(record => {
    const session = sessions.find(s => s.id === record.session_id);
    
    let matchesSession = sessionFilter === 'all' || record.session_id === parseInt(sessionFilter);
    
    let matchesDate = true;
    if (dateFilter !== 'all') {
      const recordDate = new Date(session?.date_start);
      const now = new Date();
      const daysDiff = (now - recordDate) / (1000 * 60 * 60 * 24);
      
      switch (dateFilter) {
        case 'today':
          matchesDate = Math.abs(daysDiff) < 1;
          break;
        case 'week':
          matchesDate = daysDiff <= 7 && daysDiff >= 0;
          break;
        case 'month':
          matchesDate = daysDiff <= 30 && daysDiff >= 0;
          break;
      }
    }
    
    let matchesAttendance = true;
    if (attendanceFilter !== 'all') {
      matchesAttendance = attendanceFilter === 'present' ? record.attended : !record.attended;
    }
    
    return matchesSession && matchesDate && matchesAttendance;
  });

  const attendanceStats = {
    total: attendance.length,
    present: attendance.filter(a => a.attended).length,
    absent: attendance.filter(a => !a.attended).length,
    rate: attendance.length > 0 ? 
      Math.round((attendance.filter(a => a.attended).length / attendance.length) * 100) : 0
  };

  const exportAttendanceCSV = () => {
    const csvData = filteredAttendance.map(record => {
      const session = sessions.find(s => s.id === record.session_id);
      const user = users.find(u => u.id === record.user_id);
      
      return {
        'User Name': user?.full_name || user?.email,
        'User Email': user?.email,
        'Session Title': session?.title,
        'Session Date': session?.date_start ? new Date(session.date_start).toLocaleDateString() : '',
        'Attended': record.attended ? 'Yes' : 'No',
        'Check-in Time': record.check_in_time || '',
        'Notes': record.notes || ''
      };
    });

    const csvContent = [
      Object.keys(csvData[0] || {}).join(','),
      ...csvData.map(row => Object.values(row).map(val => `"${val}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance_report_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    
    setSuccess('Attendance report exported successfully!');
  };

  return (
    <div className="attendance-tracking">
      {/* Navigation */}
      <div className="admin-page-header">
        <div>
          <Link to="/admin/dashboard" className="back-link">← Admin Dashboard</Link>
          <h1>Attendance Tracking</h1>
        </div>
        <div className="header-actions">
          <button 
            onClick={exportAttendanceCSV}
            className="export-btn primary"
            disabled={filteredAttendance.length === 0}
          >
            📊 Export CSV
          </button>
          <button onClick={() => logout()} className="logout-btn">Logout</button>
        </div>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      {/* Attendance Stats */}
      <div className="attendance-stats">
        <div className="stat-card">
          <h3>Total Records</h3>
          <div className="stat-number">{attendanceStats.total}</div>
        </div>
        <div className="stat-card present">
          <h3>Present</h3>
          <div className="stat-number">{attendanceStats.present}</div>
        </div>
        <div className="stat-card absent">
          <h3>Absent</h3>
          <div className="stat-number">{attendanceStats.absent}</div>
        </div>
        <div className="stat-card rate">
          <h3>Attendance Rate</h3>
          <div className="stat-number">{attendanceStats.rate}%</div>
        </div>
      </div>

      {/* Filters */}
      <div className="attendance-filters">
        <div className="filter-section">
          <select
            value={sessionFilter}
            onChange={(e) => setSessionFilter(e.target.value)}
            className="session-filter"
          >
            <option value="all">All Sessions</option>
            {sessions.map(session => (
              <option key={session.id} value={session.id}>
                {session.title || `Session ${session.id}`}
              </option>
            ))}
          </select>
          
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="date-filter"
          >
            <option value="all">All Dates</option>
            <option value="today">Today</option>
            <option value="week">Past Week</option>
            <option value="month">Past Month</option>
          </select>
          
          <select
            value={attendanceFilter}
            onChange={(e) => setAttendanceFilter(e.target.value)}
            className="attendance-filter"
          >
            <option value="all">All Attendance</option>
            <option value="present">Present Only</option>
            <option value="absent">Absent Only</option>
          </select>
        </div>
      </div>

      {/* Attendance Table */}
      <div className="attendance-table-container">
        {loading ? (
          <div className="table-loading">Loading attendance records...</div>
        ) : filteredAttendance.length === 0 ? (
          <div className="table-empty">
            <h3>No attendance records found</h3>
            <p>Try adjusting your filters</p>
          </div>
        ) : (
          <table className="attendance-table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Session</th>
                <th>Date</th>
                <th>Attendance</th>
                <th>Check-in Time</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {filteredAttendance.map(record => {
                const user = users.find(u => u.id === record.user_id);
                const session = sessions.find(s => s.id === record.session_id);
                
                return (
                  <tr key={`${record.user_id}-${record.session_id}`}>
                    <td className="user-info">
                      <div className="user-avatar">🎓</div>
                      <div>
                        <div className="user-name">{user?.full_name || user?.email}</div>
                        <div className="user-id">{user?.student_id}</div>
                      </div>
                    </td>
                    <td className="session-info">
                      <div className="session-title">{session?.title || `Session ${record.session_id}`}</div>
                      <div className="session-location">{session?.location}</div>
                    </td>
                    <td>
                      <div>{new Date(session?.date_start).toLocaleDateString()}</div>
                      <div className="session-time">
                        {new Date(session?.date_start).toLocaleTimeString()}
                      </div>
                    </td>
                    <td>
                      <span className={`attendance-badge ${record.attended ? 'present' : 'absent'}`}>
                        {record.attended ? '✅ Present' : '❌ Absent'}
                      </span>
                    </td>
                    <td>
                      {record.check_in_time ? 
                        new Date(record.check_in_time).toLocaleTimeString() : 
                        '-'
                      }
                    </td>
                    <td>{record.notes || '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AttendanceTracking;