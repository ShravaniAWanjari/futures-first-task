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
        borderRadius: '12px', 
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
      }}
    >
      <table style={{ 
        width: '100%', 
        borderCollapse: 'collapse', 
        fontSize: '13px', 
        textAlign: 'left' 
      }}>
        <thead style={{ background: 'var(--color-surface-raised)' }}>
          <tr>
            {columns.map((col, i) => (
              <th key={i} style={{ 
                padding: '14px 20px', 
                fontWeight: 700, 
                color: 'var(--color-text)', 
                borderBottom: '2px solid var(--color-border)',
                textTransform: 'uppercase',
                letterSpacing: '0.03em'
              }}>
                {col.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} style={{ borderBottom: '1px solid var(--color-border-subtle)', transition: 'background 0.1s' }} onMouseEnter={e => e.currentTarget.style.background = 'var(--color-bg)'} onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              {columns.map((col, ci) => (
                <td key={ci} style={{ padding: '12px 20px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
                  {typeof row[col] === 'number' ? row[col].toLocaleString() : row[col]}
                </td>
              ))}
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

export const DataChart: React.FC<ChartProps> = ({ type, labels, values, label }) => {
  if (!values || values.length === 0) return null;

  const max = Math.max(...values, 1);

  if (type === 'bar') {
    return (
      <div 
        id="analytical-chart-bar"
        style={{ 
          margin: '24px 0', 
          padding: '24px', 
          background: 'var(--color-surface)', 
          borderRadius: '16px', 
          border: '1px solid var(--color-border)',
          boxShadow: '0 4px 20px rgba(0,0,0,0.04)'
        }}
      >
        <h5 style={{ margin: '0 0 20px 0', fontSize: '14px', fontWeight: 700, color: 'var(--color-text)', letterSpacing: '-0.01em' }}>
          {label || 'Comparative Performance Metrics'}
        </h5>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {labels.map((l, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontWeight: 600 }}>{l}</span>
                <span style={{ fontWeight: 700, color: 'var(--color-text)' }}>{values[i].toLocaleString()}</span>
              </div>
              <div style={{ width: '100%', height: '10px', background: 'var(--color-bg)', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{ 
                  width: `${(values[i] / max) * 100}%`, 
                  height: '100%', 
                  background: 'linear-gradient(90deg, #202020, #404040)',
                  borderRadius: '5px',
                  transition: 'width 1s cubic-bezier(0.34, 1.56, 0.64, 1)'
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Fallback or simple visualization
  return <DataTable columns={['Category', 'Value']} rows={labels.map((l, i) => ({'Category': l, 'Value': values[i]}))} />;
};

interface KPICardProps {
  label: string;
  value: string | number;
  context?: string;
}

export const KPICard: React.FC<KPICardProps> = ({ label, value, context }) => {
  return (
    <div style={{ 
      padding: '20px', 
      background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02))', 
      borderRadius: '12px', 
      border: '1px solid var(--color-border)',
      minWidth: '200px',
      flex: '1'
    }}>
      <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </div>
      <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-text)', marginBottom: '4px' }}>
        {value}
      </div>
      {context && (
        <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', opacity: 0.8 }}>
          {context}
        </div>
      )}
    </div>
  );
};
