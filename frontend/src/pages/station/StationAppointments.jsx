import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Radio, Space, message } from 'antd';
import dayjs from 'dayjs';
import request from '../../utils/request';

const statusMap = {
  booked: { text: '已预约', color: 'blue' },
  checking: { text: '检测中', color: 'orange' },
  completed: { text: '已完成', color: 'green' },
  cancelled: { text: '已取消', color: 'default' },
};

export default function StationAppointments() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await request.get('/appointments');
      setData(res.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const filtered = data.filter((item) => {
    if (filter === 'today') return item.appointment_date === dayjs().format('YYYY-MM-DD');
    if (filter === 'booked') return item.status === 'booked';
    return true;
  });

  const columns = [
    { title: '车牌', dataIndex: ['vehicle', 'plate_number'], key: 'plate' },
    { title: '检测站', dataIndex: ['station', 'name'], key: 'station' },
    { title: '预约日期', dataIndex: 'appointment_date', key: 'appointment_date' },
    { title: '时段', dataIndex: 'time_slot', key: 'time_slot' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v) => <Tag color={statusMap[v]?.color}>{statusMap[v]?.text || v}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          {record.status === 'booked' && (
            <Button onClick={() => checkin(record.id)}>登记到站</Button>
          )}
        </Space>
      ),
    },
  ];

  const checkin = async (id) => {
    try {
      await request.post(`/appointments/${id}/checkin`);
      message.success('登记成功');
      fetch();
    } catch (err) {
      message.error(err.response?.data?.detail || '登记失败');
    }
  };

  return (
    <Card title="今日预约" extra={
      <Space>
        <Radio.Group value={filter} onChange={(e) => setFilter(e.target.value)}>
          <Radio.Button value="all">全部</Radio.Button>
          <Radio.Button value="today">今日</Radio.Button>
          <Radio.Button value="booked">待签到</Radio.Button>
        </Radio.Group>
        <Button onClick={fetch}>刷新</Button>
      </Space>
    }>
      <Table rowKey="id" columns={columns} dataSource={filtered} loading={loading} />
    </Card>
  );
}
