import type { EAMStatus } from '../../lib/apiClient';

export function StatusBadge({ status }: { status?: EAMStatus | null }): JSX.Element {
  if (!status) {
    return <span className="status-badge status-badge--empty">—</span>;
  }
  const variant = status.toLowerCase();
  return <span className={`status-badge status-badge--${variant}`}>{status}</span>;
}
