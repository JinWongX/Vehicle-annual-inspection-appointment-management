import { useEffect, useState } from 'react';
import { Card, DatePicker, Button, Space, Statistic, Row, Col, Empty, message } from 'antd';
import { PieChart, Pie, Cell, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import dayjs from 'dayjs';
import request from '../../utils/request';

const COLORS = ['#52c41a', '#f5222d', '#fa8c16'];

export default function StatisticsDashboard() {
  const [startDate, setStartDate] = useState(dayjs().subtract(30, 'day'));
  const [endDate, setEndDate] = useState(dayjs());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    if (startDate && endDate && startDate.isAfter(endDate)) {
      message.error('开始日期不能晚于结束日期');
      return;
    }
    setLoading(true);
    try {
      const res = await request.get('/reports/statistics', {
        params: {
          start_date: startDate.format('YYYY-MM-DD'),
          end_date: endDate.format('YYYY-MM-DD'),
        },
      });
      setData(res.data);
    } catch (err) {
      message.error(err.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const pieData = data ? [
    { name: '合格', value: data.pass_count },
    { name: '不合格', value: data.fail_count },
    { name: '需复检', value: data.retest_count },
  ].filter((item) => item.value > 0) : [];

  const failReasonsData = data
    ? Object.entries(data.fail_reasons || {}).map(([name, count]) => ({ name, count }))
    : [];

  return (
    <>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <DatePicker
            value={startDate}
            onChange={setStartDate}
            format="YYYY-MM-DD"
            placeholder="开始日期"
          />
          <DatePicker
            value={endDate}
            onChange={setEndDate}
            format="YYYY-MM-DD"
            placeholder="结束日期"
          />
          <Button type="primary" onClick={fetch} loading={loading}>查询</Button>
        </Space>
      </Card>
      {data && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card><Statistic title="检测总数" value={data.total_count} /></Card>
            </Col>
            <Col span={6}>
              <Card><Statistic title="合格率" value={data.pass_rate} suffix="%" precision={2} /></Card>
            </Col>
            <Col span={6}>
              <Card><Statistic title="合格数" value={data.pass_count} styles={{ content: { color: '#52c41a' } }} /></Card>
            </Col>
            <Col span={6}>
              <Card><Statistic title="不合格数" value={data.fail_count} styles={{ content: { color: '#f5222d' } }} /></Card>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Card title="检测结果分布">
                {pieData.length === 0 && <Empty />}
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="不合格原因统计">
                {failReasonsData.length === 0 && <Empty />}
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={failReasonsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#f5222d" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </>
  );
}
