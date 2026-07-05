import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
};

export const EmptyState = ({
  title,
  description,
  action,
  className,
}: EmptyStateProps) => (
  <div className={`sg-empty-state${className ? ` ${className}` : ""}`}>
    <div className="sg-empty-state-icon" aria-hidden="true" />
    <strong>{title}</strong>
    {description ? <p>{description}</p> : null}
    {action ? <div className="sg-empty-state-action">{action}</div> : null}
  </div>
);
