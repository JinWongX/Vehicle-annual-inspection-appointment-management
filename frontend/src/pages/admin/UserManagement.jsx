import { useEffect, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Tag, Popconfirm, message } from 'antd';
import request from '../../utils/request';

const ROLE_OPTIONS = [
  { value: 'owner', label: '车主' },
  { value: 'station', label: '检测站' },
  { value: 'admin', label: '车管所' },
];

const roleTag = {
  owner: { color: 'blue', label: '车主' },
  station: { color: 'orange', label: '检测站' },
  admin: { color: 'red', label: '车管所' },
};

export default function UserManagement() {
  const [data, setData] = useState([]);
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const role = Form.useWatch('role', form);

  const fetchStations = async () => {
    try {
      const res = await request.get('/stations');
      setStations(res.data || []);
    } catch {
      setStations([]);
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await request.get('/users');
      setData(res.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchStations();
  }, []);

  const openCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (user) => {
    setEditingUser(user);
    form.setFieldsValue({
      role: user.role,
      phone: user.phone,
      real_name: user.real_name,
      station_id: user.station_id ?? undefined,
    });
    setModalOpen(true);
  };

  const handleOk = async () => {
    const values = await form.validateFields();
    const payload = {
      role: values.role,
      phone: values.phone,
      real_name: values.real_name,
    };
    if (values.role === 'station') {
      payload.station_id = values.station_id;
    }
    setSubmitting(true);
    try {
      if (editingUser) {
        await request.put(`/users/${editingUser.id}`, payload);
        message.success('更新成功');
      } else {
        await request.post('/users', { ...payload, username: values.username, password: values.password });
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchUsers();
    } catch (err) {
      message.error(err.response?.data?.detail || (editingUser ? '更新失败' : '创建失败'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (user) => {
    try {
      await request.delete(`/users/${user.id}`);
      message.success('删除成功');
      fetchUsers();
    } catch (err) {
      message.error(err.response?.data?.detail || '删除失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '姓名', dataIndex: 'real_name', key: 'real_name' },
    { title: '手机号', dataIndex: 'phone', key: 'phone' },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (v) => <Tag color={roleTag[v]?.color}>{roleTag[v]?.label || v}</Tag>,
    },
    {
      title: '归属检测站',
      dataIndex: 'station_id',
      key: 'station_id',
      render: (v) => stations.find((s) => s.id === v)?.name || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_, record) => (
        <span>
          <Button type="link" size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm
            title="确定删除该用户？"
            okText="删除"
            cancelText="取消"
            onConfirm={() => handleDelete(record)}
          >
            <Button type="link" size="small" danger disabled={record.username === 'admin'}>删除</Button>
          </Popconfirm>
        </span>
      ),
    },
  ];

  return (
    <Card title="用户管理" extra={<Button type="primary" onClick={openCreate}>新增用户</Button>}>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} />
      <Modal
        title={editingUser ? '编辑用户' : '新增用户'}
        open={modalOpen}
        onOk={handleOk}
        confirmLoading={submitting}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          {!editingUser && (
            <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input />
            </Form.Item>
          )}
          {!editingUser && (
            <Form.Item
              name="password"
              label="密码"
              extra="至少 8 位"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 8, message: '密码至少 8 位' },
              ]}
            >
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="role" label="角色" rules={[{ required: true, message: '请选择角色' }]}>
            <Select options={ROLE_OPTIONS} placeholder="请选择角色" disabled={editingUser?.username === 'admin'} />
          </Form.Item>
          <Form.Item name="real_name" label="姓名">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input />
          </Form.Item>
          {role === 'station' && (
            <Form.Item name="station_id" label="归属检测站" rules={[{ required: true, message: '请选择归属检测站' }]}>
              <Select
                options={stations.map((s) => ({ value: s.id, label: s.name }))}
                placeholder="请选择检测站"
              />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </Card>
  );
}