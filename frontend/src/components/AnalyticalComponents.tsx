import React, { useEffect, useRef } from 'react';

/**
 * Analytical Presentation Pass
 * Management-grade visualization components for structured data.
 */

interface TableProps {
  columns: string[];
  rows: any[];
}

export const DataTable: React.FC<TableProps> = ({ columns, rows }) => {
  if (!rows || rows.length === 0) return null;

  return (
    <div 
      id="analytical-table-container"
      style={{ 
        margin: '24px 0', 
        overflowX: 'auto', 
        borderRadius: '20px', 
        border: '1px solid rgba(0,0,0,0.06)',
        background: 'var(--color-surface, #fff)',
        boxShadow: '0 2px 24px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04)',
      }}
    >
      <table style={{ 
        width: '100%', 
        borderCollapse: 'collapse',
        fontSize: '13px', 
        textAlign: 'left',
        minWidth: '400px',
      }}>
        <thead>
          <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
            {columns.map((col, i) => (
              <th key={i} style={{ 
                padding: '14px 20px', 
                fontWeight: 600, 
                color: 'var(--color-text-muted, #888)', 
                textTransform: 'uppercase',
                letterSpacing: '0.07em',
                fontSize: '10.5px',
                whiteSpace: 'nowrap',
              }}>
                {col.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr 
              key={ri} 
              style={{ 
                borderBottom: ri < rows.length - 1 ? '1px solid rgba(0,0,0,0.04)' : 'none',
                transition: 'background 0.15s',
              }} 
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,0,0,0.015)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              {columns.map((col, ci) => {
                const val = row[col];
                const isFirst = ci === 0;
                const htmlVal = typeof val === 'number' 
                  ? val.toLocaleString() 
                  : String(val ?? 'N/A').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                return (
                  <td 
                    key={ci} 
                    style={{ 
                      padding: '13px 20px', 
                      color: isFirst ? 'var(--color-text, #111)' : 'var(--color-text-secondary, #555)', 
                      fontWeight: isFirst ? 600 : 400,
                      fontSize: '13px',
                      lineHeight: 1.5,
                    }}
                    dangerouslySetInnerHTML={{ __html: htmlVal }}
                  />
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

interface ChartProps {
  type: 'bar' | 'line' | 'pie';
  labels: string[];
  values: number[];
  label?: string;
}

// Color palette for bars — cycling through accent tones
const BAR_COLORS = [
  'rgba(59, 130, 246, 0.85)',   // blue
  'rgba(16, 185, 129, 0.85)',   // emerald
  'rgba(245, 158, 11, 0.85)',   // amber
  'rgba(239, 68, 68, 0.85)',    // red
  'rgba(139, 92, 246, 0.85)',   // violet
  'rgba(236, 72, 153, 0.85)',   // pink
  'rgba(14, 165, 233, 0.85)',   // sky
  'rgba(168, 85, 247, 0.85)',   // purple
];

export const DataChart: React.FC<ChartProps> = ({ type, labels, values, label }) => {
  if (!values || values.length === 0) return null;

  const max = Math.max(...values, 1);

  const formatValue = (v: number) => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
    if (v % 1 !== 0) return v.toFixed(2);
    return v.toLocaleString();
  };

  return (
    <div 
      id="analytical-chart-bar"
      style={{ 
        margin: '24px 0',
        padding: '24px 28px 20px',
        background: 'var(--color-surface, #fff)',
        borderRadius: '20px', 
        border: '1px solid rgba(0,0,0,0.06)',
        boxShadow: '0 2px 24px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04)',
      }}
    >
      {/* Chart header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'baseline', 
        marginBottom: 24 
      }}>
        <h5 style={{ 
          margin: 0, 
          fontSize: '13px', 
          fontWeight: 600, 
          color: 'var(--color-text, #111)', 
          letterSpacing: '-0.01em' 
        }}>
          {label || 'Performance Breakdown'}
        </h5>
        <span style={{ 
          fontSize: '10px', 
          fontWeight: 600, 
          color: 'var(--color-text-muted, #888)', 
          textTransform: 'uppercase', 
          letterSpacing: '0.07em' 
        }}>
          {type === 'bar' ? 'Bar Chart' : type === 'line' ? 'Trend' : 'Distribution'}
        </span>
      </div>

      {/* Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {labels.map((lbl, i) => {
          const pct = (values[i] / max) * 100;
          const color = BAR_COLORS[i % BAR_COLORS.length];
          return (
            <div key={i}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: 6,
                fontSize: '12.5px',
              }}>
                <span style={{ 
                  color: 'var(--color-text-secondary, #555)', 
                  fontWeight: 500,
                  maxWidth: '65%',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {lbl}
                </span>
                <span style={{ 
                  fontWeight: 700, 
                  color: 'var(--color-text, #111)',
                  fontSize: '12.5px',
                  letterSpacing: '-0.01em',
                }}>
                  {formatValue(values[i])}
                </span>
              </div>
              {/* Bar track */}
              <div style={{ 
                width: '100%', 
                height: '8px', 
                background: 'rgba(0,0,0,0.05)', 
                borderRadius: '4px', 
                overflow: 'hidden' 
              }}>
                <div 
                  style={{ 
                    width: `${pct}%`, 
                    height: '100%', 
                    background: color,
                    borderRadius: '4px',
                    transition: 'width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  }} 
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface KPICardProps {
  label: string;
  value: string | number;
  context?: string;
}

export const KPICard: React.FC<KPICardProps> = ({ label, value, context }) => {
  return (
    <div style={{ 
      padding: '20px 24px', 
      background: 'var(--color-surface, #fff)',
      borderRadius: '16px', 
      border: '1px solid rgba(0,0,0,0.06)',
      boxShadow: '0 2px 12px rgba(0,0,0,0.05)',
      display: 'inline-flex',
      flexDirection: 'column',
      gap: 6,
    }}>
      <div style={{ 
        fontSize: '11px', 
        fontWeight: 600, 
        color: 'var(--color-text-muted, #888)', 
        textTransform: 'uppercase', 
        letterSpacing: '0.07em' 
      }}>
        {label}
      </div>
      <div style={{ 
        fontSize: '32px', 
        fontWeight: 700, 
        color: 'var(--color-text, #111)', 
        letterSpacing: '-0.03em',
        lineHeight: 1.1,
      }}>
        {value}
      </div>
      {context && (
        <div style={{ 
          fontSize: '12px', 
          color: 'var(--color-text-secondary, #666)',
          marginTop: 2,
        }}>
          {context}
        </div>
      )}
    </div>
  );
};

/**
 * InlineChart — auto-generates a bar chart from a markdown table's
 * first numeric column, triggered directly from the formatResponse pipeline.
 */
interface InlineChartProps {
  columns: string[];
  rows: any[];
  label?: string;
}

export const InlineChart: React.FC<InlineChartProps> = ({ columns, rows, label }) => {
  if (!rows || rows.length === 0 || columns.length < 2) return null;

  // Find the first column with numeric values
  const labelCol = columns[0];
  const numericCol = columns.slice(1).find(col => {
    return rows.some(r => {
      const v = String(r[col] ?? '').replace(/[$,%x]/g, '').trim();
      return !isNaN(parseFloat(v)) && v !== '';
    });
  });

  if (!numericCol) return null;

  const parseVal = (v: any): number => {
    const s = String(v ?? '').replace(/[$,%x,]/g, '').trim();
    if (s.toUpperCase().endsWith('M')) return parseFloat(s) * 1_000_000;
    if (s.toUpperCase().endsWith('K')) return parseFloat(s) * 1_000;
    return parseFloat(s) || 0;
  };

  const chartData = rows
    .map(r => ({ lbl: String(r[labelCol] ?? ''), val: parseVal(r[numericCol]) }))
    .filter(d => d.lbl && d.val > 0);

  if (chartData.length < 2) return null;

  return (
    <DataChart
      type="bar"
      labels={chartData.map(d => d.lbl)}
      values={chartData.map(d => d.val)}
      label={label || numericCol}
    />
  );
};
