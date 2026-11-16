import { useEffect, useState } from 'react';
import { Card, Table, Tag, Statistic, Row, Col, Button, message } from 'antd';
import request from '../../utils/request';
import { WarningOutlined, ClockCircleOutlined } from '@ant-design/icons';

export default function Reminders() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await request.get('/vehicles');
      const upcoming = (res.data || []).filter(
        (v) => v.days_until_inspection !== null && v.days_until_inspection <= 60
      );
      setData(upcoming);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const expiredCount = data.filter((v) => v.days_until_inspection < 0).length;
  const soonCount = data.filter((v) => v.days_until_inspection >= 0 && v.days_until_inspection <= 30).length;
  // “60 天内到期”仅统计 31~60 天这一档，与“30 天内”“已逾期”互不重叠
  const count60 = data.filter((v) => v.days_until_inspection > 30 && v.days_until_inspection <= 60).length;

  const columns = [
    { title: '车牌号', dataIndex: 'plate_number', key: 'plate_number' },
    { title: '车辆类型', dataIndex: 'vehicle_type', key: 'vehicle_type' },
    { title: '下次年检日期', dataIndex: 'next_inspection_date', key: 'next_inspection_date' },
    {
      title: '剩余天数',
      dataIndex: 'days_until_inspection',
      key: 'days_until_inspection',
      render: (v) => {
        if (v < 0) return <Tag color="red">已逾期</Tag>;
        if (v === 0) return <Tag color="orange">今日到期</Tag>;
        const color = v <= 30 ? 'orange' : 'green';
        return <Tag color={color}>{`${v} 天`}</Tag>;
      },
    },
  ];

  return (
    <>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="60 天内到期"
              value={count60}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="30 天内到期"
              value={soonCount}
              styles={{ content: { color: '#fa8c16' } }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="已逾期"
              value={expiredCount}
              styles={{ content: { color: '#cf1322' } }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
      </Row>
      <Card title="年检提醒（60 天内到期）" extra={<Button onClick={fetch}>刷新</Button>}>
        <Table rowKey="id" columns={columns} dataSource={data} loading={loading} />
      </Card>
    </>
  );
}
