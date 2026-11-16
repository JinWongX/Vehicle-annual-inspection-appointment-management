import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ProtectedRoute, RoleRoute } from './App';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    Navigate: ({ to }) => {
      mockNavigate(to);
      return null;
    },
  };
});

vi.mock('./context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

// 阻止 App.jsx 级联加载 ant-design 页面组件，仅测试路由守卫
vi.mock('./components/Layout', () => ({ default: () => <div data-testid="layout">Layout</div> }));
vi.mock('./pages/Login', () => ({ default: () => <div data-testid="login">Login</div> }));
vi.mock('./pages/Register', () => ({ default: () => <div data-testid="register">Register</div> }));
vi.mock('./pages/owner/Reminders', () => ({ default: () => <div data-testid="reminders">Reminders</div> }));
vi.mock('./pages/station/StationAppointments', () => ({ default: () => <div data-testid="station-appointments">StationAppointments</div> }));
vi.mock('./pages/admin/StatisticsDashboard', () => ({ default: () => <div data-testid="statistics-dashboard">StatisticsDashboard</div> }));

import { useAuth } from './context/AuthContext';
import App from './App';

function renderWithRouter(initialEntries, ui) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders children when authenticated', () => {
    useAuth.mockReturnValue({ user: { role: 'owner' }, loading: false });
    renderWithRouter(['/'], <ProtectedRoute><div data-testid="protected-child">child</div></ProtectedRoute>);
    expect(screen.getByTestId('protected-child')).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    useAuth.mockReturnValue({ user: null, loading: false });
    renderWithRouter(['/'], <ProtectedRoute><div>child</div></ProtectedRoute>);
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('returns null while loading', () => {
    useAuth.mockReturnValue({ user: null, loading: true });
    const { container } = renderWithRouter(['/'], <ProtectedRoute><div>child</div></ProtectedRoute>);
    expect(container.firstChild).toBeNull();
  });
});

describe('RoleRoute', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders children when role matches', () => {
    useAuth.mockReturnValue({ user: { role: 'admin' }, loading: false });
    renderWithRouter(['/admin'], <RoleRoute roles={['admin']}><div data-testid="role-child">admin</div></RoleRoute>);
    expect(screen.getByTestId('role-child')).toBeInTheDocument();
  });

  it('redirects to root when role does not match', () => {
    useAuth.mockReturnValue({ user: { role: 'owner' }, loading: false });
    renderWithRouter(['/admin'], <RoleRoute roles={['admin']}><div>admin</div></RoleRoute>);
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('redirects to login when not authenticated', () => {
    useAuth.mockReturnValue({ user: null, loading: false });
    renderWithRouter(['/admin'], <RoleRoute roles={['admin']}><div>admin</div></RoleRoute>);
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });
});

describe('App routing', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('redirects unauthenticated user to login', () => {
    useAuth.mockReturnValue({ user: null, loading: false });
    render(<App />);
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });
});
