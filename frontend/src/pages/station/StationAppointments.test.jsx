import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import dayjs from 'dayjs';
import StationAppointments from './StationAppointments';

vi.mock('../../utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import request from '../../utils/request';

describe('StationAppointments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: [
        { id: 1, vehicle: { plate_number: '鲁A11111' }, station: { name: '站A' }, appointment_date: dayjs().format('YYYY-MM-DD'), time_slot: '08:00-10:00', status: 'booked' },
        { id: 2, vehicle: { plate_number: '鲁A22222' }, station: { name: '站A' }, appointment_date: '2026-09-01', time_slot: '10:00-12:00', status: 'completed' },
      ],
    });
  });

  it('lists, filters and checks in appointments', async () => {
    request.post.mockResolvedValue({});
    render(<StationAppointments />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());

    await userEvent.click(screen.getByText('待签到'));
    await userEvent.click(screen.getByText('今日'));
    await userEvent.click(screen.getByText('全部'));

    const checkinButton = screen.getByText('登记到站');
    await userEvent.click(checkinButton);
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/appointments/1/checkin'));
    // 等待签到后的重新查询完成，避免 teardown 后仍有 scheduler 任务
    await waitFor(() => expect(request.get).toHaveBeenCalledTimes(2));
  });

  it('shows error when checkin fails', async () => {
    request.post.mockRejectedValue({ response: { data: { detail: '登记失败' } } });
    render(<StationAppointments />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    await userEvent.click(screen.getByText('登记到站'));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/appointments/1/checkin'));
    expect(request.get).toHaveBeenCalledTimes(1);
  });
});
