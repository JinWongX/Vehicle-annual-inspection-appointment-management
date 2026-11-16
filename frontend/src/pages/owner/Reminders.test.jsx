import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Reminders from './Reminders';

vi.mock('../../utils/request', () => ({
  default: {
    get: vi.fn(),
  },
}));

import request from '../../utils/request';

describe('Reminders', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: [
        { id: 1, plate_number: '鲁A11111', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: -1 },
        { id: 2, plate_number: '鲁A22222', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: 0 },
        { id: 3, plate_number: '鲁A33333', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: 15 },
        { id: 4, plate_number: '鲁A44444', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: 90 },
      ],
    });
  });

  it('displays reminder statistics and list', async () => {
    render(<Reminders />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    expect(screen.getByText('60 天内到期')).toBeInTheDocument();
    await userEvent.click(screen.getByText(/刷.*新/));
    await waitFor(() => expect(request.get).toHaveBeenCalledTimes(2));
  });

  it('filters vehicles and shows tags for negative, zero, <=30, >30 and null days_until_inspection', async () => {
    request.get.mockResolvedValue({
      data: [
        { id: 1, plate_number: '鲁A11111', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: -5 },
        { id: 2, plate_number: '鲁A22222', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: 0 },
        { id: 3, plate_number: '鲁A33333', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: 20 },
        { id: 4, plate_number: '鲁A44444', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: 45 },
        { id: 5, plate_number: '鲁A55555', vehicle_type: 'small_car', next_inspection_date: '2024-01-01', days_until_inspection: null },
      ],
    });

    render(<Reminders />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());

    expect(screen.getByText('已逾期', { selector: '.ant-tag' })).toBeInTheDocument();
    expect(screen.getByText('今日到期', { selector: '.ant-tag' })).toBeInTheDocument();
    expect(screen.getByText('20 天', { selector: '.ant-tag' })).toBeInTheDocument();
    expect(screen.getByText('45 天', { selector: '.ant-tag' })).toBeInTheDocument();
    expect(screen.queryByText('鲁A55555')).not.toBeInTheDocument();

    // days: -5(已逾期) / 0·20(30天内) / 45(60天内)，三档互不重叠
    const tileValue = (title) => {
      const titleEl = screen.getByText(title, { selector: '.ant-statistic-title' });
      return titleEl.closest('.ant-statistic').querySelector('.ant-statistic-content-value').textContent;
    };
    expect(tileValue('已逾期')).toBe('1');
    expect(tileValue('30 天内到期')).toBe('2');
    expect(tileValue('60 天内到期')).toBe('1');
  });
});
