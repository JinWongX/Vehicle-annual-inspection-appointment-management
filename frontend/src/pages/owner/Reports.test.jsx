import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Reports from './Reports';

vi.mock('../../utils/request', () => ({
  default: {
    get: vi.fn(),
  },
}));

import request from '../../utils/request';

describe('Reports', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: [
        {
          id: 1,
          result: 'pass',
          sticker_code: 'VIC-20260907-1-鲁A11111',
          overall_comment: '备注',
          items: [{ item_name: '制动', result: 'pass', comment: '正常' }],
          appointment: {
            appointment_date: '2026-09-07',
            vehicle: { plate_number: '鲁A11111' },
            station: { name: '站A' },
          },
        },
      ],
    });
  });

  it('displays reports and expands items', async () => {
    render(<Reports />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    expect(screen.getByText('合格')).toBeInTheDocument();
  });

  it('expands a report row to show overall comment and item details', async () => {
    render(<Reports />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());

    const expandIcon = document.querySelector('.ant-table-row-expand-icon');
    expect(expandIcon).toBeInTheDocument();
    await userEvent.click(expandIcon);

    await waitFor(() => {
      const expandedRow = document.querySelector('.ant-table-expanded-row');
      expect(expandedRow).toBeInTheDocument();
      expect(expandedRow.textContent).toContain('总体备注：备注');
      expect(expandedRow.textContent).toContain('制动');
      expect(expandedRow.textContent).toContain('合格');
      expect(expandedRow.textContent).toContain('备注：正常');
    });
  });
});
