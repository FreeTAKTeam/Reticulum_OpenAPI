import type { EmergencyActionMessage } from '../../lib/apiClient';

import { StatusBadge } from './StatusBadge';

export interface MessagesTableProps {
  messages: EmergencyActionMessage[];
  isLoading: boolean;
  onEdit: (message: EmergencyActionMessage) => void;
  onDelete: (message: EmergencyActionMessage) => void;
}

export function MessagesTable({
  messages,
  isLoading,
  onEdit,
  onDelete,
}: MessagesTableProps): JSX.Element {
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
                <th>Callsign</th>
                <th>Group</th>
                <th>Security</th>
                <th>Capability</th>
                <th>Preparedness</th>
                <th>Medical</th>
                <th>Mobility</th>
                <th>Comms</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {messages
                .slice()
                .sort((a, b) => a.callsign.localeCompare(b.callsign))
                .map((message) => (
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
    </div>
  );
}
