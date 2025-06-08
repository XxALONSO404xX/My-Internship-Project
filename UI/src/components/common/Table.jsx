import React from 'react';

/**
 * Table component for displaying tabular data
 * props:
 * - columns: [{ Header: string, accessor: string, Cell?: function }]
 * - data: array of objects
 */
const Table = ({ columns, data, className = '' }) => (
  <div className={`overflow-x-auto ${className}`}>
    <table className="min-w-full bg-white dark:bg-gray-800">
      <thead>
        <tr>
          {columns.map(col => (
            <th
              key={col.accessor}
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              {col.Header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, idx) => (
          <tr key={idx} className="border-t border-gray-200 dark:border-gray-700">
            {columns.map(col => (
              <td
                key={col.accessor}
                className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100"
              >
                {col.Cell ? col.Cell(row) : row[col.accessor]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export default Table;
