import { useState } from 'react';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const { Title } = Typography;

// 将后端可能返回的英文/多种格式错误统一转成友好的中文提示
function resolveErrorMsg(err, fallback) {
  const detail = err?.response?.data?.detail;
  let msg = Array.isArray(detail)
    ? detail.map((d) => d.msg).join('；')
    : (detail || '');
  if (!msg) return fallback;
  const map = {
    'incorrect username or password': '用户名或密码错误',
    'user account disabled': '账号已被禁用',
  };
  for (const [key, zh] of Object.entries(map)) {
    if (msg.toLowerCase().includes(key)) return zh;
  }
  return msg;
}

export default function Login() {
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch (err) {
      message.error(resolveErrorMsg(err, '登录失败，请检查用户名或密码'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: 'center' }}>车辆年检预约系统</Title>
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>登录</Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            还没有账号？ <Link to="/register">立即注册</Link>
          </div>
        </Form>
      </Card>
    </div>
  );
}
