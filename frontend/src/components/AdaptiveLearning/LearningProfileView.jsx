import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, Button, Space, Spin, Alert, Tag, Divider } from 'antd';
import {
  TrophyOutlined,
  FireOutlined,
  BookOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  ExperimentOutlined
} from '@ant-design/icons';
import axios from 'axios';
import RecommendationCard from './RecommendationCard';
import './LearningProfileView.css';

const LearningProfileView = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [profile, setProfile] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [error, setError] = useState(null);

  // Fetch profile and recommendations
  const fetchData = async (forceRefresh = false) => {
    try {
      if (forceRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const token = localStorage.getItem('access_token');
      const headers = { Authorization: `Bearer ${token}` };

      // Fetch profile
      const profileRes = await axios.get(
        '/api/v1/curriculum-adaptive/profile',
        { headers }
      );
      setProfile(profileRes.data);

      // Fetch recommendations
      const recsRes = await axios.get(
        `/api/v1/curriculum-adaptive/recommendations?refresh=${forceRefresh}`,
        { headers }
      );
      setRecommendations(recsRes.data);

      setError(null);
    } catch (err) {
      console.error('Error fetching adaptive learning data:', err);
      setError(err.response?.data?.detail || 'Failed to load learning profile');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Refresh profile metrics
  const handleUpdateProfile = async () => {
    try {
      setRefreshing(true);
      const token = localStorage.getItem('access_token');
      const headers = { Authorization: `Bearer ${token}` };

      await axios.post('/api/v1/curriculum-adaptive/profile/update', {}, { headers });
      await fetchData(true); // Refresh all data
    } catch (err) {
      console.error('Error updating profile:', err);
      setError('Failed to update profile');
      setRefreshing(false);
    }
  };

  // Dismiss recommendation
  const handleDismissRecommendation = async (recId) => {
    try {
      const token = localStorage.getItem('access_token');
      const headers = { Authorization: `Bearer ${token}` };

      await axios.post(
        `/api/v1/curriculum-adaptive/recommendations/${recId}/dismiss`,
        {},
        { headers }
      );

      // Remove from local state
      setRecommendations(recommendations.filter(r => r.id !== recId));
    } catch (err) {
      console.error('Error dismissing recommendation:', err);
    }
  };

  // Get pace color
  const getPaceColor = (pace) => {
    switch (pace) {
      case 'ACCELERATED': return '#52c41a';
      case 'FAST': return '#1890ff';
      case 'MEDIUM': return '#faad14';
      case 'SLOW': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  // Get pace icon
  const getPaceIcon = (pace) => {
    switch (pace) {
      case 'ACCELERATED': return '🚀';
      case 'FAST': return '⚡';
      case 'MEDIUM': return '🚶';
      case 'SLOW': return '🐢';
      default: return '📊';
    }
  };

  // Get content type icon
  const getContentIcon = (type) => {
    switch (type) {
      case 'VIDEO': return <VideoCameraOutlined />;
      case 'TEXT': return <FileTextOutlined />;
      case 'PRACTICE': return <ExperimentOutlined />;
      default: return <BookOutlined />;
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="Loading your learning profile..." />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Error"
        description={error}
        type="error"
        showIcon
        style={{ margin: '20px' }}
      />
    );
  }

  return (
    <div className="learning-profile-view" style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '28px', fontWeight: 700 }}>
            🧠 Your Learning Profile
          </h2>
          <p style={{ margin: '8px 0 0 0', color: '#8c8c8c' }}>
            AI-powered personalized learning insights
          </p>
        </div>
        <Button
          icon={<ReloadOutlined spin={refreshing} />}
          onClick={handleUpdateProfile}
          loading={refreshing}
          size="large"
        >
          Update Metrics
        </Button>
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        {/* Learning Pace */}
        <Col xs={24} sm={12} md={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Learning Pace</span>}
              value={profile.learning_pace}
              prefix={getPaceIcon(profile.learning_pace)}
              valueStyle={{ color: 'white', fontSize: '24px', fontWeight: 700 }}
            />
            <Progress
              percent={profile.pace_score}
              strokeColor="#ffffff"
              trailColor="rgba(255,255,255,0.3)"
              showInfo={false}
              style={{ marginTop: '12px' }}
            />
          </Card>
        </Col>

        {/* Quiz Average */}
        <Col xs={24} sm={12} md={6}>
          <Card bordered={false}>
            <Statistic
              title="Quiz Average"
              value={profile.quiz_average_score.toFixed(1)}
              suffix="%"
              prefix={<TrophyOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: profile.quiz_average_score >= 70 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>

        {/* Lessons Completed */}
        <Col xs={24} sm={12} md={6}>
          <Card bordered={false}>
            <Statistic
              title="Lessons Completed"
              value={profile.lessons_completed_count}
              prefix={<BookOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        {/* Avg Time per Lesson */}
        <Col xs={24} sm={12} md={6}>
          <Card bordered={false}>
            <Statistic
              title="Avg Time per Lesson"
              value={profile.avg_time_per_lesson_minutes.toFixed(0)}
              suffix="min"
              prefix={<ClockCircleOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Preferred Content Type */}
      <Card
        bordered={false}
        style={{ marginBottom: '24px', background: '#fafafa' }}
        bodyStyle={{ padding: '16px 24px' }}
      >
        <Space size="large">
          <span style={{ fontSize: '16px', fontWeight: 600 }}>
            {getContentIcon(profile.preferred_content_type)}
            Preferred Content Type:
          </span>
          <Tag color={profile.preferred_content_type === 'VIDEO' ? 'red' : profile.preferred_content_type === 'TEXT' ? 'blue' : 'green'} style={{ fontSize: '14px', padding: '4px 12px' }}>
            {profile.preferred_content_type}
          </Tag>
        </Space>
      </Card>

      <Divider orientation="left" style={{ fontSize: '20px', fontWeight: 600 }}>
        <ThunderboltOutlined /> AI Recommendations
      </Divider>

      {/* Recommendations */}
      {recommendations.length > 0 ? (
        <div>
          {recommendations.map(rec => (
            <RecommendationCard
              key={rec.id}
              recommendation={rec}
              onDismiss={handleDismissRecommendation}
            />
          ))}
        </div>
      ) : (
        <Card bordered={false} style={{ textAlign: 'center', padding: '40px' }}>
          <FireOutlined style={{ fontSize: '48px', color: '#52c41a', marginBottom: '16px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#262626' }}>
            You're doing great!
          </h3>
          <p style={{ color: '#8c8c8c', marginTop: '8px' }}>
            No urgent recommendations at the moment. Keep up the excellent work!
          </p>
          <Button type="primary" onClick={() => fetchData(true)} style={{ marginTop: '16px' }}>
            Check for New Recommendations
          </Button>
        </Card>
      )}
    </div>
  );
};

export default LearningProfileView;
