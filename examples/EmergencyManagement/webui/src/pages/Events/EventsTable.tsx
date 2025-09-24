import type { EAMStatus, EventRecord } from '../../lib/apiClient';

export interface EventsTableProps {
  events: EventRecord[];
  isLoading: boolean;
  onEdit: (event: EventRecord) => void;
  onDelete: (event: EventRecord) => void;
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

export function EventsTable({ events, isLoading, onEdit, onDelete }: EventsTableProps): JSX.Element {
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
                <th>UID</th>
                <th>Type</th>
                <th>Detail</th>
                <th>Start</th>
                <th>How</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
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
    </div>
  );
}
