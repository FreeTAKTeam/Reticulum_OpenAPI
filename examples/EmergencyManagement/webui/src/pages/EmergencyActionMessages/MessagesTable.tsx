import { useMemo, useState } from 'react';

import type { EAMStatus, EmergencyActionMessage } from '../../lib/apiClient';

type StatusFilter = 'all' | EAMStatus;

interface MessagesTableProps {
  messages: EmergencyActionMessage[];
  selectedCallsign: string | null;
  onSelect: (callsign: string) => void;
}

const STATUS_FILTER_OPTIONS: StatusFilter[] = ['all', 'Red', 'Yellow', 'Green'];

function normaliseText(value: string | undefined | null): string {
  return (value ?? '').toLowerCase();
}

export function MessagesTable({
  messages,
  selectedCallsign,
  onSelect,
}: MessagesTableProps): JSX.Element {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const filteredMessages = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return messages.filter((message) => {
      const matchesTerm = term
        ? normaliseText(message.callsign).includes(term) ||
          normaliseText(message.groupName).includes(term)
        : true;
      const matchesStatus =
        statusFilter === 'all' || message.securityStatus === statusFilter;
      return matchesTerm && matchesStatus;
    });
  }, [messages, searchTerm, statusFilter]);

  return (
    <div className="messages-table" aria-live="polite">
      <div className="messages-table-controls">
        <label className="field-label" htmlFor="eam-search-input">
          Search
        </label>
        <input
          id="eam-search-input"
          type="search"
          value={searchTerm}
          placeholder="Search by callsign or group"
          onChange={(event) => setSearchTerm(event.target.value)}
        />
        <label className="field-label" htmlFor="eam-status-filter">
          Security status
        </label>
        <select
          id="eam-status-filter"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
        >
          {STATUS_FILTER_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option === 'all' ? 'All statuses' : option}
            </option>
          ))}
        </select>
      </div>
      <table>
        <thead>
          <tr>
            <th scope="col">Callsign</th>
            <th scope="col">Group</th>
            <th scope="col">Security</th>
            <th scope="col">Comms</th>
          </tr>
        </thead>
        <tbody>
          {filteredMessages.length === 0 ? (
            <tr>
              <td colSpan={4} className="messages-table-empty">
                No messages match the current filters.
              </td>
            </tr>
          ) : (
            filteredMessages.map((message) => {
              const isSelected = message.callsign === selectedCallsign;
              return (
                <tr
                  key={message.callsign}
                  className={isSelected ? 'messages-table-row-selected' : ''}
                  onClick={() => onSelect(message.callsign)}
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      onSelect(message.callsign);
                    }
                  }}
                  aria-selected={isSelected}
                >
                  <td>{message.callsign}</td>
                  <td>{message.groupName ?? '—'}</td>
                  <td>{message.securityStatus ?? '—'}</td>
                  <td>{message.commsStatus ?? '—'}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
