import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

const Appointment = (await import('./Appointment')).default;
import request from '../../utils/request';
import { Form, message } from 'antd';

describe('Appointment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockImplementation((url) => {
      if (url === '/vehicles') {
        return Promise.resolve({ data: [{ id: 1, plate_number: '鲁A11111', vehicle_type: 'small_car' }] });
      }
      if (url.startsWith('/stations/available')) {
        return Promise.resolve({
          data: [
            {
              station: { id: 10, name: '站A', address: '地址A', phone: '010' },
              time_slots: [
                { time_slot: '08:00-10:00', remaining: 2 },
                { time_slot: '10:00-12:00', remaining: 0 },
              ],
            },
          ],
        });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it('Form mock is active', () => {
    const [form] = Form.useForm();
    expect(form).toBe(mockForm);
  });

  it('queries available stations and submits appointment', async () => {
    const testDate = { format: () => '2026-09-10' };
    mockForm.validateFields.mockResolvedValue({
      vehicle_id: 1,
      date: testDate,
    });
    mockForm.getFieldsValue.mockReturnValue({
      vehicle_id: 1,
      date: testDate,
    });
    request.post.mockResolvedValue({});

    render(<Appointment />);
    await waitFor(() => expect(screen.getByText(/查询可约检测站/)).toBeInTheDocument());
    await userEvent.click(screen.getByText(/查询可约检测站/));
    await waitFor(() => expect(screen.getByText('站A')).toBeInTheDocument());

    await userEvent.click(screen.getByText('08:00-10:00'));
    await userEvent.click(screen.getByRole('button', { name: /提.*交.*预.*约/ }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/appointments', expect.objectContaining({
      vehicle_id: 1,
      station_id: 10,
      appointment_date: '2026-09-10',
      time_slot: '08:00-10:00',
    })));
  });

  it('shows error when query fails', async () => {
    const testDate = { format: () => '2026-09-10' };
    mockForm.validateFields.mockResolvedValue({
      vehicle_id: 1,
      date: testDate,
    });
    request.get.mockImplementation((url) => {
      if (url === '/vehicles') {
        return Promise.resolve({ data: [{ id: 1, plate_number: '鲁A11111', vehicle_type: 'small_car' }] });
      }
      if (url === '/stations/available') {
        return Promise.reject({ response: { data: { detail: '查询失败测试' } } });
      }
      return Promise.resolve({ data: [] });
    });

    render(<Appointment />);
    await waitFor(() => expect(screen.getByText(/查询可约检测站/)).toBeInTheDocument());
    await userEvent.click(screen.getByText(/查询可约检测站/));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('查询失败测试'));
  });

  it('warns when submitting without selecting a station or slot', async () => {
    const testDate = { format: () => '2026-09-10' };
    mockForm.validateFields.mockResolvedValue({
      vehicle_id: 1,
      date: testDate,
    });
    mockForm.getFieldsValue.mockReturnValue({
      vehicle_id: 1,
      date: testDate,
    });

    render(<Appointment />);
    await waitFor(() => expect(screen.getByText(/查询可约检测站/)).toBeInTheDocument());
    fireEvent.submit(screen.getByTestId('mock-form'));
    await waitFor(() => expect(message.warning).toHaveBeenCalledWith('请选择检测站与时段'));
  });

  it('shows error when submit fails', async () => {
    const testDate = { format: () => '2026-09-10' };
    mockForm.validateFields.mockResolvedValue({
      vehicle_id: 1,
      date: testDate,
    });
    mockForm.getFieldsValue.mockReturnValue({
      vehicle_id: 1,
      date: testDate,
    });
    request.post.mockRejectedValue({ response: { data: { detail: '预约失败测试' } } });

    render(<Appointment />);
    await waitFor(() => expect(screen.getByText(/查询可约检测站/)).toBeInTheDocument());
    await userEvent.click(screen.getByText(/查询可约检测站/));
    await waitFor(() => expect(screen.getByText('站A')).toBeInTheDocument());

    await userEvent.click(screen.getByText('08:00-10:00'));
    await userEvent.click(screen.getByRole('button', { name: /提.*交.*预.*约/ }));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('预约失败测试'));
  });
});
