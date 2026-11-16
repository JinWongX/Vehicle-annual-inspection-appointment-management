import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
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

const StationManagement = (await import('./StationManagement')).default;
import request from '../../utils/request';
import { Form, message } from 'antd';

describe('StationManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({
      data: [{ id: 1, name: '站A', address: '地址A', phone: '010', allowed_vehicle_types: 'small_car', daily_capacity: 40 }],
    });
  });

  it('Form mock is active', () => {
    const [form] = Form.useForm();
    expect(form).toBe(mockForm);
  });

  it('displays stations and deletes one after Popconfirm confirmation', async () => {
    request.delete.mockResolvedValue({});
    render(<StationManagement />);
    await waitFor(() => expect(screen.getByText('站A')).toBeInTheDocument());
    await userEvent.click(screen.getAllByText(/删除/)[0]);
    await screen.findByText('确定删除该检测站吗？');
    const popover = screen.getByText('确定删除该检测站吗？').closest('.ant-popover');
    await userEvent.click(within(popover).getByRole('button', { name: /删.*除/ }));
    await waitFor(() => expect(request.delete).toHaveBeenCalledWith('/stations/1'));
  });

  it('adds a new station', async () => {
    mockForm.validateFields.mockResolvedValue({
      name: '站B', address: '地址B', phone: '020', allowed_vehicle_types: 'small_car', daily_capacity: 20,
    });
    request.post.mockResolvedValue({});

    render(<StationManagement />);
    await waitFor(() => screen.getByText('站A'));
    await userEvent.click(screen.getByText(/新增检测站/));
    await waitFor(() => expect(screen.getByText('新增检测站', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/stations', expect.objectContaining({
      name: '站B',
      daily_capacity: 20,
    })));
  });

  it('edits an existing station', async () => {
    mockForm.validateFields.mockResolvedValue({
      name: '站A-edit', address: '地址A-edit', phone: '010-edit', allowed_vehicle_types: 'small_car', daily_capacity: 50,
    });
    request.put.mockResolvedValue({});

    render(<StationManagement />);
    await waitFor(() => expect(screen.getByText('站A')).toBeInTheDocument());
    await userEvent.click(screen.getByText(/编辑/));
    await waitFor(() => expect(screen.getByText('编辑检测站', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(request.put).toHaveBeenCalledWith('/stations/1', expect.objectContaining({
      name: '站A-edit',
      daily_capacity: 50,
    })));
  });

  it('shows error when saving fails', async () => {
    mockForm.validateFields.mockResolvedValue({
      name: '站B', address: '地址B', phone: '020', allowed_vehicle_types: 'small_car', daily_capacity: 20,
    });
    request.post.mockRejectedValue({ response: { data: { detail: '保存异常' } } });

    render(<StationManagement />);
    await waitFor(() => expect(screen.getByText('站A')).toBeInTheDocument());
    await userEvent.click(screen.getByText(/新增检测站/));
    await waitFor(() => expect(screen.getByText('新增检测站', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('保存异常'));
  });

  it('shows error when deleting fails', async () => {
    request.delete.mockRejectedValue({ response: { data: { detail: '删除异常' } } });

    render(<StationManagement />);
    await waitFor(() => expect(screen.getByText('站A')).toBeInTheDocument());
    await userEvent.click(screen.getAllByText(/删除/)[0]);
    await screen.findByText('确定删除该检测站吗？');
    const popover = screen.getByText('确定删除该检测站吗？').closest('.ant-popover');
    await userEvent.click(within(popover).getByRole('button', { name: /删.*除/ }));
    await waitFor(() => expect(request.delete).toHaveBeenCalledWith('/stations/1'));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('删除异常'));
  });
});
