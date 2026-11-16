import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './AuthContext';

// mock request module to avoid real network calls
vi.mock('../utils/request', () => {
  return {
    default: {
      post: vi.fn(),
      get: vi.fn(),
      defaults: { headers: {} },
    },
  };
});

import request from '../utils/request';

function TestComponent() {
  const { user, loading, login, registerAndLogin, logout } = useAuth();
  if (loading) return <div data-testid="loading">loading</div>;
  return (
    <div>
      <div data-testid="user">{user ? user.username : 'no-user'}</div>
      <button onClick={() => login('alice', 'pass123')}>login</button>
      <button onClick={() => registerAndLogin({ username: 'bob', password: 'pass123' })}>
        registerAndLogin
      </button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

function setup(initialStorage = {}) {
  localStorage.clear();
  Object.entries(initialStorage).forEach(([k, v]) => localStorage.setItem(k, v));
  return render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    request.post.mockReset();
    request.get.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('validates token via /auth/me and restores user on mount', async () => {
    request.get.mockResolvedValue({ data: { username: 'alice', role: 'owner' } });
    setup({
      inspection_token: 'token123',
      inspection_user: JSON.stringify({ username: 'alice', role: 'owner' }),
    });
    await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('alice'));
    expect(request.get).toHaveBeenCalledWith('/auth/me');
  });

  it('clears stale token when /auth/me fails on mount', async () => {
    request.get.mockRejectedValue({ response: { status: 401 } });
    setup({
      inspection_token: 'expired-token',
      inspection_user: JSON.stringify({ username: 'alice', role: 'owner' }),
    });
    await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('no-user'));
    expect(localStorage.getItem('inspection_token')).toBeNull();
  });

  it('does not restore user when token missing', async () => {
    setup({ inspection_user: JSON.stringify({ username: 'alice' }) });
    await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('no-user'));
    expect(request.get).not.toHaveBeenCalledWith('/auth/me');
  });

  it('login stores token and user then sets state', async () => {
    request.post.mockResolvedValueOnce({ data: { access_token: 'new-token' } });
    request.get.mockResolvedValue({ data: { username: 'alice', role: 'owner' } });

    setup();
    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument());
    await act(async () => userEvent.click(screen.getByRole('button', { name: /^login$/i })));

    await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('alice'));
    expect(localStorage.getItem('inspection_token')).toBe('new-token');
  });

  it('registerAndLogin registers then logs in', async () => {
    request.post
      .mockResolvedValueOnce({ data: {} })
      .mockResolvedValueOnce({ data: { access_token: 'reg-token' } });
    request.get.mockResolvedValue({ data: { username: 'bob', role: 'owner' } });

    setup();
    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument());
    await act(async () =>
      userEvent.click(screen.getByRole('button', { name: /registerAndLogin/i }))
    );

    await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('bob'));
    expect(request.post).toHaveBeenCalledWith('/auth/register', {
      username: 'bob',
      password: 'pass123',
    });
  });

  it('logout clears storage and user state', async () => {
    request.get.mockResolvedValue({ data: { username: 'alice', role: 'owner' } });
    setup({
      inspection_token: 'token123',
      inspection_user: JSON.stringify({ username: 'alice', role: 'owner' }),
    });
    await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('alice'));
    await act(async () => userEvent.click(screen.getByRole('button', { name: /logout/i })));
    expect(screen.getByTestId('user').textContent).toBe('no-user');
    expect(localStorage.getItem('inspection_token')).toBeNull();
  });

  it('clears user state on auth:expired event', async () => {
    request.get.mockResolvedValue({ data: { username: 'alice', role: 'owner' } });
    setup({
      inspection_token: 'token123',
      inspection_user: JSON.stringify({ username: 'alice', role: 'owner' }),
    });
    await waitFor(() => expect(screen.getByTestId('user').textContent).toBe('alice'));
    await act(async () => {
      window.dispatchEvent(new Event('auth:expired'));
    });
    expect(screen.getByTestId('user').textContent).toBe('no-user');
    expect(localStorage.getItem('inspection_token')).toBeNull();
  });
});