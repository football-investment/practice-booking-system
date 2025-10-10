import React from 'react';
import { Card, Button, Tag, Space } from 'antd';
import {
  BookOutlined,
  ThunderboltOutlined,
  CoffeeOutlined,
  RocketOutlined,
  ExperimentOutlined,
  PlayCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import './RecommendationCard.css';

const RecommendationCard = ({ recommendation, onDismiss }) => {
  // Icon mapping for recommendation types
  const iconMap = {
    REVIEW_LESSON: <BookOutlined style={{ fontSize: '24px', color: '#ff4d4f' }} />,
    CONTINUE_LEARNING: <ThunderboltOutlined style={{ fontSize: '24px', color: '#52c41a' }} />,
    TAKE_BREAK: <CoffeeOutlined style={{ fontSize: '24px', color: '#fa8c16' }} />,
    RESUME_LEARNING: <RocketOutlined style={{ fontSize: '24px', color: '#1890ff' }} />,
    PRACTICE_MORE: <ExperimentOutlined style={{ fontSize: '24px', color: '#722ed1' }} />,
    START_LEARNING: <PlayCircleOutlined style={{ fontSize: '24px', color: '#13c2c2' }} />,
    ADVANCE_FASTER: <ThunderboltOutlined style={{ fontSize: '24px', color: '#faad14' }} />
  };

  // Color mapping for recommendation types
  const colorMap = {
    REVIEW_LESSON: 'red',
    CONTINUE_LEARNING: 'green',
    TAKE_BREAK: 'orange',
    RESUME_LEARNING: 'blue',
    PRACTICE_MORE: 'purple',
    START_LEARNING: 'cyan',
    ADVANCE_FASTER: 'gold'
  };

  // Priority badge
  const getPriorityTag = (priority) => {
    if (priority >= 90) return <Tag color="red">High Priority</Tag>;
    if (priority >= 70) return <Tag color="orange">Medium Priority</Tag>;
    return <Tag color="blue">Low Priority</Tag>;
  };

  return (
    <Card
      className="recommendation-card"
      hoverable
      bordered={false}
      style={{
        marginBottom: '16px',
        borderLeft: `4px solid ${colorMap[recommendation.type] || '#1890ff'}`,
        background: 'linear-gradient(135deg, #ffffff 0%, #f0f5ff 100%)'
      }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            {iconMap[recommendation.type] || iconMap.CONTINUE_LEARNING}
            <div>
              <div style={{ fontSize: '18px', fontWeight: 600, color: '#262626' }}>
                {recommendation.title}
              </div>
              {getPriorityTag(recommendation.priority)}
            </div>
          </Space>
          <Button
            type="text"
            icon={<CloseCircleOutlined />}
            onClick={() => onDismiss(recommendation.id)}
            style={{ color: '#8c8c8c' }}
          >
            Dismiss
          </Button>
        </div>

        {/* Message */}
        <div style={{ fontSize: '14px', color: '#595959', lineHeight: '1.6' }}>
          {recommendation.message}
        </div>

        {/* Metadata display */}
        {recommendation.metadata && Object.keys(recommendation.metadata).length > 0 && (
          <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
            {recommendation.metadata.lesson_ids && (
              <div>📚 {recommendation.metadata.lesson_ids.length} lessons to review</div>
            )}
            {recommendation.metadata.lesson_title && (
              <div>📖 Next: {recommendation.metadata.lesson_title}</div>
            )}
            {recommendation.metadata.days_inactive && (
              <div>⏰ Last activity: {recommendation.metadata.days_inactive} days ago</div>
            )}
            {recommendation.metadata.total_minutes && (
              <div>⏱️ Study time: {Math.round(recommendation.metadata.total_minutes)} minutes</div>
            )}
          </div>
        )}

        {/* Action button */}
        {recommendation.type === 'CONTINUE_LEARNING' && recommendation.metadata?.lesson_id && (
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            href={`/student/curriculum/lesson/${recommendation.metadata.lesson_id}`}
          >
            Start Lesson
          </Button>
        )}
        {recommendation.type === 'REVIEW_LESSON' && recommendation.metadata?.lesson_ids && (
          <Button
            type="primary"
            danger
            icon={<BookOutlined />}
            href={`/student/curriculum/lesson/${recommendation.metadata.lesson_ids[0]}`}
          >
            Review Now
          </Button>
        )}
      </Space>
    </Card>
  );
};

export default RecommendationCard;
