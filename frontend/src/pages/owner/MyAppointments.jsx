import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, message, Space } from 'antd';
import request from '../../utils/request';

const statusMap = {
  booked: { text: '已预约', color: 'blue' },
  checking: { text: '检测中', color: 'orange' },
  completed: { text: '已完成', color: 'green' },
  cancelled: { text: '已取消', color: 'default' },
};

export default function MyAppointments() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);

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

  const cancel = async (id) => {
    setBusyId(id);
    try {
      await request.post(`/appointments/${id}/cancel`);
      message.success('取消成功');
      fetch();
    } catch (err) {
      message.error(err.response?.data?.detail || '取消失败');
    } finally {
      setBusyId(null);
    }
  };

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
            <Button danger loading={busyId === record.id} disabled={busyId !== null} onClick={() => cancel(record.id)}>取消</Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card title="我的预约">
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} />
    </Card>
  );
}
