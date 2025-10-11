import React, { useState, useEffect } from 'react';
import {
  Card, Row, Col, Statistic, Progress, Tag, Space,
  Button, Spin, message, Typography, Alert
} from 'antd';
import {
  TrophyOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  FireOutlined,
  ThunderboltOutlined,
  BookOutlined
} from '@ant-design/icons';
import axiosInstance from '../../utils/axiosInstance';
import { API_ENDPOINTS } from '../../config/api';
import RecommendationCard from './RecommendationCard';
import './LearningProfileView.css';

const { Title, Text } = Typography;

const LearningProfileView = () => {
  const [profile, setProfile] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadProfile();
    loadRecommendations();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axiosInstance.get(API_ENDPOINTS.ADAPTIVE.PROFILE);
      setProfile(response.data);
    } catch (error) {
      console.error('Failed to load learning profile:', error);
      setError('Failed to load learning profile. Please try again.');
      message.error('Failed to load learning profile');
    } finally {
      setLoading(false);
    }
  };

  const loadRecommendations = async (refresh = false) => {
    try {
      if (refresh) setRefreshing(true);
      const response = await axiosInstance.get(API_ENDPOINTS.ADAPTIVE.RECOMMENDATIONS, {
        params: { refresh }
      });
      setRecommendations(response.data);
      if (refresh) {
        message.success('Recommendations refreshed!');
      }
    } catch (error) {
      console.error('Failed to load recommendations:', error);
      if (refresh) {
        message.error('Failed to refresh recommendations');
      }
    } finally {
      if (refresh) setRefreshing(false);
    }
  };

  const handleDismiss = async (recommendationId) => {
    try {
      await axiosInstance.post(API_ENDPOINTS.ADAPTIVE.DISMISS_RECOMMENDATION(recommendationId));
      message.success('Recommendation dismissed');
      loadRecommendations();
    } catch (error) {
      console.error('Failed to dismiss recommendation:', error);
      message.error('Failed to dismiss recommendation');
    }
  };

  const getPaceColor = (pace) => {
    const colors = {
      'ACCELERATED': 'purple',
      'FAST': 'green',
      'MEDIUM': 'blue',
      'SLOW': 'orange'
    };
    return colors[pace] || 'default';
  };

  const getPaceIcon = (pace) => {
    if (pace === 'ACCELERATED' || pace === 'FAST') return <ThunderboltOutlined />;
    if (pace === 'SLOW') return <ClockCircleOutlined />;
    return <RiseOutlined />;
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" tip="Loading your learning profile..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        <Alert
          message="Error Loading Profile"
          description={error}
          type="error"
          showIcon
          action={
            <Button onClick={loadProfile} type="primary">
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  if (!profile) {
    return (
      <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        <Alert
          message="No Profile Data"
          description="Complete some lessons and quizzes to build your learning profile!"
          type="info"
          showIcon
          icon={<BookOutlined />}
        />
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Title level={2}>
        <FireOutlined style={{ color: '#ff4d4f' }} /> Your Learning Profile
      </Title>

      {/* Statistics Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Quiz Average"
              value={profile.quiz_average_score || 0}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{
                color: profile.quiz_average_score >= 70 ? '#3f8600' : '#cf1322'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Lessons Progress"
              value={profile.lesson_completion_rate || 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Study Time"
              value={Math.floor((profile.total_study_time_minutes || 0) / 60)}
              suffix="hours"
              prefix={<ClockCircleOutlined />}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {(profile.total_study_time_minutes || 0) % 60} minutes
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Days Active"
              value={profile.days_active || 0}
              prefix={<RiseOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Learning Pace Card */}
      <Card
        title={
          <Space>
            {getPaceIcon(profile.learning_pace)}
            <span>Learning Pace</span>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Space>
            <Text strong>Current Pace:</Text>
            <Tag
              color={getPaceColor(profile.learning_pace)}
              style={{ fontSize: 16, padding: '4px 12px' }}
            >
              {profile.learning_pace || 'MEDIUM'}
            </Tag>
          </Space>
          <div>
            <Text type="secondary">Pace Score</Text>
            <Progress
              percent={Math.round(profile.pace_score || 50)}
              strokeColor={{
                '0%': '#108ee9',
                '50%': '#87d068',
                '100%': '#52c41a',
              }}
              status="active"
            />
          </div>
          {profile.pace_score >= 80 && (
            <Text type="success">
              <ThunderboltOutlined /> You're learning faster than average! Keep it up!
            </Text>
          )}
          {profile.pace_score < 40 && (
            <Text type="warning">
              Take your time to fully understand each concept. Quality over speed!
            </Text>
          )}
        </Space>
      </Card>

      {/* Recommendations Card */}
      <Card
        title={
          <Space>
            <FireOutlined style={{ color: '#ff4d4f' }} />
            <span>Personalized Recommendations</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => loadRecommendations(true)}
            loading={refreshing}
            type="primary"
          >
            Refresh
          </Button>
        }
      >
        {recommendations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Text type="secondary">
              No recommendations at this time. Keep up the good work! 🎉
            </Text>
          </div>
        ) : (
          <div>
            {recommendations.map(rec => (
              <RecommendationCard
                key={rec.id}
                recommendation={rec}
                onDismiss={handleDismiss}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default LearningProfileView;
