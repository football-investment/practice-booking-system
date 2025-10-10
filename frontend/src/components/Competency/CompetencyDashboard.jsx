import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Progress, Tag, Divider, Spin, Alert, Button, Modal, List, Collapse, Empty, Timeline } from 'antd';
import {
  TrophyOutlined,
  FireOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  StarOutlined,
  RiseOutlined
} from '@ant-design/icons';
import axios from 'axios';
import CompetencyRadarChart from './CompetencyRadarChart';
import './CompetencyDashboard.css';

const { Panel } = Collapse;

const CompetencyDashboard = ({ specializationId }) => {
  const [loading, setLoading] = useState(true);
  const [competencies, setCompetencies] = useState([]);
  const [milestones, setMilestones] = useState([]);
  const [assessmentHistory, setAssessmentHistory] = useState([]);
  const [error, setError] = useState(null);
  const [breakdownModal, setBreakdownModal] = useState({ visible: false, categoryId: null, data: null });

  useEffect(() => {
    fetchData();
  }, [specializationId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const headers = { Authorization: `Bearer ${token}` };

      // Fetch competencies
      const compRes = await axios.get(
        `/api/v1/competency/my-competencies?specialization_id=${specializationId}`,
        { headers }
      );
      setCompetencies(compRes.data);

      // Fetch milestones
      const milestonesRes = await axios.get(
        `/api/v1/competency/milestones?specialization_id=${specializationId}`,
        { headers }
      );
      setMilestones(milestonesRes.data);

      // Fetch recent assessment history
      const historyRes = await axios.get(
        '/api/v1/competency/assessment-history?limit=10',
        { headers }
      );
      setAssessmentHistory(historyRes.data);

      setError(null);
    } catch (err) {
      console.error('Error fetching competency data:', err);
      setError(err.response?.data?.detail || 'Failed to load competency dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchBreakdown = async (categoryId) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `/api/v1/competency/breakdown/${categoryId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setBreakdownModal({ visible: true, categoryId, data: response.data });
    } catch (err) {
      console.error('Error fetching breakdown:', err);
    }
  };

  const getLevelColor = (level) => {
    switch (level) {
      case 'Expert': return '#722ed1';
      case 'Proficient': return '#52c41a';
      case 'Competent': return '#1890ff';
      case 'Developing': return '#faad14';
      case 'Beginner': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  const getLevelIcon = (level) => {
    switch (level) {
      case 'Expert': return '🏆';
      case 'Proficient': return '⭐';
      case 'Competent': return '✅';
      case 'Developing': return '📈';
      case 'Beginner': return '🌱';
      default: return '📊';
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="Loading competency dashboard..." />
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
    <div className="competency-dashboard" style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ margin: 0, fontSize: '28px', fontWeight: 700 }}>
          🎯 Competency Dashboard
        </h2>
        <p style={{ margin: '8px 0 0 0', color: '#8c8c8c' }}>
          Track your skills automatically assessed from quizzes and exercises
        </p>
      </div>

      {/* Radar Chart */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} lg={14}>
          <CompetencyRadarChart specializationId={specializationId} height={450} />
        </Col>

        {/* Milestones */}
        <Col xs={24} lg={10}>
          <Card
            title={<span><TrophyOutlined /> Achievements</span>}
            bordered={false}
            style={{ height: '100%', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
          >
            {milestones.length > 0 ? (
              <List
                dataSource={milestones.slice(0, 5)}
                renderItem={(milestone) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<span style={{ fontSize: '24px' }}>{milestone.icon || '🏆'}</span>}
                      title={milestone.milestone_name}
                      description={
                        <div>
                          <div style={{ color: '#8c8c8c', fontSize: '12px' }}>
                            {milestone.description}
                          </div>
                          <div style={{ marginTop: '4px' }}>
                            <Tag color="gold" style={{ fontSize: '11px' }}>
                              +{milestone.xp_reward} XP
                            </Tag>
                            <Tag color="blue" style={{ fontSize: '11px' }}>
                              {new Date(milestone.achieved_at).toLocaleDateString()}
                            </Tag>
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty
                description="No achievements yet. Keep learning to unlock milestones!"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
      </Row>

      <Divider orientation="left" style={{ fontSize: '20px', fontWeight: 600 }}>
        <BarChartOutlined /> Competency Breakdown
      </Divider>

      {/* Competency Cards */}
      {competencies.length > 0 ? (
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          {competencies.map((comp) => (
            <Col xs={24} sm={12} md={8} lg={6} key={comp.id}>
              <Card
                hoverable
                bordered={false}
                style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
                onClick={() => fetchBreakdown(comp.category_id)}
              >
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '32px', marginBottom: '12px' }}>
                    {comp.category_icon || '📊'}
                  </div>
                  <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px' }}>
                    {comp.category_name}
                  </h3>
                  <Tag color={getLevelColor(comp.current_level)} style={{ marginBottom: '12px', fontSize: '12px' }}>
                    {getLevelIcon(comp.current_level)} {comp.current_level}
                  </Tag>
                  <Progress
                    type="circle"
                    percent={Math.round(comp.current_score)}
                    strokeColor={getLevelColor(comp.current_level)}
                    width={80}
                  />
                  <div style={{ marginTop: '12px', fontSize: '12px', color: '#8c8c8c' }}>
                    {comp.total_assessments} assessments
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      ) : (
        <Empty
          description="No competency data yet. Complete quizzes and exercises to build your profile!"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ margin: '40px 0' }}
        />
      )}

      {/* Recent Assessment History */}
      {assessmentHistory.length > 0 && (
        <>
          <Divider orientation="left" style={{ fontSize: '20px', fontWeight: 600 }}>
            <ClockCircleOutlined /> Recent Assessments
          </Divider>
          <Card bordered={false} style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
            <Timeline mode="left">
              {assessmentHistory.map((assessment, index) => (
                <Timeline.Item
                  key={assessment.id}
                  color={assessment.score >= 70 ? 'green' : 'red'}
                  dot={assessment.score >= 70 ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
                >
                  <div style={{ fontSize: '14px' }}>
                    <div style={{ fontWeight: 600, marginBottom: '4px' }}>
                      {assessment.category_name || assessment.skill_name}
                    </div>
                    <div style={{ color: '#8c8c8c', fontSize: '12px' }}>
                      Score: <span style={{ color: assessment.score >= 70 ? '#52c41a' : '#ff4d4f', fontWeight: 600 }}>
                        {assessment.score.toFixed(0)}%
                      </span>
                      {' • '}
                      From: <Tag color="blue" style={{ fontSize: '11px' }}>{assessment.source_type}</Tag>
                      {' • '}
                      {new Date(assessment.assessed_at).toLocaleString()}
                    </div>
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
          </Card>
        </>
      )}

      {/* Breakdown Modal */}
      <Modal
        title={breakdownModal.data?.category?.name || 'Competency Breakdown'}
        visible={breakdownModal.visible}
        onCancel={() => setBreakdownModal({ visible: false, categoryId: null, data: null })}
        footer={null}
        width={700}
      >
        {breakdownModal.data && (
          <div>
            {/* Category Summary */}
            <Card bordered={false} style={{ marginBottom: '16px', background: '#fafafa' }}>
              <Row gutter={16} align="middle">
                <Col flex="auto">
                  <div style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
                    {breakdownModal.data.category.icon} {breakdownModal.data.category.name}
                  </div>
                  <div style={{ color: '#8c8c8c', fontSize: '13px' }}>
                    {breakdownModal.data.category.description}
                  </div>
                </Col>
                <Col>
                  <Progress
                    type="circle"
                    percent={Math.round(breakdownModal.data.category.current_score)}
                    strokeColor={getLevelColor(breakdownModal.data.category.current_level)}
                    width={100}
                  />
                </Col>
              </Row>
            </Card>

            {/* Skills */}
            <h4 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>
              <StarOutlined /> Individual Skills
            </h4>
            <List
              dataSource={breakdownModal.data.skills}
              renderItem={(skill) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{skill.name}</span>
                        <Tag color={getLevelColor(skill.current_level)}>
                          {getLevelIcon(skill.current_level)} {skill.current_level}
                        </Tag>
                      </div>
                    }
                    description={
                      <div>
                        <div style={{ marginBottom: '8px', fontSize: '12px', color: '#8c8c8c' }}>
                          {skill.description}
                        </div>
                        <Progress
                          percent={Math.round(skill.current_score)}
                          strokeColor={getLevelColor(skill.current_level)}
                          size="small"
                        />
                        <div style={{ fontSize: '11px', color: '#8c8c8c', marginTop: '4px' }}>
                          {skill.total_assessments} assessments
                          {skill.last_assessed_at && (
                            <> • Last: {new Date(skill.last_assessed_at).toLocaleDateString()}</>
                          )}
                        </div>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CompetencyDashboard;
