interface DeleteMessageDialogProps {
  callsign: string | null;
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteMessageDialog({
  callsign,
  isOpen,
  onCancel,
  onConfirm,
}: DeleteMessageDialogProps): JSX.Element | null {
  if (!isOpen || !callsign) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <h3>Delete message</h3>
        <p>
          Are you sure you want to delete the message for <strong>{callsign}</strong>? This
          action cannot be undone.
        </p>
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="danger-button" onClick={onConfirm}>
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
