import { useEffect, useState } from 'react';
import { Card, Form, Select, DatePicker, Button, message } from 'antd';
import dayjs from 'dayjs';
import request from '../../utils/request';

const FORMATS = [
  { value: 'excel', label: 'Excel' },
  { value: 'csv', label: 'CSV' },
];

export default function DataExport() {
  const [form] = Form.useForm();
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    request.get('/stations')
      .then((res) => setStations(res.data || []))
      .catch((err) => message.error(err.response?.data?.detail || '加载检测站失败'));
  }, []);

  const handleExport = async (values) => {
    setLoading(true);
    try {
      const res = await request.get('/reports/export', {
        params: {
          format: values.format,
          station_id: values.station_id,
          start_date: values.start_date.format('YYYY-MM-DD'),
          end_date: values.end_date.format('YYYY-MM-DD'),
        },
        responseType: 'blob',
      });
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const ext = values.format === 'csv' ? 'csv' : 'xlsx';
      link.download = `reports_${dayjs().format('YYYYMMDD_HHmmss')}.${ext}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (err) {
      message.error(err.response?.data?.detail || '导出失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="数据导出">
      <Form form={form} onFinish={handleExport} layout="vertical">
        <Form.Item name="format" label="导出格式" initialValue="excel" rules={[{ required: true }]}>
          <Select options={FORMATS} />
        </Form.Item>
        <Form.Item name="station_id" label="检测站（可选）">
          <Select
            allowClear
            placeholder="全部检测站"
            options={stations.map((s) => ({ value: s.id, label: s.name }))}
          />
        </Form.Item>
        <Form.Item name="start_date" label="开始日期" initialValue={dayjs().subtract(30, 'day')} rules={[{ required: true }]}>
          <DatePicker format="YYYY-MM-DD" style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          name="end_date"
          label="结束日期"
          initialValue={dayjs()}
          dependencies={['start_date']}
          rules={[
            { required: true },
            ({ getFieldValue }) => ({
              validator(_, value) {
                const start = getFieldValue('start_date');
                if (!value || !start || !value.isBefore(start)) return Promise.resolve();
                return Promise.reject(new Error('结束日期不能早于开始日期'));
              },
            }),
          ]}
        >
          <DatePicker format="YYYY-MM-DD" style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>导出</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
