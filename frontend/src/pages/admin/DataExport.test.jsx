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
    },
  };
});

vi.mock('../../utils/request', () => ({
  default: {
    get: vi.fn(),
  },
}));

const DataExport = (await import('./DataExport')).default;
import request from '../../utils/request';
import { message } from 'antd';

describe('DataExport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockImplementation((url, config) => {
      if (url === '/stations') {
        return Promise.resolve({ data: [{ id: 1, name: '站A' }] });
      }
      return Promise.resolve({ data: new Blob(['test']) });
    });
  });

  it('loads stations and exports data', async () => {
    const testDate = { format: () => '2026-09-07' };
    mockForm.validateFields.mockResolvedValue({
      format: 'excel',
      station_id: undefined,
      start_date: testDate,
      end_date: testDate,
    });
    render(<DataExport />);
    await waitFor(() => expect(screen.getByText(/导出格式/)).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /导.*出/ }));
    await waitFor(() => expect(request.get).toHaveBeenCalledWith('/reports/export', expect.any(Object)));
  });

  it('handles stations loading failure', async () => {
    request.get.mockImplementation((url) => {
      if (url === '/stations') {
        return Promise.reject({ response: { data: { detail: '加载失败' } } });
      }
      return Promise.resolve({ data: new Blob(['test']) });
    });
    render(<DataExport />);
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('加载失败'));
  });

  it('exports xlsx format by default', async () => {
    const testDate = { format: () => '2026-09-07' };
    const linkMock = { href: '', download: '', click: vi.fn(), remove: vi.fn() };
    const originalCreateElement = document.createElement.bind(document);
    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'a') return linkMock;
      return originalCreateElement(tag);
    });
    mockForm.validateFields.mockResolvedValue({
      format: 'excel',
      station_id: undefined,
      start_date: testDate,
      end_date: testDate,
    });

    render(<DataExport />);
    await waitFor(() => expect(screen.getByText(/导出格式/)).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /导.*出/ }));
    await waitFor(() => expect(request.get).toHaveBeenCalledWith('/reports/export', expect.any(Object)));
    expect(linkMock.download).toMatch(/\.xlsx$/);

    createElementSpy.mockRestore();
  });

  it('exports csv format', async () => {
    const testDate = { format: () => '2026-09-07' };
    const linkMock = { href: '', download: '', click: vi.fn(), remove: vi.fn() };
    const originalCreateElement = document.createElement.bind(document);
    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'a') return linkMock;
      return originalCreateElement(tag);
    });
    mockForm.validateFields.mockResolvedValue({
      format: 'csv',
      station_id: undefined,
      start_date: testDate,
      end_date: testDate,
    });

    render(<DataExport />);
    await waitFor(() => expect(screen.getByText(/导出格式/)).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /导.*出/ }));
    await waitFor(() => expect(request.get).toHaveBeenCalledWith('/reports/export', expect.objectContaining({
      params: expect.objectContaining({ format: 'csv' }),
    })));
    expect(linkMock.download).toMatch(/\.csv$/);

    createElementSpy.mockRestore();
  });
});
