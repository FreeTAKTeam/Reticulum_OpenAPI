import { useEffect, useMemo, useState } from 'react';

import {
  apiClient,
  extractApiErrorMessage,
  getApiBaseUrl,
  getConfiguredServerIdentity,
  getLiveUpdatesUrl,
} from '../lib/apiClient';

interface LinkStatus {
  state: 'pending' | 'connected' | 'error' | 'unconfigured' | 'unknown';
  message?: string | null;
  serverIdentity?: string | null;
  lastAttempt?: string | null;
  lastSuccess?: string | null;
  lastError?: string | null;
}

interface GatewayInfo {
  version: string;
  uptime: string;
  serverIdentity?: string | null;
  clientDisplayName: string;
  requestTimeoutSeconds: number;
  lxmfConfigPath?: string | null;
  lxmfStoragePath?: string | null;
  allowedOrigins?: string[];
  linkStatus?: LinkStatus | null;
}

export function DashboardPage(): JSX.Element {
  const [gatewayInfo, setGatewayInfo] = useState<GatewayInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const webUiConfig = useMemo(
    () => ({
      apiBaseUrl: getApiBaseUrl(),
      liveUpdatesUrl: getLiveUpdatesUrl(),
      serverIdentityHeader: getConfiguredServerIdentity() ?? null,
    }),
    [],
  );
  const allowedOrigins = useMemo(
    () =>
      gatewayInfo && Array.isArray(gatewayInfo.allowedOrigins)
        ? gatewayInfo.allowedOrigins
        : [],
    [gatewayInfo],
  );
  const linkStatus = gatewayInfo?.linkStatus ?? null;
  const resolvedLinkMessage = linkStatus?.message ?? 'No link status reported yet.';
  const resolvedLinkState = linkStatus?.state ?? 'unknown';
  const resolvedLastSuccess = linkStatus?.lastSuccess ?? 'Never';
  const resolvedLastAttempt = linkStatus?.lastAttempt ?? 'Never';
  const resolvedLastError = linkStatus?.lastError ?? null;

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
            <div>
              <dt>Link State</dt>
              <dd>{resolvedLinkState}</dd>
            </div>
            <div>
              <dt>Link Status</dt>
              <dd>{resolvedLinkMessage}</dd>
            </div>
            <div>
              <dt>Last Successful Link</dt>
              <dd>{resolvedLastSuccess}</dd>
            </div>
            <div>
              <dt>Last Link Attempt</dt>
              <dd>{resolvedLastAttempt}</dd>
            </div>
            {resolvedLastError && (
              <div>
                <dt>Last Link Error</dt>
                <dd>{resolvedLastError}</dd>
              </div>
            )}
          </dl>
        )}
      </div>
      {gatewayInfo && (
        <div className="page-card">
          <h3>Gateway Configuration</h3>
          <dl className="page-definition-list">
            <div>
              <dt>Server Identity</dt>
              <dd>{gatewayInfo.serverIdentity ?? 'Not configured'}</dd>
            </div>
            <div>
              <dt>Client Display Name</dt>
              <dd>{gatewayInfo.clientDisplayName}</dd>
            </div>
            <div>
              <dt>Request Timeout</dt>
              <dd>
                {Number.isInteger(gatewayInfo.requestTimeoutSeconds)
                  ? `${gatewayInfo.requestTimeoutSeconds} seconds`
                  : `${gatewayInfo.requestTimeoutSeconds.toFixed(1)} seconds`}
              </dd>
            </div>
            <div>
              <dt>LXMF Config Path</dt>
              <dd>{gatewayInfo.lxmfConfigPath ?? 'Not configured'}</dd>
            </div>
            <div>
              <dt>LXMF Storage Path</dt>
              <dd>{gatewayInfo.lxmfStoragePath ?? 'Not configured'}</dd>
            </div>
            <div>
              <dt>Allowed Origins</dt>
              <dd>
                {allowedOrigins.length > 0
                  ? allowedOrigins.join(', ')
                  : 'Not configured'}
              </dd>
            </div>
          </dl>
        </div>
      )}
      <div className="page-card">
        <h3>Web UI API Configuration</h3>
        <dl className="page-definition-list">
          <div>
            <dt>API Base URL</dt>
            <dd>{webUiConfig.apiBaseUrl}</dd>
          </div>
          <div>
            <dt>Live Updates URL</dt>
            <dd>{webUiConfig.liveUpdatesUrl}</dd>
          </div>
          <div>
            <dt>Server Identity Header</dt>
            <dd>{webUiConfig.serverIdentityHeader ?? 'Not configured'}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
