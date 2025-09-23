import type { EmergencyActionMessage } from '../../lib/apiClient';

interface MessageDetailsProps {
  message: EmergencyActionMessage | null;
  onEdit: () => void;
  onDelete: () => void;
}

const FIELD_LABELS: Array<keyof EmergencyActionMessage> = [
  'groupName',
  'securityStatus',
  'securityCapability',
  'preparednessStatus',
  'medicalStatus',
  'mobilityStatus',
  'commsStatus',
  'commsMethod',
];

function formatFieldLabel(field: keyof EmergencyActionMessage): string {
  return field
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (char) => char.toUpperCase());
}

export function MessageDetails({
  message,
  onEdit,
  onDelete,
}: MessageDetailsProps): JSX.Element {
  if (!message) {
    return (
      <div className="message-details-empty">
        Select a message from the table to review its details.
      </div>
    );
  }

  return (
    <div className="message-details">
      <header className="message-details-header">
        <div>
          <h3>{message.callsign}</h3>
          {message.groupName && <p className="message-details-subtitle">Group: {message.groupName}</p>}
        </div>
        <div className="message-details-actions">
          <button type="button" onClick={onEdit} className="secondary-button">
            Edit
          </button>
          <button type="button" onClick={onDelete} className="danger-button">
            Delete
          </button>
        </div>
      </header>
      <dl className="page-definition-list">
        {FIELD_LABELS.map((field) => (
          <div key={field}>
            <dt>{formatFieldLabel(field)}</dt>
            <dd>{message[field] ?? '—'}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
