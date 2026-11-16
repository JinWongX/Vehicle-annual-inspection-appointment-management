import { useEffect, useState } from 'react';
import { Table, Button, Card, Modal, Form, Input, DatePicker, Select, Space, Tag, Popconfirm, message } from 'antd';
import dayjs from 'dayjs';
import request from '../../utils/request';

const USAGE_OPTIONS = [
  { value: 'non_operational', label: '非营运' },
  { value: 'commercial', label: '营运' },
];

export default function Vehicles() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const fetchVehicles = async () => {
    setLoading(true);
    try {
      const res = await request.get('/vehicles');
      setData(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVehicles();
  }, []);

  const handleAdd = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (record) => {
    setEditing(record);
    form.setFieldsValue({
      ...record,
      register_date: record.register_date ? dayjs(record.register_date) : null,
      next_inspection_date: record.next_inspection_date ? dayjs(record.next_inspection_date) : null,
    });
    setModalOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await request.delete(`/vehicles/${id}`);
      message.success('删除成功');
      fetchVehicles();
    } catch (err) {
      message.error(err.response?.data?.detail || '删除失败');
    }
  };

  const handleOk = async () => {
    const values = await form.validateFields();
    const payload = {
      ...values,
      register_date: values.register_date ? values.register_date.format('YYYY-MM-DD') : undefined,
      next_inspection_date: values.next_inspection_date ? values.next_inspection_date.format('YYYY-MM-DD') : undefined,
    };
    if (editing) {
      delete payload.plate_number;
    }
    try {
      if (editing) {
        await request.put(`/vehicles/${editing.id}`, payload);
      } else {
        await request.post('/vehicles', payload);
      }
      message.success('保存成功');
      setModalOpen(false);
      fetchVehicles();
    } catch (err) {
      message.error(err.response?.data?.detail || '保存失败');
    }
  };

  const columns = [
    { title: '车牌号', dataIndex: 'plate_number', key: 'plate_number' },
    { title: '车辆类型', dataIndex: 'vehicle_type', key: 'vehicle_type' },
    { title: '注册日期', dataIndex: 'register_date', key: 'register_date' },
    { title: '下次年检日期', dataIndex: 'next_inspection_date', key: 'next_inspection_date' },
    {
      title: '距年检天数',
      dataIndex: 'days_until_inspection',
      key: 'days_until_inspection',
      render: (v) => {
        if (v === null || v === undefined) return '-';
        if (v < 0) return <Tag color="red">已逾期</Tag>;
        if (v === 0) return <Tag color="orange">今日到期</Tag>;
        const color = v <= 30 ? 'orange' : 'green';
        return <Tag color={color}>{`${v} 天`}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除该车辆吗？" okText="删除" cancelText="取消" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card title="我的车辆" extra={<Button type="primary" onClick={handleAdd}>新增车辆</Button>}>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} />
      <Modal
        title={editing ? '编辑车辆' : '新增车辆'}
        open={modalOpen}
        onOk={handleOk}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="plate_number"
            label="车牌号"
            rules={[
              { required: true, message: '请输入车牌号' },
              { min: 5, max: 12, message: '车牌号长度应为 5–12 位' },
            ]}
          >
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item name="vehicle_type" label="车辆类型" rules={[{ required: true, message: '请输入车辆类型' }]}>
            <Input placeholder="如 small, large" />
          </Form.Item>
          <Form.Item name="usage_nature" label="使用性质">
            <Select options={USAGE_OPTIONS} placeholder="请选择" />
          </Form.Item>
          <Form.Item name="register_date" label="注册日期">
            <DatePicker format="YYYY-MM-DD" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="next_inspection_date" label="下次年检日期（留空则按注册日期自动计算）">
            <DatePicker format="YYYY-MM-DD" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
