import { useMemo, useState } from 'react';

import type { EAMStatus, EmergencyActionMessage } from '../../lib/apiClient';

import { StatusBadge } from './StatusBadge';

type SortDirection = 'asc' | 'desc';

type MessageSortColumn =
  | 'callsign'
  | 'groupName'
  | 'securityStatus'
  | 'securityCapability'
  | 'preparednessStatus'
  | 'medicalStatus'
  | 'mobilityStatus'
  | 'commsStatus';

interface SortState {
  column: MessageSortColumn;
  direction: SortDirection;
}

const STATUS_ORDER: Record<EAMStatus, number> = {
  Green: 0,
  Yellow: 1,
  Red: 2,
};

function compareStatus(
  a: EAMStatus | null | undefined,
  b: EAMStatus | null | undefined,
  direction: SortDirection,
): number {
  if (!a && !b) {
    return 0;
  }
  if (!a) {
    return direction === 'asc' ? 1 : -1;
  }
  if (!b) {
    return direction === 'asc' ? -1 : 1;
  }

  const result = STATUS_ORDER[a] - STATUS_ORDER[b];
  return direction === 'asc' ? result : -result;
}

function compareString(
  a: string | null | undefined,
  b: string | null | undefined,
  direction: SortDirection,
): number {
  const normalizedA = a?.trim().toLowerCase();
  const normalizedB = b?.trim().toLowerCase();

  if (!normalizedA && !normalizedB) {
    return 0;
  }
  if (!normalizedA) {
    return direction === 'asc' ? 1 : -1;
  }
  if (!normalizedB) {
    return direction === 'asc' ? -1 : 1;
  }

  const result = normalizedA.localeCompare(normalizedB, undefined, {
    sensitivity: 'base',
  });
  return direction === 'asc' ? result : -result;
}

function sortMessages(
  messages: EmergencyActionMessage[],
  sortState: SortState,
): EmergencyActionMessage[] {
  const sorted = messages.slice();

  sorted.sort((a, b) => {
    switch (sortState.column) {
      case 'callsign':
        return compareString(a.callsign, b.callsign, sortState.direction);
      case 'groupName':
        return compareString(a.groupName, b.groupName, sortState.direction);
      case 'securityStatus':
        return compareStatus(a.securityStatus, b.securityStatus, sortState.direction);
      case 'securityCapability':
        return compareStatus(a.securityCapability, b.securityCapability, sortState.direction);
      case 'preparednessStatus':
        return compareStatus(a.preparednessStatus, b.preparednessStatus, sortState.direction);
      case 'medicalStatus':
        return compareStatus(a.medicalStatus, b.medicalStatus, sortState.direction);
      case 'mobilityStatus':
        return compareStatus(a.mobilityStatus, b.mobilityStatus, sortState.direction);
      case 'commsStatus':
        return compareStatus(a.commsStatus, b.commsStatus, sortState.direction);
      default:
        return 0;
    }
  });

  return sorted;
}

function getAriaSort(sortState: SortState, column: MessageSortColumn): 'ascending' | 'descending' | 'none' {
  if (sortState.column !== column) {
    return 'none';
  }

  return sortState.direction === 'asc' ? 'ascending' : 'descending';
}

function getSortButtonLabel(sortState: SortState, column: MessageSortColumn, label: string): string {
  if (sortState.column === column) {
    const directionLabel = sortState.direction === 'asc' ? 'ascending' : 'descending';
    return `Sort by ${label} (currently ${directionLabel})`;
  }
  return `Sort by ${label} (ascending)`;
}

function renderSortIndicator(sortState: SortState, column: MessageSortColumn): JSX.Element {
  const isActive = sortState.column === column;
  const icon = !isActive ? '↕' : sortState.direction === 'asc' ? '↑' : '↓';
  return (
    <span
      className={`sortable-header__icon${isActive ? ' sortable-header__icon--active' : ''}`}
      aria-hidden="true"
    >
      {icon}
    </span>
  );
}

export interface MessagesTableProps {
  messages: EmergencyActionMessage[];
  isLoading: boolean;
  onEdit: (message: EmergencyActionMessage) => void;
  onDelete: (message: EmergencyActionMessage) => void;
  onCreateNew: () => void;
}

