import { Table } from "antd";
import type { ColumnsType } from "antd/es/table";

type OperationalTableProps<T extends object> = {
  columns: ColumnsType<T>;
  data: T[];
  rowKey: keyof T | ((row: T) => string);
};

export const OperationalTable = <T extends object>({
  columns,
  data,
  rowKey,
}: OperationalTableProps<T>) => (
  <Table
    size="middle"
    columns={columns}
    dataSource={data}
    rowKey={rowKey}
    pagination={false}
    scroll={{ x: true }}
  />
);
