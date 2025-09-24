import { useEffect, useState } from 'react';

import { apiClient, extractApiErrorMessage } from '../lib/apiClient';

interface GatewayInfo {
  version: string;
  uptime: string;
}

export function DashboardPage(): JSX.Element {
  const [gatewayInfo, setGatewayInfo] = useState<GatewayInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadInfo(): Promise<void> {
      if (!isMounted) {
        return;
      }
      setError(null);
      try {
        const response = await apiClient.get<GatewayInfo>('/');
        if (!isMounted) {
          return;
        }
        setGatewayInfo(response.data);
        setError(null);
      } catch (err: unknown) {
        if (!isMounted) {
          return;
        }
        setGatewayInfo(null);
        setError(extractApiErrorMessage(err));
      }
    }

    loadInfo();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section className="page-section">
      <header className="page-header">
        <h2>Dashboard</h2>
        <p>High-level overview of the Emergency Management gateway.</p>
      </header>
      <div className="page-card">
        <h3>Gateway Status</h3>
        {error && <p className="page-error">{error}</p>}
        {!error && !gatewayInfo && <p>Loading gateway information…</p>}
        {gatewayInfo && (
          <dl className="page-definition-list">
            <div>
              <dt>Version</dt>
              <dd>{gatewayInfo.version}</dd>
            </div>
            <div>
              <dt>Uptime</dt>
              <dd>{gatewayInfo.uptime}</dd>
            </div>
          </dl>
        )}
      </div>
    </section>
  );
}