export function MessagesTable({
  messages,
  isLoading,
  onEdit,
  onDelete,
  onCreateNew,
}: MessagesTableProps): JSX.Element {
  const [sortState, setSortState] = useState<SortState>({ column: 'callsign', direction: 'asc' });

  const sortedMessages = useMemo(() => sortMessages(messages, sortState), [messages, sortState]);

  function handleSort(column: MessageSortColumn): void {
    setSortState((previous) => {
      if (previous.column === column) {
        return {
          column,
          direction: previous.direction === 'asc' ? 'desc' : 'asc',
        };
      }
      return { column, direction: 'asc' };
    });
  }

  return (
    <div className="table-card">
      <header className="table-card__header">
        <div>
          <h3>Emergency action messages</h3>
          <p>Monitor status updates from field teams and dispatch support.</p>
        </div>
        <span className="pill pill--subtle">{messages.length} active</span>
      </header>
      <div className="table-card__body">
        {isLoading && <p>Loading messages…</p>}
        {!isLoading && messages.length === 0 && <p>No messages recorded yet.</p>}
        {!isLoading && messages.length > 0 && (
          <table>
            <thead>
              <tr>
                <th scope="col" aria-sort={getAriaSort(sortState, 'callsign')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('callsign')}
                    aria-label={getSortButtonLabel(sortState, 'callsign', 'Callsign')}
                    title="Sort by Callsign"
                  >
                    <span>Callsign</span>
                    {renderSortIndicator(sortState, 'callsign')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'groupName')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('groupName')}
                    aria-label={getSortButtonLabel(sortState, 'groupName', 'Group')}
                    title="Sort by Group"
                  >
                    <span>Group</span>
                    {renderSortIndicator(sortState, 'groupName')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'securityStatus')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('securityStatus')}
                    aria-label={getSortButtonLabel(sortState, 'securityStatus', 'Security')}
                    title="Sort by Security"
                  >
                    <span>Security</span>
                    {renderSortIndicator(sortState, 'securityStatus')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'securityCapability')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('securityCapability')}
                    aria-label={getSortButtonLabel(sortState, 'securityCapability', 'Capability')}
                    title="Sort by Capability"
                  >
                    <span>Capability</span>
                    {renderSortIndicator(sortState, 'securityCapability')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'preparednessStatus')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('preparednessStatus')}
                    aria-label={getSortButtonLabel(sortState, 'preparednessStatus', 'Preparedness')}
                    title="Sort by Preparedness"
                  >
                    <span>Preparedness</span>
                    {renderSortIndicator(sortState, 'preparednessStatus')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'medicalStatus')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('medicalStatus')}
                    aria-label={getSortButtonLabel(sortState, 'medicalStatus', 'Medical')}
                    title="Sort by Medical"
                  >
                    <span>Medical</span>
                    {renderSortIndicator(sortState, 'medicalStatus')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'mobilityStatus')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('mobilityStatus')}
                    aria-label={getSortButtonLabel(sortState, 'mobilityStatus', 'Mobility')}
                    title="Sort by Mobility"
                  >
                    <span>Mobility</span>
                    {renderSortIndicator(sortState, 'mobilityStatus')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'commsStatus')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('commsStatus')}
                    aria-label={getSortButtonLabel(sortState, 'commsStatus', 'Comms')}
                    title="Sort by Comms"
                  >
                    <span>Comms</span>
                    {renderSortIndicator(sortState, 'commsStatus')}
                  </button>
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedMessages.map((message) => (
                  <tr key={message.callsign}>
                    <td>
                      <div className="callsign-cell">
                        <span className="callsign">{message.callsign}</span>
                        {message.commsMethod && (
                          <span className="callsign-subtitle">{message.commsMethod}</span>
                        )}
                      </div>
                    </td>
                    <td>{message.groupName ?? '—'}</td>
                    <td>
                      <StatusBadge status={message.securityStatus} />
                    </td>
                    <td>
                      <StatusBadge status={message.securityCapability} />
                    </td>
                    <td>
                      <StatusBadge status={message.preparednessStatus} />
                    </td>
                    <td>
                      <StatusBadge status={message.medicalStatus} />
                    </td>
                    <td>
                      <StatusBadge status={message.mobilityStatus} />
                    </td>
                    <td>
                      <StatusBadge status={message.commsStatus} />
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          type="button"
                          className="button button--secondary"
                          onClick={() => onEdit(message)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="button button--danger"
                          onClick={() => onDelete(message)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}
      </div>
      <footer className="table-card__footer">
        <button type="button" className="button" onClick={onCreateNew}>
          New
        </button>
      </footer>
    </div>
  );
}
