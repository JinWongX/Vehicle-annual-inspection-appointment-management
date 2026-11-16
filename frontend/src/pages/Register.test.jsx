import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Register from './Register';
import { message } from 'antd';

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    Link: ({ children }) => <span>{children}</span>,
  };
});

vi.mock('../utils/request', () => ({ default: {} }));

vi.mock('antd', async () => {
  const MockForm = ({ onFinish, children, ...props }) => {
    const handleSubmit = (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      const values = {};
      formData.forEach((value, key) => {
        values[key] = value;
      });
      if (onFinish) {
        onFinish(values);
      }
    };
    return (
      <form {...props} onSubmit={handleSubmit}>
        {children}
      </form>
    );
  };

  MockForm.Item = ({ name, label, rules, children }) => {
    const required = rules?.some((rule) => rule.required);
    const child = React.isValidElement(children)
      ? React.cloneElement(children, { id: name, name, required })
      : children;
    return (
      <div>
        {label && <label htmlFor={name}>{label}</label>}
        {child}
      </div>
    );
  };

  const Input = (props) => <input {...props} />;
  Input.Password = (props) => <input {...props} type="password" />;

  const Button = ({ children, htmlType = 'button', loading, block, ...props }) => (
    <button type={htmlType} {...props}>
      {children}
    </button>
  );

  const Card = ({ children }) => <div>{children}</div>;
  const Typography = { Title: ({ children }) => <h1>{children}</h1> };
  const messageMock = {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  };

  return { Form: MockForm, Input, Button, Card, Typography, message: messageMock };
});

import { useAuth } from '../context/AuthContext';

describe('Register', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders register form and submits', async () => {
    const registerMock = vi.fn().mockResolvedValue({});
    useAuth.mockReturnValue({ registerAndLogin: registerMock });

    render(<Register />);
    await userEvent.type(screen.getByLabelText(/用户名/), 'bob');
    await userEvent.type(screen.getByLabelText(/密码/), 'Password123');
    await userEvent.type(screen.getByLabelText(/手机号/), '13800000000');
    await userEvent.type(screen.getByLabelText(/真实姓名/), 'Bob');
    await userEvent.click(screen.getByRole('button', { name: /注.*册/ }));

    await waitFor(() =>
      expect(registerMock).toHaveBeenCalledWith(
        expect.objectContaining({ username: 'bob', password: 'Password123' })
      )
    );
  });

  it('calls message.error when register fails', async () => {
    const registerMock = vi.fn().mockRejectedValue({
      response: { data: { detail: '用户名已存在' } },
    });
    useAuth.mockReturnValue({ registerAndLogin: registerMock });

    render(<Register />);
    await userEvent.type(screen.getByLabelText(/用户名/), 'bob');
    await userEvent.type(screen.getByLabelText(/密码/), 'Password123');
    await userEvent.type(screen.getByLabelText(/手机号/), '13800000000');
    await userEvent.type(screen.getByLabelText(/真实姓名/), 'Bob');
    await userEvent.click(screen.getByRole('button', { name: /注.*册/ }));

    await waitFor(() => expect(message.error).toHaveBeenCalledWith('用户名已存在'));
  });

  it('renders readable message for FastAPI 422 array detail', async () => {
    const registerMock = vi.fn().mockRejectedValue({
      response: {
        data: {
          detail: [{ msg: 'String should have at least 8 characters' }, { msg: 'Value error' }],
        },
      },
    });
    useAuth.mockReturnValue({ registerAndLogin: registerMock });

    render(<Register />);
    await userEvent.type(screen.getByLabelText(/用户名/), 'bob');
    await userEvent.type(screen.getByLabelText(/密码/), 'short');
    await userEvent.type(screen.getByLabelText(/手机号/), '13800000000');
    await userEvent.type(screen.getByLabelText(/真实姓名/), 'Bob');
    await userEvent.click(screen.getByRole('button', { name: /注.*册/ }));

    await waitFor(() =>
      expect(message.error).toHaveBeenCalledWith(
        'String should have at least 8 characters；Value error'
      )
    );
  });
});
