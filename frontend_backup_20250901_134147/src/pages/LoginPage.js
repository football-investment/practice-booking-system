import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { login, isAuthenticated } = useAuth();

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/dashboard" />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(email, password);
    
    if (result.success) {
      // AuthContext handles redirect
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2>🔐 Login to Practice Booking System</h2>
      <p style={{textAlign: 'center', color: '#666', marginBottom: '1.5rem'}}>
        Enter your credentials to access the system
      </p>

      {error && <div className="error">❌ {error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>📧 Email:</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
            placeholder="Enter your email"
          />
        </div>

        <div className="form-group">
          <label>🔑 Password:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
            placeholder="Enter your password"
          />
        </div>

        <button 
          type="submit" 
          className="btn" 
          disabled={loading}
          style={{width: '100%'}}
        >
          {loading ? '🔄 Logging in...' : '🚀 Login'}
        </button>
      </form>

    </div>
  );
}

export default LoginPage;