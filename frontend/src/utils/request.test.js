import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';

// 每次重新加载模块，避免拦截器状态累积
async function loadRequest() {
  const mod = await import('./request');
  return mod.default;
}

describe('request axios instance', () => {
  let originalLocation;

  beforeEach(() => {
    localStorage.clear();
    originalLocation = window.location;
    delete window.location;
    window.location = { href: '' };
  });

  afterEach(() => {
    window.location = originalLocation;
    vi.restoreAllMocks();
  });

  it('attaches Bearer token when inspection_token exists', async () => {
    localStorage.setItem('inspection_token', 'abc123');
    const request = await loadRequest();
    const adapter = vi.fn().mockResolvedValue({ data: {}, status: 200, headers: {} });
    request.defaults.adapter = adapter;

    await request.get('/test');
    expect(adapter).toHaveBeenCalled();
    const config = adapter.mock.calls[0][0];
    expect(config.headers.Authorization).toBe('Bearer abc123');
  });

  it('does not attach Authorization header when no token', async () => {
    const request = await loadRequest();
    const adapter = vi.fn().mockResolvedValue({ data: {}, status: 200, headers: {} });
    request.defaults.adapter = adapter;

    await request.get('/test');
    const config = adapter.mock.calls[0][0];
    expect(config.headers.Authorization).toBeUndefined();
  });

  it('clears storage and redirects to login on 401', async () => {
    localStorage.setItem('inspection_token', 'abc123');
    localStorage.setItem('inspection_user', '{}');
    const request = await loadRequest();
    const error = new Error('Unauthorized');
    error.response = { status: 401 };
    request.defaults.adapter = vi.fn().mockRejectedValue(error);

    await expect(request.get('/test')).rejects.toThrow('Unauthorized');
    expect(localStorage.getItem('inspection_token')).toBeNull();
    expect(localStorage.getItem('inspection_user')).toBeNull();
    expect(window.location.href).toBe('/login');
  });

  it('does not redirect or clear storage on 401 from login endpoint', async () => {
    localStorage.setItem('inspection_token', 'abc123');
    localStorage.setItem('inspection_user', '{}');
    const request = await loadRequest();
    const error = new Error('Bad credentials');
    error.response = { status: 401 };
    error.config = { url: '/auth/login' };
    request.defaults.adapter = vi.fn().mockRejectedValue(error);

    await expect(request.post('/auth/login')).rejects.toThrow('Bad credentials');
    expect(localStorage.getItem('inspection_token')).toBe('abc123');
    expect(localStorage.getItem('inspection_user')).toBe('{}');
    expect(window.location.href).toBe('');
  });
});
