import { Card, Typography } from "antd";

type PlaceholderPageProps = {
  title: string;
  purpose: string;
};

export const PlaceholderPage = ({ title, purpose }: PlaceholderPageProps) => (
  <Card className="sg-placeholder">
    <Typography.Title level={2}>{title}</Typography.Title>
    <Typography.Paragraph>{purpose}</Typography.Paragraph>
    <Typography.Paragraph type="secondary">
      This module is not implemented in the current React foundation sprint. It will
      use FastAPI results only and will not show fabricated operational values.
    </Typography.Paragraph>
  </Card>
);
