import { useEffect, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, InputNumber, Space, Popconfirm, message } from 'antd';
import request from '../../utils/request';

export default function StationManagement() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await request.get('/stations');
      setData(res.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const handleAdd = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (record) => {
    setEditing(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await request.delete(`/stations/${id}`);
      message.success('删除成功');
      fetch();
    } catch (err) {
      message.error(err.response?.data?.detail || '删除失败');
    }
  };

  const handleOk = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await request.put(`/stations/${editing.id}`, values);
      } else {
        await request.post('/stations', values);
      }
      message.success('保存成功');
      setModalOpen(false);
      fetch();
    } catch (err) {
      message.error(err.response?.data?.detail || '保存失败');
    }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '地址', dataIndex: 'address', key: 'address' },
    { title: '电话', dataIndex: 'phone', key: 'phone' },
    { title: '可检车型', dataIndex: 'allowed_vehicle_types', key: 'allowed_vehicle_types' },
    { title: '日容量', dataIndex: 'daily_capacity', key: 'daily_capacity' },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除该检测站吗？" okText="删除" cancelText="取消" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card title="检测站管理" extra={<Button type="primary" onClick={handleAdd}>新增检测站</Button>}>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} />
      <Modal
        title={editing ? '编辑检测站' : '新增检测站'}
        open={modalOpen}
        onOk={handleOk}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="address" label="地址">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="电话">
            <Input />
          </Form.Item>
          <Form.Item name="allowed_vehicle_types" label="可检车型（逗号分隔）">
            <Input placeholder="small, large" />
          </Form.Item>
          <Form.Item name="daily_capacity" label="日容量" rules={[{ required: true, message: '请输入日容量' }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
