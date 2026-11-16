import { useEffect, useState } from 'react';
import { Layout as AntLayout, Menu, Button, Typography, Space, theme } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  CarOutlined,
  BellOutlined,
  CalendarOutlined,
  OrderedListOutlined,
  FileTextOutlined,
  EnvironmentOutlined,
  BarChartOutlined,
  ExportOutlined,
  LogoutOutlined,
  DashboardOutlined,
  AuditOutlined,
  FormOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';

const { Header, Sider, Content } = AntLayout;
const { Title } = Typography;

const roleLabels = {
  owner: '车主',
  station: '检测站',
  admin: '车管所',
};

const menus = {
  owner: [
    { key: '/', icon: <BellOutlined />, label: '年检提醒' },
    { key: '/vehicles', icon: <CarOutlined />, label: '我的车辆' },
    { key: '/appointment', icon: <CalendarOutlined />, label: '我要预约' },
    { key: '/my-appointments', icon: <OrderedListOutlined />, label: '我的预约' },
    { key: '/reports', icon: <FileTextOutlined />, label: '检测报告' },
  ],
  station: [
    { key: '/', icon: <DashboardOutlined />, label: '今日预约' },
    { key: '/station-checkin', icon: <AuditOutlined />, label: '到站登记' },
    { key: '/station-report', icon: <FormOutlined />, label: '结果录入' },
  ],
  admin: [
    { key: '/', icon: <BarChartOutlined />, label: '统计看板' },
    { key: '/stations', icon: <EnvironmentOutlined />, label: '检测站管理' },
    { key: '/users', icon: <TeamOutlined />, label: '用户管理' },
    { key: '/export', icon: <ExportOutlined />, label: '数据导出' },
  ],
};

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  useEffect(() => {
    if (!user) {
      navigate('/login', { replace: true });
    }
  }, [user, navigate]);

  if (!user) return null;

  const role = user.role;
  const items = menus[role] || [];

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} theme="light">
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Title level={collapsed ? 5 : 4} style={{ margin: 0 }}>年检</Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={items}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{ background: colorBgContainer, padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Space>
            <span style={{ fontSize: 16, fontWeight: 500 }}>车辆年检预约管理系统</span>
            <span style={{ color: '#888' }}>|</span>
            <span>{roleLabels[role]}端</span>
          </Space>
          <Space>
            <span>{user.real_name || user.username}</span>
            <Button icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login', { replace: true }); }}>
              退出
            </Button>
          </Space>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: colorBgContainer, borderRadius: borderRadiusLG, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
