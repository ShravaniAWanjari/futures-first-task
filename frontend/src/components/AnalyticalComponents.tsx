import React from 'react';

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

interface ChartProps {
  data?: { label: string; value: number }[];
  labels?: string[];
  values?: number[];
  title?: string;
}

export const SimpleBarChart: React.FC<ChartProps> = ({ data, labels, values, title }) => {
  const chartData = data || (labels && values ? labels.map((l, i) => ({ label: l, value: values[i] })) : []);
  if (!chartData || chartData.length === 0) return null;
  const maxValue = Math.max(...chartData.map(d => d.value));

  return (
    <div style={{
      padding: '24px', background: 'var(--color-surface, #fff)', borderRadius: '20px',
      border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 2px 24px rgba(0,0,0,0.06)', margin: '20px 0'
    }}>
      {title && <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</h3>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {chartData.map((item, i) => {
          const width = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
          return (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                <span style={{ fontWeight: 500 }}>{item.label}</span>
                <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{item.value.toLocaleString()}</span>
              </div>
              <div style={{ height: '8px', width: '100%', background: 'var(--color-primary-soft)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${width}%`, background: 'var(--color-primary)', borderRadius: '4px', transition: 'width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)' }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const SimpleLineChart: React.FC<ChartProps> = ({ data, labels, values, title }) => {
  const chartData = data || (labels && values ? labels.map((l, i) => ({ label: l, value: values[i] })) : []);
  if (!chartData || chartData.length < 2) return <SimpleBarChart data={chartData} title={title} />;
  
  const maxValue = Math.max(...chartData.map(d => d.value)) || 1;
  const minValue = Math.min(...chartData.map(d => d.value)) || 0;
  const range = maxValue - minValue || 1;
  
  const width = 500;
  const height = 150;
  const padding = 20;
  
  const points = chartData.map((d, i) => {
    const x = padding + (i * (width - 2 * padding) / (chartData.length - 1));
    const y = height - padding - ((d.value - minValue) * (height - 2 * padding) / range);
    return `${x},${y}`;
  }).join(' ');

  return (
    <div style={{
      padding: '24px', background: 'var(--color-surface, #fff)', borderRadius: '20px',
      border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 2px 24px rgba(0,0,0,0.06)', margin: '20px 0'
    }}>
      {title && <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</h3>}
      <div style={{ position: 'relative', width: '100%', height }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '100%', overflow: 'visible' }}>
          <polyline fill="none" stroke="var(--color-primary-soft)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" points={points} />
          {chartData.map((d, i) => {
            const x = padding + (i * (width - 2 * padding) / (chartData.length - 1));
            const y = height - padding - ((d.value - minValue) * (height - 2 * padding) / range);
            return (
              <g key={i}>
                <circle cx={x} cy={y} r="4" fill="var(--color-primary)" stroke="#fff" strokeWidth="2" />
                <text x={x} y={height - 2} fontSize="10" textAnchor="middle" fill="var(--color-text-muted)">{d.label}</text>
                <text x={x} y={y - 8} fontSize="10" textAnchor="middle" fontWeight="600" fill="var(--color-text)">{_fmt(d.value)}</text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};

export const SimplePieChart: React.FC<ChartProps> = ({ data, labels, values, title }) => {
  const chartData = data || (labels && values ? labels.map((l, i) => ({ label: l, value: values[i] })) : []);
  if (!chartData || chartData.length === 0) return null;
  
  const total = chartData.reduce((sum, d) => sum + d.value, 0);
  let cumulativePercent = 0;
  
  const colors = [
    'var(--color-primary)', 
    '#0f766e', '#1d4ed8', '#b45309', '#be123c', '#475569', '#0f172a'
  ];

  const slices = chartData.map((d, i) => {
    const percent = (d.value / total) * 100;
    const start = cumulativePercent;
    cumulativePercent += percent;
    return { label: d.label, value: d.value, percent, start, color: colors[i % colors.length] };
  });

  const gradient = slices.map(s => `${s.color} ${s.start}% ${s.start + s.percent}%`).join(', ');

  return (
    <div style={{
      padding: '24px', background: 'var(--color-surface, #fff)', borderRadius: '20px',
      border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 2px 24px rgba(0,0,0,0.06)', margin: '20px 0',
      display: 'flex', flexDirection: 'column', gap: 20
    }}>
      {title && <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</h3>}
      <div style={{ display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
        <div style={{
          width: 120, height: 120, borderRadius: '50%',
          background: `conic-gradient(${gradient})`,
          boxShadow: 'inset 0 0 0 10px rgba(255,255,255,0.2)'
        }} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {slices.map((s, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: s.color }} />
                <span style={{ color: 'var(--color-text-secondary)' }}>{s.label}</span>
              </div>
              <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{Math.round(s.percent)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Helper for formatting large numbers used by charts
const _fmt = (n: number) => {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
};


