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



