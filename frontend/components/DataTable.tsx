"use client";
interface Props {
  columns: string[];
  rows: string[][];
}

export default function DataTable({ columns, rows }: Props) {
  return (
    <div className="overflow-auto border rounded-md dark:border-gray-700">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                scope="col"
                className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-100 dark:hover:bg-gray-800">
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="px-3 py-2 whitespace-nowrap text-sm text-gray-700 dark:text-gray-200"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
