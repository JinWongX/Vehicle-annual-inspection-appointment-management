import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StatisticsDashboard from './StatisticsDashboard';

vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
    },
  };
});

vi.mock('../../utils/request', () => ({
  default: {
    get: vi.fn(),
  },
}));

import request from '../../utils/request';
import { message } from 'antd';

describe('StatisticsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: {
        total_count: 10,
        pass_count: 7,
        fail_count: 2,
        retest_count: 1,
        pass_rate: 70.0,
        fail_reasons: { 灯光: 1, 制动: 1 },
      },
    });
  });

  it('loads statistics and queries with date range', async () => {
    render(<StatisticsDashboard />);
    await waitFor(() => expect(screen.getByText('检测总数')).toBeInTheDocument());
    expect(screen.getByText('70')).toBeInTheDocument();
    // 等待初始查询完成，按钮不再处于 loading 状态后再点击
    await waitFor(() => expect(request.get).toHaveBeenCalledTimes(1));
    await userEvent.click(screen.getByRole('button', { name: /查.*询/ }));
    await waitFor(() => expect(request.get).toHaveBeenCalledTimes(2));
  });

  it('shows error when statistics request fails', async () => {
    request.get.mockRejectedValue({ response: { data: { detail: '统计异常' } } });
    render(<StatisticsDashboard />);
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('统计异常'));
  });

  it('renders empty charts when counts and fail_reasons are empty', async () => {
    request.get.mockResolvedValue({
      data: {
        total_count: 0,
        pass_count: 0,
        fail_count: 0,
        retest_count: 0,
        pass_rate: 0,
        fail_reasons: null,
      },
    });
    render(<StatisticsDashboard />);
    await waitFor(() => expect(screen.getByText('检测总数')).toBeInTheDocument());
    const empties = document.querySelectorAll('.ant-empty');
    expect(empties).toHaveLength(2);
  });

  it('blocks query when start date is after end date', async () => {
    render(<StatisticsDashboard />);
    await waitFor(() => expect(request.get).toHaveBeenCalledTimes(1));
    const startInput = screen.getByPlaceholderText('开始日期');
    await userEvent.clear(startInput);
    await userEvent.type(startInput, '2027-01-01');
    await userEvent.keyboard('{Enter}');
    await userEvent.click(screen.getByRole('button', { name: /查.*询/ }));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('开始日期不能晚于结束日期'));
    expect(request.get).toHaveBeenCalledTimes(1);
  });
});
