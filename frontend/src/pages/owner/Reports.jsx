import { useEffect, useState } from 'react';
import { Card, Table, Tag, Empty, List } from 'antd';
import request from '../../utils/request';

const resultMap = {
  pass: { text: '合格', color: 'green' },
  fail: { text: '不合格', color: 'red' },
  retest: { text: '需复检', color: 'orange' },
};

export default function Reports() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    request.get('/reports')
      .then((res) => setData(res.data || []))
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    { title: '车牌', dataIndex: ['appointment', 'vehicle', 'plate_number'], key: 'plate' },
    { title: '检测站', dataIndex: ['appointment', 'station', 'name'], key: 'station' },
    { title: '预约日期', dataIndex: ['appointment', 'appointment_date'], key: 'date' },
    {
      title: '检测结果',
      dataIndex: 'result',
      key: 'result',
      render: (v) => <Tag color={resultMap[v]?.color}>{resultMap[v]?.text || v}</Tag>,
    },
    { title: '贴纸码', dataIndex: 'sticker_code', key: 'sticker_code' },
  ];

  return (
    <Card title="检测报告" loading={loading}>
      {data.length === 0 && <Empty description="暂无检测报告" />}
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        expandable={{
          expandedRowRender: (record) => (
            <div>
              <p><strong>总体备注：</strong>{record.overall_comment || '-'}</p>
              {record.items?.length > 0 && (
                <List
                  size="small"
                  bordered
                  dataSource={record.items}
                  renderItem={(item) => (
                    <List.Item>
                      {item.item_name} — <Tag color={resultMap[item.result]?.color}>{resultMap[item.result]?.text || item.result}</Tag>
                      {item.comment && <span style={{ marginLeft: 8 }}>备注：{item.comment}</span>}
                    </List.Item>
                  )}
                />
              )}
            </div>
          ),
        }}
      />
    </Card>
  );
}
