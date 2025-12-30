"use client";

interface TableData {
  title?: string;
  columns: string[];
  rows: (string | number | boolean | null)[][];
}

interface TableArtifactProps {
  data: unknown;
}

export default function TableArtifact({ data }: TableArtifactProps) {
  const tableData = data as TableData;

  if (!tableData?.columns || !tableData?.rows) {
    return (
      <div className="p-4 text-gray-400 text-center">
        No table data available
      </div>
    );
  }

  return (
    <div className="overflow-auto max-h-96 rounded-lg border border-gray-200 shadow-sm">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50 sticky top-0">
          <tr>
            {tableData.columns.map((column, index) => (
              <th
                key={index}
                scope="col"
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {tableData.rows.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className={rowIndex % 2 === 0 ? "bg-white" : "bg-gray-50"}
            >
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap"
                >
                  {formatCell(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {tableData.rows.length === 0 && (
        <div className="p-4 text-center text-gray-400">No data to display</div>
      )}
    </div>
  );
}

function formatCell(value: string | number | boolean | null): string {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return String(value);
}
