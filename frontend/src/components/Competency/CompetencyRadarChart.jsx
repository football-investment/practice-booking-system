import React, { useEffect, useState } from 'react';
import { Card, Spin, Alert, Empty } from 'antd';
import { Radar } from '@ant-design/plots';
import axiosInstance from '../../utils/axiosInstance';

const CompetencyRadarChart = ({ specializationId, height = 400 }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchRadarData();
  }, [specializationId]);

  const fetchRadarData = async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get('/competency/radar-chart-data', {
        params: { specialization_id: specializationId }
      });

      const radarData = response.data;

      // Format data for @ant-design/plots Radar
      const formattedData = radarData.categories.map((category, index) => ({
        name: category,
        score: radarData.scores[index],
        level: radarData.levels[index],
        color: radarData.colors[index]
      }));

      setData(formattedData);
      setError(null);
    } catch (err) {
      console.error('Error fetching radar chart data:', err);
      setError(err.response?.data?.detail || 'Failed to load competency data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card style={{ textAlign: 'center', padding: '40px' }}>
        <Spin size="large" tip="Loading competency radar..." />
      </Card>
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

  if (!data || data.length === 0) {
    return (
      <Card>
        <Empty
          description="No competency data yet. Complete quizzes and exercises to see your skills!"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  // Radar chart configuration
  const config = {
    data: data,
    xField: 'name',
    yField: 'score',
    meta: {
      score: {
        alias: 'Competency Score',
        min: 0,
        max: 100
      }
    },
    xAxis: {
      line: null,
      tickLine: null,
      grid: {
        line: {
          style: {
            lineDash: null
          }
        }
      }
    },
    yAxis: {
      line: null,
      tickLine: null,
      grid: {
        line: {
          type: 'line',
          style: {
            lineDash: null
          }
        }
      },
      label: {
        formatter: (v) => `${v}%`
      }
    },
    point: {
      size: 4,
      shape: 'circle',
      style: {
        fill: '#1890ff',
        fillOpacity: 1
      }
    },
    area: {
      style: {
        fill: '#1890ff',
        fillOpacity: 0.25
      }
    },
    line: {
      style: {
        stroke: '#1890ff',
        lineWidth: 2
      }
    },
    // Tooltip
    tooltip: {
      customContent: (title, items) => {
        if (!items || items.length === 0) return null;
        const item = items[0];
        const dataPoint = data.find(d => d.name === item.data.name);
        return (
          <div style={{ padding: '12px', background: 'white', borderRadius: '4px', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
            <div style={{ fontWeight: 600, marginBottom: '8px', fontSize: '14px' }}>
              {item.data.name}
            </div>
            <div style={{ color: '#8c8c8c', fontSize: '12px' }}>
              Score: <span style={{ fontWeight: 600, color: '#262626' }}>{item.data.score.toFixed(1)}%</span>
            </div>
            {dataPoint && (
              <div style={{ color: '#8c8c8c', fontSize: '12px', marginTop: '4px' }}>
                Level: <span style={{ fontWeight: 600, color: dataPoint.color }}>{dataPoint.level}</span>
              </div>
            )}
          </div>
        );
      }
    },
    height: height
  };

  return (
    <Card
      title="Competency Radar"
      bordered={false}
      style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
    >
      <Radar {...config} />

      {/* Legend */}
      <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: '16px' }}>
        {data.map((item, index) => (
          <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: item.color }} />
            <span style={{ fontSize: '12px', color: '#595959' }}>
              {item.name}: <strong>{item.level}</strong> ({item.score.toFixed(0)}%)
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default CompetencyRadarChart;
