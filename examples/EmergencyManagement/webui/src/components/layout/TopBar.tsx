import { useMemo } from 'react';

import { getApiBaseUrl } from '../../lib/apiClient';

import {
  Activity,
  Antenna,
  CloudDownload,
  Radio,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface StatusCard {
  label: string;
  value: string;
  icon: LucideIcon;
}

const STATUS_CARDS: StatusCard[] = [
  {
    label: 'Data Package',
    value: 'Awaiting sync',
    icon: CloudDownload,
  },
  {
    label: 'API & Federations',
    value: 'Listening',
    icon: Antenna,
  },
  {
    label: 'COT Network',
    value: 'Standby',
    icon: Radio,
  },
  {
    label: 'Connected Clients',
    value: '—',
    icon: Users,
  },
];

export function TopBar(): JSX.Element {
  const gatewayBaseUrl = useMemo(() => getApiBaseUrl(), []);

  return (
    <header className="app-topbar">
      <div className="topbar-overview">
        <div className="topbar-network">
          <span className="topbar-network__icon" aria-hidden="true">
            <Activity size={20} strokeWidth={2.4} />
          </span>
          <div className="topbar-network__content">
            <span className="topbar-label">Mesh Network</span>
            <span className="topbar-value">Awaiting updates…</span>
          </div>
        </div>
        <div className="topbar-gateway">
          <span className="topbar-label">Gateway</span>
          <code>{gatewayBaseUrl}</code>
        </div>
      </div>
      <div className="topbar-status-grid">
        {STATUS_CARDS.map((card) => (
          <div key={card.label} className="topbar-status-card">
            <span className="topbar-status-icon" aria-hidden="true">
              <card.icon size={18} strokeWidth={2.2} />
            </span>
            <div className="topbar-status-copy">
              <span className="topbar-status-label">{card.label}</span>
              <span className="topbar-status-value">{card.value}</span>
            </div>
            <span className="topbar-status-wave" aria-hidden="true" />
          </div>
        ))}
      </div>
    </header>
  );
}
