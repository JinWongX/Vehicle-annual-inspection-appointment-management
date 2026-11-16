import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

const mockForm = vi.hoisted(() => ({
  resetFields: vi.fn(),
  setFieldsValue: vi.fn(),
  validateFields: vi.fn(),
  getFieldsValue: vi.fn(),
  getInternalHooks: vi.fn(() => ({ registerWatch: vi.fn(() => vi.fn()), getFieldValue: vi.fn() })),
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  const FormModule = actual.default || actual;
  const Form = FormModule.Form;
  const MockForm = ({ children, onFinish, ...props }) =>
    React.createElement('form', {
      'data-testid': 'mock-form',
      onSubmit: async (e) => {
        e.preventDefault();
        if (onFinish) {
          try {
            const values = await mockForm.validateFields();
            onFinish(values);
          } catch {}
        }
      },
      ...props,
    }, children);
  Object.assign(MockForm, Form);
  MockForm.useForm = vi.fn(() => [mockForm]);

  return {
    ...actual,
    Form: MockForm,
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

const StationReportEntry = (await import('./StationReportEntry')).default;
import request from '../../utils/request';
import { Form, message } from 'antd';

describe('StationReportEntry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: [
        { id: 1, vehicle: { plate_number: '鲁A11111' }, station: { name: '站A' }, appointment_date: '2026-09-07', time_slot: '08:00-10:00', status: 'checking' },
      ],
    });
  });

  it('Form mock is active', () => {
    const [form] = Form.useForm();
    expect(form).toBe(mockForm);
  });

  it('submits inspection report', async () => {
    mockForm.validateFields.mockResolvedValue({
      appointment_id: 1,
      result: 'pass',
      overall_comment: '合格',
      items: [{ item_name: '制动', result: 'pass', comment: '正常' }],
    });
    request.post.mockResolvedValue({});

    render(<StationReportEntry />);
    await waitFor(() => expect(screen.getByText(/选择待录入预约/)).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /提.*交.*结.*果/ }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/reports', expect.objectContaining({
      appointment_id: 1,
      result: 'pass',
      items: expect.any(Array),
    })));
  });

  it('submits inspection report with multiple items', async () => {
    mockForm.validateFields.mockResolvedValue({
      appointment_id: 1,
      result: 'pass',
      overall_comment: '合格',
      items: [
        { item_name: '制动', result: 'pass', comment: '正常' },
        { item_name: '灯光', result: 'fail', comment: '不亮' },
      ],
    });
    request.post.mockResolvedValue({});

    render(<StationReportEntry />);
    await waitFor(() => expect(screen.getByText(/选择待录入预约/)).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /提.*交.*结.*果/ }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/reports', expect.objectContaining({
      appointment_id: 1,
      result: 'pass',
      items: [
        { item_name: '制动', result: 'pass', comment: '正常' },
        { item_name: '灯光', result: 'fail', comment: '不亮' },
      ],
    })));
  });

  it('shows error when submit fails', async () => {
    mockForm.validateFields.mockResolvedValue({
      appointment_id: 1,
      result: 'fail',
      overall_comment: '不合格',
    });
    request.post.mockRejectedValue({ response: { data: { detail: '录入失败' } } });

    render(<StationReportEntry />);
    await waitFor(() => expect(screen.getByText(/选择待录入预约/)).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /提.*交.*结.*果/ }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/reports', expect.objectContaining({
      appointment_id: 1,
      result: 'fail',
      items: [],
    })));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('录入失败'));
  });
});
