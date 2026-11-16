import { useEffect, useState } from 'react';
import { Card, Input, Button, List, Tag, Empty, message } from 'antd';
import request from '../../utils/request';

const statusMap = {
  booked: { text: '已预约', color: 'blue' },
  checking: { text: '检测中', color: 'orange' },
  completed: { text: '已完成', color: 'green' },
  cancelled: { text: '已取消', color: 'default' },
};

export default function StationCheckin() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [plate, setPlate] = useState('');
  const [busyId, setBusyId] = useState(null);

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await request.get('/appointments');
      setAppointments(res.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const candidates = appointments.filter(
    (a) => a.status === 'booked' && a.vehicle?.plate_number?.includes(plate.trim())
  );

  const checkin = async (id) => {
    setBusyId(id);
    try {
      await request.post(`/appointments/${id}/checkin`);
      message.success('登记成功');
      fetch();
    } catch (err) {
      message.error(err.response?.data?.detail || '登记失败');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Card title="到站登记">
      <Input.Search
        placeholder="输入车牌号查询"
        value={plate}
        onChange={(e) => setPlate(e.target.value)}
        onSearch={fetch}
        enterButton="刷新"
        style={{ marginBottom: 16 }}
      />
      {candidates.length === 0 && <Empty description="无待签到预约" />}
      <List
        loading={loading}
        dataSource={candidates}
        renderItem={(item) => (
          <List.Item
            actions={[
              <Button type="primary" loading={busyId === item.id} disabled={busyId !== null} onClick={() => checkin(item.id)}>确认到站</Button>,
            ]}
          >
            <List.Item.Meta
              title={item.vehicle?.plate_number}
              description={
                <>
                  <div>{item.station?.name} {item.appointment_date} {item.time_slot}</div>
                  <Tag color={statusMap[item.status]?.color}>{statusMap[item.status]?.text || item.status}</Tag>
                </>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  );
}
