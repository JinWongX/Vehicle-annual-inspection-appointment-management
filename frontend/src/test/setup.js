import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import React from 'react'
import { act } from 'react'
import { vi, afterEach } from 'vitest'

// 每个用例结束后清理 DOM 并刷新 React 调度器，减少 antd 组件遗留的异步副作用
afterEach(async () => {
  cleanup()
  await act(async () => {})
})

// antd 组件依赖 matchMedia
Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  })),
})

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// DataExport 组件使用 Blob 下载
URL.createObjectURL = vi.fn(() => 'blob:test')
URL.revokeObjectURL = vi.fn()

// 全局 mock ant-design 图标，避免 jsdom 下部分图标组件 undefined
vi.mock('@ant-design/icons', () => ({
  WarningOutlined: () => React.createElement('span', { 'data-testid': 'warning-icon' }),
  ClockCircleOutlined: () => React.createElement('span', { 'data-testid': 'clock-icon' }),
  DashboardOutlined: () => React.createElement('span', { 'data-testid': 'dashboard-icon' }),
  AuditOutlined: () => React.createElement('span', { 'data-testid': 'audit-icon' }),
  FormOutlined: () => React.createElement('span', { 'data-testid': 'form-icon' }),
  BarChartOutlined: () => React.createElement('span', { 'data-testid': 'barchart-icon' }),
  EnvironmentOutlined: () => React.createElement('span', { 'data-testid': 'env-icon' }),
  TeamOutlined: () => React.createElement('span', { 'data-testid': 'team-icon' }),
  ExportOutlined: () => React.createElement('span', { 'data-testid': 'export-icon' }),
  LogoutOutlined: (props) => React.createElement('span', { ...props, 'data-testid': 'logout-icon' }),
  MinusCircleOutlined: (props) => React.createElement('span', { onClick: props.onClick, 'data-testid': 'minus-icon' }),
  PlusOutlined: () => React.createElement('span', { 'data-testid': 'plus-icon' }),
  CarOutlined: () => React.createElement('span', { 'data-testid': 'car-icon' }),
  BellOutlined: () => React.createElement('span', { 'data-testid': 'bell-icon' }),
  CalendarOutlined: () => React.createElement('span', { 'data-testid': 'calendar-icon' }),
  OrderedListOutlined: () => React.createElement('span', { 'data-testid': 'list-icon' }),
  FileTextOutlined: () => React.createElement('span', { 'data-testid': 'file-icon' }),
}))

// recharts 在 jsdom 下渲染复杂，使用轻量 mock
vi.mock('recharts', () => ({
  PieChart: ({ children }) => React.createElement('div', { 'data-testid': 'pie-chart' }, children),
  Pie: ({ children }) => React.createElement('div', null, children),
  Cell: () => null,
  Tooltip: () => null,
  Legend: () => null,
  BarChart: ({ children }) => React.createElement('div', { 'data-testid': 'bar-chart' }, children),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  ResponsiveContainer: ({ children }) => React.createElement('div', null, children),
}))

// 禁用 antd 的 CSSMotion 动画，避免 jsdom 下留下未完成的定时器导致测试超时
vi.mock('@rc-component/motion', () => {
  const renderMotion = ({ children, visible }) => {
    if (visible === false) return null
    return typeof children === 'function' ? children({}) : children
  }
  return {
    __esModule: true,
    default: renderMotion,
    genCSSMotion: () => renderMotion,
    CSSMotionList: ({ children }) => children,
    Provider: ({ children }) => children,
  }
})
