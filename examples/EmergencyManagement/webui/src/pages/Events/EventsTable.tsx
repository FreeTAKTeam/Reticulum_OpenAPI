import { useMemo, useState } from 'react';

import type { EAMStatus, EventRecord } from '../../lib/apiClient';

export interface EventsTableProps {
  events: EventRecord[];
  isLoading: boolean;
  onEdit: (event: EventRecord) => void;
  onDelete: (event: EventRecord) => void;
  onCreateNew: () => void;
}

type SortDirection = 'asc' | 'desc';

type EventsSortColumn = 'uid' | 'type' | 'detail' | 'start' | 'how';

interface SortState {
  column: EventsSortColumn;
  direction: SortDirection;
}

function compareNumber(
  a: number | string | null | undefined,
  b: number | string | null | undefined,
  direction: SortDirection,
): number {
  const parsedA = typeof a === 'number' ? a : a ? Number(a) : Number.NaN;
  const parsedB = typeof b === 'number' ? b : b ? Number(b) : Number.NaN;

  const isValidA = Number.isFinite(parsedA);
  const isValidB = Number.isFinite(parsedB);

  if (!isValidA && !isValidB) {
    return 0;
  }
  if (!isValidA) {
    return direction === 'asc' ? 1 : -1;
  }
  if (!isValidB) {
    return direction === 'asc' ? -1 : 1;
  }

  const result = parsedA - parsedB;
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

function compareDate(
  a: string | null | undefined,
  b: string | null | undefined,
  direction: SortDirection,
): number {
  const parsedA = a ? Date.parse(a) : Number.NaN;
  const parsedB = b ? Date.parse(b) : Number.NaN;

  const isValidA = Number.isFinite(parsedA);
  const isValidB = Number.isFinite(parsedB);

  if (!isValidA && !isValidB) {
    return 0;
  }
  if (!isValidA) {
    return direction === 'asc' ? 1 : -1;
  }
  if (!isValidB) {
    return direction === 'asc' ? -1 : 1;
  }

  const result = parsedA - parsedB;
  return direction === 'asc' ? result : -result;
}

function getDetailSortValue(detail: EventRecord['detail']): string | undefined {
  return detail?.emergencyActionMessage?.callsign ?? undefined;
}

function sortEvents(events: EventRecord[], sortState: SortState): EventRecord[] {
  const sorted = events.slice();

  sorted.sort((a, b) => {
    switch (sortState.column) {
      case 'uid':
        return compareNumber(a.uid, b.uid, sortState.direction);
      case 'type':
        return compareString(a.type, b.type, sortState.direction);
      case 'detail':
        return compareString(
          getDetailSortValue(a.detail),
          getDetailSortValue(b.detail),
          sortState.direction,
        );
      case 'start':
        return compareDate(a.start, b.start, sortState.direction);
      case 'how':
        return compareString(a.how, b.how, sortState.direction);
      default:
        return 0;
    }
  });

  return sorted;
}

function getAriaSort(sortState: SortState, column: EventsSortColumn): 'ascending' | 'descending' | 'none' {
  if (sortState.column !== column) {
    return 'none';
  }
  return sortState.direction === 'asc' ? 'ascending' : 'descending';
}

function getSortButtonLabel(sortState: SortState, column: EventsSortColumn, label: string): string {
  if (sortState.column === column) {
    const directionLabel = sortState.direction === 'asc' ? 'ascending' : 'descending';
    return `Sort by ${label} (currently ${directionLabel})`;
  }
  return `Sort by ${label} (ascending)`;
}

function renderSortIndicator(sortState: SortState, column: EventsSortColumn): JSX.Element {
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

interface StatusEntry {
  label: string;
  value: EAMStatus | null | undefined;
}

function isStatus(value: StatusEntry): value is { label: string; value: EAMStatus } {
  return value.value === 'Green' || value.value === 'Yellow' || value.value === 'Red';
}

function renderDetail(detail: EventRecord['detail']): JSX.Element {
  const message = detail?.emergencyActionMessage;
  if (!message) {
    return <span>—</span>;
  }

  const statuses = (
    [
      { label: 'Security', value: message.securityStatus },
      { label: 'Capability', value: message.securityCapability },
      { label: 'Preparedness', value: message.preparednessStatus },
      { label: 'Medical', value: message.medicalStatus },
      { label: 'Mobility', value: message.mobilityStatus },
      { label: 'Comms', value: message.commsStatus },
    ] satisfies StatusEntry[]
  ).filter(isStatus);

  return (
    <div className="events-detail">
      <div className="events-detail__headline">
        <span className="events-detail__callsign">{message.callsign}</span>
        {message.groupName && <span className="events-detail__group">· {message.groupName}</span>}
      </div>
      {statuses.length > 0 && (
        <div className="events-detail__statuses">
          {statuses.map(({ label, value }) => (
            <span key={label} className={`status-badge status-badge--${value.toLowerCase()}`}>
              {`${label}: ${value}`}
            </span>
          ))}
        </div>
      )}
      {message.commsMethod && (
        <div className="events-detail__meta">Method: {message.commsMethod}</div>
      )}
    </div>
  );
}

export function EventsTable({
  events,
  isLoading,
  onEdit,
  onDelete,
  onCreateNew,
}: EventsTableProps): JSX.Element {
  const [sortState, setSortState] = useState<SortState>({ column: 'uid', direction: 'asc' });

  const sortedEvents = useMemo(() => sortEvents(events, sortState), [events, sortState]);

  function handleSort(column: EventsSortColumn): void {
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
          <h3>Event timeline</h3>
          <p>Review operational updates and mesh incident traffic.</p>
        </div>
        <span className="pill pill--subtle">{events.length} logged</span>
      </header>
      <div className="table-card__body">
        {isLoading && <p>Loading events…</p>}
        {!isLoading && events.length === 0 && <p>No events reported yet.</p>}
        {!isLoading && events.length > 0 && (
          <table>
            <thead>
              <tr>
                <th scope="col" aria-sort={getAriaSort(sortState, 'uid')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('uid')}
                    aria-label={getSortButtonLabel(sortState, 'uid', 'UID')}
                    title="Sort by UID"
                  >
                    <span>UID</span>
                    {renderSortIndicator(sortState, 'uid')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'type')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('type')}
                    aria-label={getSortButtonLabel(sortState, 'type', 'Type')}
                    title="Sort by Type"
                  >
                    <span>Type</span>
                    {renderSortIndicator(sortState, 'type')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'detail')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('detail')}
                    aria-label={getSortButtonLabel(sortState, 'detail', 'Detail')}
                    title="Sort by Detail"
                  >
                    <span>Detail</span>
                    {renderSortIndicator(sortState, 'detail')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'start')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('start')}
                    aria-label={getSortButtonLabel(sortState, 'start', 'Start')}
                    title="Sort by Start"
                  >
                    <span>Start</span>
                    {renderSortIndicator(sortState, 'start')}
                  </button>
                </th>
                <th scope="col" aria-sort={getAriaSort(sortState, 'how')}>
                  <button
                    type="button"
                    className="sortable-header__button"
                    onClick={() => handleSort('how')}
                    aria-label={getSortButtonLabel(sortState, 'how', 'How')}
                    title="Sort by How"
                  >
                    <span>How</span>
                    {renderSortIndicator(sortState, 'how')}
                  </button>
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedEvents.map((event) => (
                <tr key={event.uid}>
                  <td>{event.uid}</td>
                  <td>{event.type ?? '—'}</td>
                  <td>{renderDetail(event.detail)}</td>
                  <td>{event.start ?? '—'}</td>
                  <td>{event.how ?? '—'}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        type="button"
                        className="button button--secondary"
                        onClick={() => onEdit(event)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="button button--danger"
                        onClick={() => onDelete(event)}
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
