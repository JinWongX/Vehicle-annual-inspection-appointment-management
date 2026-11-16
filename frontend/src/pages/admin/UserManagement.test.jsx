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
  MockForm.useWatch = vi.fn(() => undefined);

  const MockModal = ({ children, title, open, onOk, onCancel }) => {
    if (!open) return null;
    return React.createElement('div', { className: 'ant-modal' },
      React.createElement('div', { className: 'ant-modal-title' }, title),
      React.createElement('div', { className: 'ant-modal-body' }, children),
      React.createElement('button', { onClick: onOk, type: 'button' }, 'OK'),
      React.createElement('button', { onClick: onCancel, type: 'button' }, 'Cancel')
    );
  };
  const MockPopconfirm = ({ children, onConfirm, title }) =>
    React.createElement('span', { onClick: onConfirm, 'aria-label': `确认:${title}` }, children);
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
    Popconfirm: MockPopconfirm,
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

const UserManagement = (await import('./UserManagement')).default;
import request from '../../utils/request';
import { Form, message } from 'antd';

describe('UserManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Form.useWatch.mockReturnValue(undefined);
    request.get.mockImplementation((url) => {
      if (url === '/users') {
        return Promise.resolve({ data: [{ id: 1, username: 'admin_user', role: 'admin', real_name: 'A', phone: '138', station_id: null }] });
      }
      if (url === '/stations') {
        return Promise.resolve({ data: [{ id: 10, name: '站A' }] });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it('Form mock is active', () => {
    const [form] = Form.useForm();
    expect(form).toBe(mockForm);
  });

  it('creates an owner user', async () => {
    mockForm.validateFields.mockResolvedValue({
      username: 'new_owner', password: 'Password123', role: 'owner', real_name: 'N', phone: '139',
    });
    request.post.mockResolvedValue({});

    render(<UserManagement />);
    await waitFor(() => expect(screen.getByText('admin_user')).toBeInTheDocument());
    await userEvent.click(screen.getByText(/新增用户/));
    await waitFor(() => expect(screen.getByText('新增用户', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/users', expect.objectContaining({
      username: 'new_owner',
      role: 'owner',
    })));
  });

  it('creates a station user with station_id', async () => {
    Form.useWatch.mockReturnValue('station');
    mockForm.validateFields.mockResolvedValue({
      username: 'new_station',
      password: 'Password123',
      role: 'station',
      real_name: 'S',
      phone: '139',
      station_id: 10,
    });
    request.post.mockResolvedValue({});

    render(<UserManagement />);
    await waitFor(() => expect(screen.getByText('admin_user')).toBeInTheDocument());
    await userEvent.click(screen.getByText(/新增用户/));
    await waitFor(() => expect(screen.getByText('新增用户', { selector: '.ant-modal-title' })).toBeInTheDocument());
    expect(screen.getByLabelText('归属检测站')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(request.post).toHaveBeenCalledWith('/users', expect.objectContaining({
      username: 'new_station',
      role: 'station',
      station_id: 10,
    })));
  });

  it('shows error when creating user fails', async () => {
    mockForm.validateFields.mockResolvedValue({
      username: 'new_owner', password: 'Password123', role: 'owner', real_name: 'N', phone: '139',
    });
    request.post.mockRejectedValue({ response: { data: { detail: '创建异常' } } });

    render(<UserManagement />);
    await waitFor(() => expect(screen.getByText('admin_user')).toBeInTheDocument());
    await userEvent.click(screen.getByText(/新增用户/));
    await waitFor(() => expect(screen.getByText('新增用户', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('创建异常'));
  });

  it('edits an existing user', async () => {
    Form.useWatch.mockReturnValue('owner');
    request.put.mockResolvedValue({});
    mockForm.validateFields.mockResolvedValue({
      role: 'owner', real_name: '编辑后的姓名', phone: '139',
    });

    render(<UserManagement />);
    await waitFor(() => expect(screen.getByText('admin_user')).toBeInTheDocument());
    await userEvent.click(screen.getByText('编辑'));
    await waitFor(() => expect(screen.getByText('编辑用户', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(request.put).toHaveBeenCalledWith('/users/1', expect.objectContaining({
      role: 'owner',
      real_name: '编辑后的姓名',
    })));
    await waitFor(() => expect(message.success).toHaveBeenCalledWith('更新成功'));
  });

  it('shows error when updating fails', async () => {
    Form.useWatch.mockReturnValue('owner');
    request.put.mockRejectedValue({ response: { data: { detail: '更新异常' } } });
    mockForm.validateFields.mockResolvedValue({ role: 'owner', real_name: 'X', phone: '139' });

    render(<UserManagement />);
    await waitFor(() => expect(screen.getByText('admin_user')).toBeInTheDocument());
    await userEvent.click(screen.getByText('编辑'));
    await waitFor(() => expect(screen.getByText('编辑用户', { selector: '.ant-modal-title' })).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^OK$/i }));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('更新异常'));
  });

  it('deletes a user', async () => {
    request.delete.mockResolvedValue({});
    request.get.mockImplementation((url) => {
      if (url === '/stations') return Promise.resolve({ data: [{ id: 10, name: '站A' }] });
      return Promise.resolve({ data: [{ id: 1, username: 'admin_user', role: 'admin', real_name: 'A', phone: '138', station_id: null }] });
    });

    render(<UserManagement />);
    await waitFor(() => expect(screen.getByText('admin_user')).toBeInTheDocument());
    await userEvent.click(screen.getByText('删除'));
    await waitFor(() => expect(request.delete).toHaveBeenCalledWith('/users/1'));
    await waitFor(() => expect(message.success).toHaveBeenCalledWith('删除成功'));
  });

  it('shows error when delete fails', async () => {
    request.delete.mockRejectedValue({ response: { data: { detail: '删除异常' } } });

    render(<UserManagement />);
    await waitFor(() => expect(screen.getByText('admin_user')).toBeInTheDocument());
    await userEvent.click(screen.getByText('删除'));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('删除异常'));
  });
});
