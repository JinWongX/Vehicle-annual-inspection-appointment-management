import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StationCheckin from './StationCheckin';

vi.mock('../../utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import request from '../../utils/request';

describe('StationCheckin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: [
        { id: 1, vehicle: { plate_number: '鲁A11111' }, station: { name: '站A' }, appointment_date: '2026-09-07', time_slot: '08:00-10:00', status: 'booked' },
        { id: 2, vehicle: { plate_number: '鲁B22222' }, station: { name: '站A' }, appointment_date: '2026-09-07', time_slot: '10:00-12:00', status: 'booked' },
      ],
    });
  });

  it('filters by plate and checks in', async () => {
    request.post.mockResolvedValue({});
    render(<StationCheckin />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());

    const searchInput = screen.getByPlaceholderText(/输入车牌号查询/);
    await userEvent.type(searchInput, '鲁A');

    const checkinButton = screen.getByText('确认到站');
    await userEvent.click(checkinButton);
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/appointments/1/checkin'));
  }, 10000);

  it('shows error when checkin fails', async () => {
    request.post.mockRejectedValue({ response: { data: { detail: '登记失败' } } });
    render(<StationCheckin />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());

    const searchInput = screen.getByPlaceholderText(/输入车牌号查询/);
    await userEvent.clear(searchInput);
    await userEvent.type(searchInput, '鲁A11111');

    const checkinButton = screen.getByRole('button', { name: /确认到站/ });
    await userEvent.click(checkinButton);
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/appointments/1/checkin'));
    expect(request.get).toHaveBeenCalledTimes(1);
  });

  it('filters candidates by plate', async () => {
    render(<StationCheckin />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    const searchInput = screen.getByPlaceholderText(/输入车牌号查询/);
    await userEvent.clear(searchInput);
    await userEvent.type(searchInput, '鲁B');
    await waitFor(() => {
      expect(screen.queryByText('鲁A11111')).not.toBeInTheDocument();
      expect(screen.getByText('鲁B22222')).toBeInTheDocument();
    });
  });

  it('prevents double submit while checkin is in flight', async () => {
    let resolvePost;
    request.post.mockImplementation(() => new Promise((r) => { resolvePost = r; }));
    render(<StationCheckin />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    const btn = screen.getAllByRole('button', { name: /确认到站/ })[0];
    await userEvent.click(btn);
    await waitFor(() => expect(screen.getAllByRole('button', { name: /确认到站/ })[0]).toBeDisabled());
    // 按钮禁用期间再次点击不应触发第二个请求
    fireEvent.click(btn);
    resolvePost({});
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/appointments/1/checkin'));
    expect(request.post).toHaveBeenCalledTimes(1);
  });
});
