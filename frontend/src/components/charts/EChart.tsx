import { ExpandOutlined } from "@ant-design/icons";
import { Modal } from "antd";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import { useEffect, useRef, useState } from "react";

type EChartProps = {
  option: EChartsOption;
  ariaLabel: string;
  className?: string;
  expandable?: boolean;
  expandedTitle?: string;
  expandedAriaLabel?: string;
  expandedOption?: EChartsOption;
  modalWidth?: number;
};

type ChartCanvasProps = {
  option: EChartsOption;
  ariaLabel: string;
  className?: string;
};

const ChartCanvas = ({ option, ariaLabel, className }: ChartCanvasProps) => {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!elementRef.current) {
      return undefined;
    }

    const chart = echarts.init(elementRef.current);
    chartRef.current = chart;

    const resize = () => chart.resize();
    const resizeObserver =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(() => resize())
        : null;
    resizeObserver?.observe(elementRef.current);
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      resizeObserver?.disconnect();
      chartRef.current = null;
      chart.dispose();
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
    chartRef.current?.resize();
  }, [option]);

  return (
    <div
      ref={elementRef}
      className={className ? `sg-chart ${className}` : "sg-chart"}
      role="img"
      aria-label={ariaLabel}
    />
  );
};

export const EChart = ({
  option,
  ariaLabel,
  className,
  expandable = false,
  expandedTitle,
  expandedAriaLabel,
  expandedOption,
  modalWidth = 1080,
}: EChartProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!expandable) {
    return <ChartCanvas option={option} ariaLabel={ariaLabel} className={className} />;
  }

  const openExpanded = () => setIsExpanded(true);
  const closeExpanded = () => setIsExpanded(false);
  const modalTitle = expandedTitle ?? ariaLabel;
  const expandLabel = `Expand ${modalTitle}`;

  return (
    <>
      <div
        className="sg-chart-frame is-expandable"
        role="button"
        tabIndex={0}
        aria-label={expandLabel}
        onClick={openExpanded}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openExpanded();
          }
        }}
      >
        <ChartCanvas option={option} ariaLabel={ariaLabel} className={className} />
        <span className="sg-chart-expand-hint" aria-hidden="true">
          <ExpandOutlined />
          Expand
        </span>
      </div>
      <Modal
        className="sg-chart-modal"
        footer={null}
        onCancel={closeExpanded}
        open={isExpanded}
        title={modalTitle}
        width={modalWidth}
      >
        <ChartCanvas
          option={expandedOption ?? option}
          ariaLabel={expandedAriaLabel ?? `${ariaLabel} enlarged`}
          className="sg-chart-expanded"
        />
      </Modal>
    </>
  );
};
