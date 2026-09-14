import React from 'react';

export function LoadingState({ children, message = "Loading..." }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-600" />
      <p className="text-sm text-slate-500">{message}</p>
      {children}
    </div>
  );
}

export function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: 8 }).map((_, index) => (
        <td key={index} className="px-4 py-4">
          <div className="h-4 rounded bg-gray-200" />
        </td>
      ))}
    </tr>
  );
}
