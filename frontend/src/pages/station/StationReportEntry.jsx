import { useEffect, useState } from 'react';
import { Card, Form, Select, Button, Input, List, Space, Tag, message } from 'antd';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import request from '../../utils/request';

const RESULT_OPTIONS = [
  { value: 'pass', label: '合格' },
  { value: 'fail', label: '不合格' },
  { value: 'retest', label: '需复检' },
];

const ITEM_RESULT_OPTIONS = [
  { value: 'pass', label: '通过' },
  { value: 'fail', label: '不通过' },
  { value: 'retest', label: '需复检' },
];

export default function StationReportEntry() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await request.get('/appointments');
      setAppointments(res.data.filter((a) => a.status === 'checking') || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      await request.post('/reports', {
        appointment_id: values.appointment_id,
        result: values.result,
        overall_comment: values.overall_comment,
        items: values.items || [],
      });
      message.success('录入成功');
      form.resetFields();
      fetch();
    } catch (err) {
      message.error(err.response?.data?.detail || '录入失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card title="结果录入" loading={loading}>
      <Form form={form} onFinish={handleSubmit} layout="vertical">
        <Form.Item name="appointment_id" label="选择待录入预约" rules={[{ required: true, message: '请选择预约' }]}>
          <Select
            placeholder="请选择"
            options={appointments.map((a) => ({
              value: a.id,
              label: `${a.vehicle?.plate_number} — ${a.station?.name} — ${a.appointment_date} ${a.time_slot}`,
            }))}
          />
        </Form.Item>
        <Form.Item name="result" label="检测结果" rules={[{ required: true, message: '请选择检测结果' }]}>
          <Select options={RESULT_OPTIONS} placeholder="请选择" />
        </Form.Item>
        <Form.Item name="overall_comment" label="总体备注" rules={[{ max: 1000, message: '总体备注不能超过 1000 字' }]}>
          <Input.TextArea rows={2} />
        </Form.Item>
        <Form.Item label="检测项目">
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} align="baseline">
                    <Form.Item
                      {...restField}
                      name={[name, 'item_name']}
                      rules={[{ required: true, message: '请输入项目名' }]}
                    >
                      <Input placeholder="项目名称" />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'result']}
                      rules={[{ required: true, message: '请选择结果' }]}
                    >
                      <Select options={ITEM_RESULT_OPTIONS} placeholder="结果" style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'comment']}
                      rules={[{ max: 500, message: '备注不能超过 500 字' }]}
                    >
                      <Input placeholder="备注" />
                    </Form.Item>
                    <MinusCircleOutlined onClick={() => remove(name)} />
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add()} icon={<PlusOutlined />} block>
                  添加检测项目
                </Button>
              </>
            )}
          </Form.List>
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting}>提交结果</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
