import React from 'react';

/**
 * Toolbar with bulk actions for selected devices.
 * Props:
 *  - selected (array of device objects)
 *  - onPowerToggle(state: 'on'|'off')
 *  - onScan()
 */
export default function BulkActionsToolbar({ selected, onPowerToggle, onScan }) {
  const hasSelection = selected.length > 0;

  return (
    <div className="flex space-x-2 mb-4">
      <button
        className="px-3 py-2 rounded bg-green-600 text-white disabled:opacity-40"
        disabled={!hasSelection}
        onClick={() => onPowerToggle('on')}
      >
        Power On
      </button>
      <button
        className="px-3 py-2 rounded bg-red-600 text-white disabled:opacity-40"
        disabled={!hasSelection}
        onClick={() => onPowerToggle('off')}
      >
        Power Off
      </button>
      <button
        className="px-3 py-2 rounded bg-blue-600 text-white disabled:opacity-40"
        disabled={!hasSelection}
        onClick={onScan}
      >
        Scan Vulnerabilities
      </button>
      <span className="ml-auto text-sm text-gray-600">{selected.length} selected</span>
    </div>
  );
}
