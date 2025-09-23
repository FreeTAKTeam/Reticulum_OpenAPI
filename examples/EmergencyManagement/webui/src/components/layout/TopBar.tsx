import { useMemo } from 'react';

import { getApiBaseUrl } from '../../lib/apiClient';

export function TopBar(): JSX.Element {
  const gatewayBaseUrl = useMemo(() => getApiBaseUrl(), []);

  return (
    <header className="app-topbar">
      <div>
        <span className="topbar-label">Mesh Network Status:</span>
        <span className="topbar-value">Awaiting updates…</span>
      </div>
      <div className="topbar-gateway">
        Gateway: <code>{gatewayBaseUrl}</code>
      </div>
    </header>
  );
}
