import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

const mockForm = vi.hoisted(() => ({
  resetFields: vi.fn(),
  setFieldsValue: vi.fn(),
  validateFields: vi.fn(),
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  const FormModule = actual.default || actual;
  const Form = FormModule.Form;
  const MockForm = ({ children }) => React.createElement('div', null, children);
  Object.assign(MockForm, Form);
  MockForm.useForm = vi.fn(() => [mockForm]);

  const MockModal = ({ children, title, open, onOk, onCancel }) => {
    if (!open) return null;
    return React.createElement('div', { className: 'ant-modal' },
      React.createElement('div', { className: 'ant-modal-title' }, title),
      React.createElement('div', { className: 'ant-modal-body' }, children),
      React.createElement('button', { onClick: onOk, type: 'button' }, 'OK'),
      React.createElement('button', { onClick: onCancel, type: 'button' }, 'Cancel')
    );
  };
  MockModal.info = vi.fn();
  MockModal.success = vi.fn();
  MockModal.error = vi.fn();
  MockModal.warning = vi.fn();
  MockModal.confirm = vi.fn();
  MockModal.destroyAll = vi.fn();
  MockModal.config = vi.fn();
  MockModal.useModal = vi.fn(() => [vi.fn(), vi.fn()]);

  return {
    ...actual,
    Form: MockForm,
    Modal: MockModal,
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
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const Vehicles = (await import('./Vehicles')).default;
import request from '../../utils/request';
import { Form, message } from 'antd';

describe('Vehicles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: [
        { id: 1, plate_number: '鲁A11111', vehicle_type: 'small_car', register_date: '2024-01-01', next_inspection_date: '2025-01-01', days_until_inspection: 10, usage_nature: 'non_operational' },
        { id: 2, plate_number: '鲁A22222', vehicle_type: 'small_car', register_date: '2024-01-01', next_inspection_date: null, days_until_inspection: null, usage_nature: 'non_operational' },
        { id: 3, plate_number: '鲁A33333', vehicle_type: 'small_car', register_date: '2024-01-01', next_inspection_date: '2024-01-01', days_until_inspection: -1, usage_nature: 'non_operational' },
      ],
    });
  });

  it('Form mock is active', () => {
    const [form] = Form.useForm();
    expect(form).toBe(mockForm);
  });

  it('loads and displays vehicles', async () => {
    render(<Vehicles />);
    await waitFor(() => expect(screen.getByText('鲁A11111')).toBeInTheDocument());
    expect(request.get).toHaveBeenCalledWith('/vehicles');
  });

  it('deletes a vehicle after Popconfirm confirmation', async () => {
    request.delete.mockResolvedValue({});
    render(<Vehicles />);
    await waitFor(() => screen.getByText('鲁A11111'));
    await userEvent.click(screen.getAllByText(/删除/)[0]);
    await screen.findByText('确定删除该车辆吗？');
    const popover = screen.getByText('确定删除该车辆吗？').closest('.ant-popover');
    await userEvent.click(within(popover).getByRole('button', { name: /删.*除/ }));
    await waitFor(() => expect(request.delete).toHaveBeenCalledWith('/vehicles/1'));
  });

  it('keeps the vehicle when Popconfirm is cancelled', async () => {
    render(<Vehicles />);
    await waitFor(() => screen.getByText('鲁A11111'));
    await userEvent.click(screen.getAllByText(/删除/)[0]);
    await screen.findByText('确定删除该车辆吗？');
    const popover = screen.getByText('确定删除该车辆吗？').closest('.ant-popover');
    await userEvent.click(within(popover).getByRole('button', { name: /取.*消/ }));
    expect(request.delete).not.toHaveBeenCalled();
  });

  it('opens add modal and submits new vehicle', async () => {
    mockForm.validateFields.mockResolvedValue({
      plate_number: '鲁A99999',
      vehicle_type: 'small',
      usage_nature: 'non_operational',
    });
    request.post.mockResolvedValue({});

    render(<Vehicles />);
    await waitFor(() => screen.getByText('鲁A11111'));
    await userEvent.click(screen.getByText(/新增车辆/));
    await waitFor(() => expect(screen.getByText('新增车辆', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/vehicles', expect.objectContaining({
      plate_number: '鲁A99999',
      vehicle_type: 'small',
    })));
  });

  it('opens edit modal and updates vehicle without date', async () => {
    mockForm.validateFields.mockResolvedValue({
      plate_number: '鲁A11111',
      vehicle_type: 'small_car',
      usage_nature: 'operational',
    });
    request.put.mockResolvedValue({});

    render(<Vehicles />);
    await waitFor(() => screen.getByText('鲁A11111'));
    const editButtons = screen.getAllByText(/编辑/);
    await userEvent.click(editButtons[0]);
    await waitFor(() => expect(screen.getByText('编辑车辆', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(request.put).toHaveBeenCalledWith('/vehicles/1', expect.objectContaining({
      vehicle_type: 'small_car',
      usage_nature: 'operational',
    })));
  });

  it('opens edit modal with null register_date and next_inspection_date', async () => {
    request.get.mockResolvedValue({
      data: [
        { id: 5, plate_number: '鲁A55555', vehicle_type: 'small_car', register_date: null, next_inspection_date: null, days_until_inspection: null, usage_nature: 'non_operational' },
      ],
    });
    render(<Vehicles />);
    await waitFor(() => screen.getByText('鲁A55555'));
    const editButtons = screen.getAllByText(/编辑/);
    await userEvent.click(editButtons[0]);
    await waitFor(() => expect(screen.getByText('编辑车辆', { selector: '.ant-modal-title' })).toBeInTheDocument());
    await waitFor(() => expect(mockForm.setFieldsValue).toHaveBeenCalledWith(expect.objectContaining({
      register_date: null,
      next_inspection_date: null,
    })));
  });

  it('shows error when delete fails', async () => {
    request.delete.mockRejectedValue({ response: { data: { detail: '删除失败测试' } } });
    render(<Vehicles />);
    await waitFor(() => screen.getByText('鲁A11111'));
    await userEvent.click(screen.getAllByText(/删除/)[0]);
    await screen.findByText('确定删除该车辆吗？');
    const popover = screen.getByText('确定删除该车辆吗？').closest('.ant-popover');
    await userEvent.click(within(popover).getByRole('button', { name: /删.*除/ }));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('删除失败测试'));
  });

  it('shows error when save fails', async () => {
    mockForm.validateFields.mockResolvedValue({
      plate_number: '鲁A11111',
      vehicle_type: 'small_car',
      usage_nature: 'operational',
    });
    request.put.mockRejectedValue({ response: { data: { detail: '保存失败测试' } } });

    render(<Vehicles />);
    await waitFor(() => screen.getByText('鲁A11111'));
    const editButtons = screen.getAllByText(/编辑/);
    await userEvent.click(editButtons[0]);
    await waitFor(() => expect(screen.getByText('编辑车辆', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('保存失败测试'));
  });

  it('displays days_until_inspection branches including 今日到期', async () => {
    request.get.mockResolvedValue({
      data: [
        { id: 1, plate_number: '鲁A11111', vehicle_type: 'small_car', register_date: '2024-01-01', next_inspection_date: '2025-01-01', days_until_inspection: 0, usage_nature: 'non_operational' },
        { id: 2, plate_number: '鲁A22222', vehicle_type: 'small_car', register_date: '2024-01-01', next_inspection_date: '2025-01-01', days_until_inspection: 31, usage_nature: 'non_operational' },
        { id: 3, plate_number: '鲁A33333', vehicle_type: 'small_car', register_date: '2024-01-01', next_inspection_date: null, days_until_inspection: null, usage_nature: 'non_operational' },
      ],
    });
    render(<Vehicles />);
    await waitFor(() => expect(screen.getByText('今日到期')).toBeInTheDocument());
    expect(screen.getByText('31 天')).toBeInTheDocument();
    expect(screen.getByText('-')).toBeInTheDocument();
  });
});
