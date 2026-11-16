import { useEffect, useState } from 'react';
import { Card, Form, Select, DatePicker, Button, List, Tag, Radio, message, Empty } from 'antd';
import dayjs from 'dayjs';
import request from '../../utils/request';

export default function Appointment() {
  const [form] = Form.useForm();
  const [vehicles, setVehicles] = useState([]);
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedStation, setSelectedStation] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);

  useEffect(() => {
    request.get('/vehicles').then((res) => setVehicles(res.data || []));
  }, []);

  const handleQuery = async () => {
    const { vehicle_id, date } = await form.validateFields(['vehicle_id', 'date']);
    const vehicle = vehicles.find((v) => v.id === vehicle_id);
    if (!vehicle) return;
    setSelectedStation(null);
    setSelectedSlot(null);
    setLoading(true);
    try {
      const res = await request.get('/stations/available', {
        params: {
          vehicle_type: vehicle.vehicle_type,
          date: date.format('YYYY-MM-DD'),
        },
      });
      setStations(res.data || []);
    } catch (err) {
      message.error(err.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    const { vehicle_id, date } = form.getFieldsValue(['vehicle_id', 'date']);
    if (!selectedStation || !selectedSlot) {
      message.warning('请选择检测站与时段');
      return;
    }
    setSubmitting(true);
    try {
      await request.post('/appointments', {
        vehicle_id: vehicle_id,
        station_id: selectedStation.station.id,
        appointment_date: date.format('YYYY-MM-DD'),
        time_slot: selectedSlot.time_slot,
      });
      message.success('预约成功');
      form.resetFields();
      setStations([]);
      setSelectedStation(null);
      setSelectedSlot(null);
    } catch (err) {
      message.error(err.response?.data?.detail || '预约失败');
    } finally {
      setSubmitting(false);
    }
  };

  const disabledDate = (current) => {
    return current && (current < dayjs().startOf('day') || current > dayjs().add(30, 'day').endOf('day'));
  };

  return (
    <Card title="我要预约" loading={loading}>
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item name="vehicle_id" label="选择车辆" rules={[{ required: true, message: '请选择车辆' }]}>
          <Select
            placeholder="请选择车辆"
            options={vehicles.map((v) => ({ value: v.id, label: `${v.plate_number}（${v.vehicle_type}）` }))}
          />
        </Form.Item>
        <Form.Item name="date" label="预约日期" rules={[{ required: true, message: '请选择日期' }]}>
          <DatePicker format="YYYY-MM-DD" style={{ width: '100%' }} disabledDate={disabledDate} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" onClick={handleQuery}>查询可约检测站</Button>
        </Form.Item>
      </Form>

      {stations.length === 0 && !loading && <Empty description="暂无可用检测站" />}
      <List
        grid={{ gutter: 16, column: 1 }}
        dataSource={stations}
        renderItem={(item) => (
          <List.Item>
            <Card
              title={item.station.name}
              extra={<span>{item.station.address}</span>}
              style={{ border: selectedStation?.station.id === item.station.id ? '2px solid #1890ff' : undefined }}
              onClick={() => { setSelectedStation(item); setSelectedSlot(null); }}
            >
              <p>地址：{item.station.address || '-'}</p>
              <p>电话：{item.station.phone || '-'}</p>
              <Radio.Group
                value={selectedSlot?.time_slot}
                onChange={(e) => {
                  const slot = item.time_slots.find((s) => s.time_slot === e.target.value);
                  setSelectedStation(item);
                  setSelectedSlot(slot);
                }}
              >
                {item.time_slots.map((slot) => (
                  <Radio.Button key={slot.time_slot} value={slot.time_slot} disabled={slot.remaining <= 0}>
                    {slot.time_slot} <Tag color={slot.remaining > 0 ? 'green' : 'red'}>剩余 {slot.remaining}</Tag>
                  </Radio.Button>
                ))}
              </Radio.Group>
            </Card>
          </List.Item>
        )}
      />
      {selectedSlot && (
        <div style={{ marginTop: 16 }}>
          已选择：<Tag color="blue">{selectedStation.station.name} {selectedSlot.time_slot}</Tag>
          <Button type="primary" loading={submitting} onClick={handleSubmit} style={{ marginLeft: 16 }}>提交预约</Button>
        </div>
      )}
    </Card>
  );
}
