import type { EventRecord } from '../../lib/apiClient';

export interface EventsTableProps {
  events: EventRecord[];
  isLoading: boolean;
  onEdit: (event: EventRecord) => void;
  onDelete: (event: EventRecord) => void;
}

function truncate(text: string | null | undefined, length = 60): string {
  if (!text) {
    return '—';
  }
  return text.length > length ? `${text.slice(0, length)}…` : text;
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
                  <td>{truncate(event.detail)}</td>
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
