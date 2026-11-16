import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MyAppointments from './MyAppointments';

vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
      warning: vi.fn(),
    },
  };
});

vi.mock('../../utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import request from '../../utils/request';

describe('MyAppointments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: [
        { id: 1, vehicle: { plate_number: '鲁A11111' }, station: { name: '站A' }, appointment_date: '2026-09-10', time_slot: '08:00-10:00', status: 'booked' },
        { id: 2, vehicle: { plate_number: '鲁A22222' }, station: { name: '站B' }, appointment_date: '2026-09-10', time_slot: '10:00-12:00', status: 'completed' },
      ],
    });
  });

  it('lists appointments and cancels a booked one', async () => {
    request.post.mockResolvedValue({});
    render(<MyAppointments />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    const cancelButton = screen.getByText(/取.*消/);
    await userEvent.click(cancelButton);
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/appointments/1/cancel'));
    // 等待取消后的重新查询完成，避免 teardown 后仍有 scheduler 任务
    await waitFor(() => expect(request.get).toHaveBeenCalledTimes(2));
  });

  it('shows error when cancel fails', async () => {
    request.post.mockRejectedValue({ response: { data: { detail: '取消失败' } } });
    render(<MyAppointments />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /取.*消/ }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/appointments/1/cancel'));
    expect(request.get).toHaveBeenCalledTimes(1);
  });

  it('prevents double submit while cancel is in flight', async () => {
    let resolvePost;
    request.post.mockImplementation(() => new Promise((r) => { resolvePost = r; }));
    render(<MyAppointments />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    const btn = screen.getByRole('button', { name: /取.*消/ });
    await userEvent.click(btn);
    await waitFor(() => expect(screen.getByRole('button', { name: /取.*消/ })).toBeDisabled());
    // 按钮禁用期间再次点击不应触发第二个请求
    fireEvent.click(btn);
    resolvePost({});
    await waitFor(() => expect(request.get).toHaveBeenCalledTimes(2));
    expect(request.post).toHaveBeenCalledTimes(1);
  });
});
