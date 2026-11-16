import { vi } from 'vitest';

// 全局 mock ant-design 图标，避免 jsdom 下 ESM 问题
vi.mock('@ant-design/icons', () => ({
  WarningOutlined: () => <span data-testid="warning-icon" />,
  ClockCircleOutlined: () => <span data-testid="clock-icon" />,
  DashboardOutlined: () => <span data-testid="dashboard-icon" />,
  AuditOutlined: () => <span data-testid="audit-icon" />,
  FormOutlined: () => <span data-testid="form-icon" />,
  BarChartOutlined: () => <span data-testid="barchart-icon" />,
  EnvironmentOutlined: () => <span data-testid="env-icon" />,
  TeamOutlined: () => <span data-testid="team-icon" />,
  ExportOutlined: () => <span data-testid="export-icon" />,
  LogoutOutlined: (props) => <span {...props} data-testid="logout-icon" />,
  MinusCircleOutlined: (props) => <span {...props} data-testid="minus-icon" />,
  PlusOutlined: () => <span data-testid="plus-icon" />,
  CarOutlined: () => <span data-testid="car-icon" />,
  BellOutlined: () => <span data-testid="bell-icon" />,
  CalendarOutlined: () => <span data-testid="calendar-icon" />,
  OrderedListOutlined: () => <span data-testid="list-icon" />,
  FileTextOutlined: () => <span data-testid="file-icon" />,
}));

vi.mock('recharts', () => ({
  PieChart: ({ children }) => <div data-testid="pie-chart">{children}</div>,
  Pie: ({ children }) => <div>{children}</div>,
  Cell: () => null,
  Tooltip: () => null,
  Legend: () => null,
  BarChart: ({ children }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
}));
