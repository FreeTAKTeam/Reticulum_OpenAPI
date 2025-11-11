import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  apiClient,
  createLinkDestination,
  deleteLinkDestination,
  extractApiErrorMessage,
  getApiBaseUrl,
  getConfiguredServerIdentity,
  getLinkDestinationSettings,
  getLiveUpdatesUrl,
  LinkDestinationSettings,
  LinkStatus,
  updateLinkDestination,
} from '../lib/apiClient';

interface ReticulumInterfaceStatus {
  id: string;
  name: string;
  type: string;
  online: boolean;
  mode?: string | null;
  bitrate?: number | null;
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
  reticulumInterfaces?: ReticulumInterfaceStatus[] | null;
}

export function DashboardPage(): JSX.Element {
  const [gatewayInfo, setGatewayInfo] = useState<GatewayInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [linkDestination, setLinkDestination] = useState<LinkDestinationSettings | null>(null);
  const [linkDestinationInput, setLinkDestinationInput] = useState('');
  const [linkDestinationError, setLinkDestinationError] = useState<string | null>(null);
  const [linkDestinationSuccess, setLinkDestinationSuccess] = useState<string | null>(null);
  const [isSavingLinkDestination, setIsSavingLinkDestination] = useState(false);
  const isMountedRef = useRef(true);
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
  const reticulumInterfaces = useMemo(
    () =>
      gatewayInfo && Array.isArray(gatewayInfo.reticulumInterfaces)
        ? gatewayInfo.reticulumInterfaces
        : [],
    [gatewayInfo],
  );
  const linkStatus = gatewayInfo?.linkStatus ?? null;
  const resolvedLinkMessage = linkStatus?.message ?? 'No link status reported yet.';
  const resolvedLinkState = linkStatus?.state ?? 'unknown';
  const resolvedLastSuccess = linkStatus?.lastSuccess ?? 'Never';
  const resolvedLastAttempt = linkStatus?.lastAttempt ?? 'Never';
  const resolvedLastError = linkStatus?.lastError ?? null;
  const activeInterfaces = useMemo(
    () => reticulumInterfaces.filter((item) => item.online),
    [reticulumInterfaces],
  );
  const formatInterface = (item: ReticulumInterfaceStatus): string => {
    const parts: string[] = [];
    const resolvedName = item.name?.trim() ? item.name.trim() : item.type;
    parts.push(resolvedName);
    if (item.mode?.trim()) {
      parts.push(item.mode.trim());
    }
    if (typeof item.bitrate === 'number' && Number.isFinite(item.bitrate)) {
      parts.push(`${item.bitrate} bps`);
    }
    return parts.join(' • ');
  };

  const applyLinkDestinationResponse = useCallback(
    (response: LinkDestinationSettings) => {
      if (!isMountedRef.current) {
        return;
      }
      setLinkDestination(response);
      setLinkDestinationInput(response.serverIdentity ?? '');
      setGatewayInfo((previous) =>
        previous
          ? {
              ...previous,
              serverIdentity: response.serverIdentity ?? null,
              linkStatus: response.linkStatus ?? previous.linkStatus,
            }
          : previous,
      );
    },
    [],
  );

  const loadGatewayInfo = useCallback(async () => {
    setError(null);
    try {
      const response = await apiClient.get<GatewayInfo>('/');
      if (!isMountedRef.current) {
        return;
      }
      setGatewayInfo(response.data);
    } catch (err: unknown) {
      if (!isMountedRef.current) {
        return;
      }
      setGatewayInfo(null);
      setError(extractApiErrorMessage(err));
    }
  }, [extractApiErrorMessage]);

  const loadLinkDestination = useCallback(async () => {
    setLinkDestinationError(null);
    setLinkDestinationSuccess(null);
    try {
      const response = await getLinkDestinationSettings();
      applyLinkDestinationResponse(response);
    } catch (err: unknown) {
      if (!isMountedRef.current) {
        return;
      }
      setLinkDestination(null);
      setLinkDestinationInput('');
      setLinkDestinationError(extractApiErrorMessage(err));
    }
  }, [applyLinkDestinationResponse, extractApiErrorMessage]);

  const handleLinkDestinationInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      setLinkDestinationInput(event.target.value);
    },
    [],
  );

  const handleLinkDestinationSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!linkDestination?.configurable) {
        setLinkDestinationError('Gateway configuration is read-only.');
        return;
      }
      const trimmed = linkDestinationInput.trim();
      if (!trimmed) {
        setLinkDestinationError('Server identity hash is required.');
        return;
      }
      setIsSavingLinkDestination(true);
      setLinkDestinationError(null);
      setLinkDestinationSuccess(null);
      try {
        const payload = { serverIdentity: trimmed };
        const response = linkDestination?.serverIdentity
          ? await updateLinkDestination(payload)
          : await createLinkDestination(payload);
        applyLinkDestinationResponse(response);
        if (!isMountedRef.current) {
          return;
        }
        setLinkDestinationSuccess('Link destination saved.');
      } catch (err: unknown) {
        if (!isMountedRef.current) {
          return;
        }
        setLinkDestinationError(extractApiErrorMessage(err));
      } finally {
        if (isMountedRef.current) {
          setIsSavingLinkDestination(false);
        }
      }
    },
    [
      linkDestination,
      linkDestinationInput,
      applyLinkDestinationResponse,
      extractApiErrorMessage,
    ],
  );

  const handleLinkDestinationClear = useCallback(async () => {
    if (!linkDestination?.configurable) {
      return;
    }
    if (!linkDestination.serverIdentity) {
      setLinkDestinationInput('');
      return;
    }
    setIsSavingLinkDestination(true);
    setLinkDestinationError(null);
    setLinkDestinationSuccess(null);
    try {
      await deleteLinkDestination();
      const refreshed = await getLinkDestinationSettings();
      applyLinkDestinationResponse(refreshed);
      if (!isMountedRef.current) {
        return;
      }
      setLinkDestinationSuccess('Link destination removed.');
    } catch (err: unknown) {
      if (!isMountedRef.current) {
        return;
      }
      setLinkDestinationError(extractApiErrorMessage(err));
    } finally {
      if (isMountedRef.current) {
        setIsSavingLinkDestination(false);
      }
    }
  }, [linkDestination, applyLinkDestinationResponse, extractApiErrorMessage]);

  useEffect(() => {
    isMountedRef.current = true;
    loadGatewayInfo();
    loadLinkDestination();
    return () => {
      isMountedRef.current = false;
    };
  }, [loadGatewayInfo, loadLinkDestination]);

  return (
    <section className="page-section">
      <header className="page-header">
        <h2>Dashboard</h2>
        <p>High-level overview of the Emergency Management gateway.</p>
      </header>
      <div className="dashboard-layout">
        <div className="page-card dashboard-layout__status-card">
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
              <div>
                <dt>Active Interfaces</dt>
                <dd>
                  {activeInterfaces.length > 0
                    ? activeInterfaces.map((item) => formatInterface(item)).join(', ')
                    : 'No active interfaces reported'}
                </dd>
              </div>
              <div>
                <dt>Configured Interfaces</dt>
                <dd>
                  {reticulumInterfaces.length > 0
                    ? reticulumInterfaces
                        .map((item) =>
                          `${formatInterface(item)} (${item.online ? 'online' : 'offline'})`,
                        )
                        .join(', ')
                    : 'No interfaces reported'}
                </dd>
              </div>
            </dl>
          )}
        </div>
        {gatewayInfo && (
          <div className="page-card dashboard-layout__configuration-card">
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
        <div className="page-card dashboard-layout__link-card">
          <h3>Link Destination</h3>
          {!linkDestination && !linkDestinationError && (
            <p>Loading link destination…</p>
          )}
          {linkDestinationError && <p className="page-error">{linkDestinationError}</p>}
          {linkDestinationSuccess && <p className="page-success">{linkDestinationSuccess}</p>}
          {linkDestination && (
            <>
              {!linkDestination.configurable && (
                <p className="page-error">
                  Runtime updates are disabled because the gateway is using environment overrides.
                </p>
              )}
              <form onSubmit={handleLinkDestinationSubmit}>
                <label className="form-field form-field--wide" htmlFor="link-destination-input">
                  <span>Server Identity</span>
                  <input
                    id="link-destination-input"
                    type="text"
                    value={linkDestinationInput}
                    onChange={handleLinkDestinationInputChange}
                    autoComplete="off"
                    autoCorrect="off"
                    spellCheck={false}
                    placeholder="Enter 32 character destination hash"
                    disabled={!linkDestination.configurable || isSavingLinkDestination}
                  />
                </label>
                <div className="form-card__footer">
                  <button
                    type="submit"
                    className="button"
                    disabled={
                      !linkDestination.configurable ||
                      isSavingLinkDestination ||
                      !linkDestinationInput.trim()
                    }
                  >
                    Save Link Destination
                  </button>
                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={handleLinkDestinationClear}
                    disabled={
                      !linkDestination.configurable ||
                      isSavingLinkDestination ||
                      !linkDestination.serverIdentity
                    }
                  >
                    Clear
                  </button>
                </div>
              </form>
              <dl className="page-definition-list">
                <div>
                  <dt>Config Path</dt>
                  <dd>{linkDestination.configPath ?? 'Provided via environment'}</dd>
                </div>
                <div>
                  <dt>Gateway Link State</dt>
                  <dd>{linkDestination.linkStatus?.state ?? 'unknown'}</dd>
                </div>
                <div>
                  <dt>Gateway Link Message</dt>
                  <dd>
                    {linkDestination.linkStatus?.message ?? 'No link status reported yet.'}
                  </dd>
                </div>
              </dl>
            </>
          )}
        </div>
        <div className="page-card dashboard-layout__api-card">
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
      </div>
    </section>
  );
}
