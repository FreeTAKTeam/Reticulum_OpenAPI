import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AxiosResponse } from 'axios';

import * as apiClientModule from '../../lib/apiClient';
import { DashboardPage } from '../DashboardPage';

describe('DashboardPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  const buildGatewayInfoResponse = (): AxiosResponse<{
    version: string;
    uptime: string;
    serverIdentity?: string | null;
    clientDisplayName: string;
    requestTimeoutSeconds: number;
    lxmfConfigPath: string | null;
    lxmfStoragePath: string | null;
    allowedOrigins: string[];
    linkStatus: apiClientModule.LinkStatus;
    reticulumInterfaces: {
      id: string;
      name: string;
      type: string;
      online: boolean;
      mode?: string | null;
      bitrate?: number | null;
    }[];
  }> => ({
    data: {
      version: '1.2.3',
      uptime: '4 hours',
      serverIdentity: 'abc123',
      clientDisplayName: 'Responder',
      requestTimeoutSeconds: 45.5,
      lxmfConfigPath: '/tmp/config.json',
      lxmfStoragePath: '/tmp/storage',
      allowedOrigins: ['https://example.com'],
      linkStatus: {
        state: 'connected',
        message: 'Connected to LXMF server abc123',
        lastSuccess: '2025-09-23T12:34:56Z',
        lastAttempt: '2025-09-23T12:34:56Z',
        lastError: null,
      },
      reticulumInterfaces: [
        {
          id: 'AutoInterface:0',
          name: 'Mesh Neighbors',
          type: 'AutoInterface',
          online: true,
          mode: 'full',
          bitrate: 125000,
        },
        {
          id: 'TCPClientInterface:1',
          name: 'WAN Link',
          type: 'TCPClientInterface',
          online: false,
          mode: 'access_point',
          bitrate: null,
        },
      ],
    },
  } as AxiosResponse);

  const buildLinkDestinationSettings = (
    overrides: Partial<apiClientModule.LinkDestinationSettings> = {},
  ): apiClientModule.LinkDestinationSettings => ({
    serverIdentity: 'abc123',
    configurable: true,
    configPath: '/tmp/client_config.json',
    linkStatus: {
      state: 'connected',
      message: 'Connected to LXMF server abc123',
      serverIdentity: 'abc123',
    },
    ...overrides,
  });

  it('renders backend error message when loading gateway info fails', async () => {
    const backendMessage = 'Gateway temporarily offline';
    const error = new Error('503 Service Unavailable');
    vi.spyOn(apiClientModule.apiClient, 'get').mockRejectedValueOnce(error);
    const extractSpy = vi
      .spyOn(apiClientModule, 'extractApiErrorMessage')
      .mockReturnValue(backendMessage);
    vi.spyOn(apiClientModule, 'getLinkDestinationSettings').mockResolvedValue(
      buildLinkDestinationSettings(),
    );

    render(<DashboardPage />);

    expect(await screen.findByText(backendMessage)).toBeInTheDocument();
    expect(extractSpy).toHaveBeenCalledWith(error);
  });

  it('clears dashboard errors after successfully loading gateway info', async () => {
    vi.spyOn(apiClientModule.apiClient, 'get').mockResolvedValueOnce(buildGatewayInfoResponse());
    vi.spyOn(apiClientModule, 'getLinkDestinationSettings').mockResolvedValue(
      buildLinkDestinationSettings(),
    );

    render(<DashboardPage />);

    expect(await screen.findByText('1.2.3')).toBeInTheDocument();
    expect(screen.getByText('4 hours')).toBeInTheDocument();
    expect(screen.getByText('Responder')).toBeInTheDocument();
    expect(screen.getByText('45.5 seconds')).toBeInTheDocument();
    expect(screen.getByText('/tmp/config.json')).toBeInTheDocument();
    expect(screen.getByText('/tmp/storage')).toBeInTheDocument();
    expect(screen.getByText('https://example.com')).toBeInTheDocument();
    expect(screen.getAllByText('connected')).toHaveLength(2);
    expect(screen.getByText('Connected to LXMF server abc123')).toBeInTheDocument();
    const timestampMatches = screen.getAllByText('2025-09-23T12:34:56Z');
    expect(timestampMatches).toHaveLength(2);
    expect(screen.getByText('Mesh Neighbors • full • 125000 bps')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Mesh Neighbors • full • 125000 bps (online), WAN Link • access_point (offline)',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText('http://localhost:8000')).toBeInTheDocument();
    expect(screen.getByText('http://localhost:8000/notifications/stream')).toBeInTheDocument();
    expect(
      screen.queryByText((_, element) => element?.classList.contains('page-error') ?? false),
    ).not.toBeInTheDocument();
  });

  it('loads link destination settings into the form', async () => {
    vi.spyOn(apiClientModule.apiClient, 'get').mockResolvedValueOnce(buildGatewayInfoResponse());
    vi.spyOn(apiClientModule, 'getLinkDestinationSettings').mockResolvedValue(
      buildLinkDestinationSettings(),
    );

    render(<DashboardPage />);

    const input = await screen.findByLabelText(/server identity/i);
    expect(input).toHaveValue('abc123');
    expect(screen.getByText('/tmp/client_config.json')).toBeInTheDocument();
  });

  it('updates the link destination via the dashboard form', async () => {
    vi.spyOn(apiClientModule.apiClient, 'get').mockResolvedValueOnce(buildGatewayInfoResponse());
    vi.spyOn(apiClientModule, 'getLinkDestinationSettings').mockResolvedValue(
      buildLinkDestinationSettings(),
    );
    const updateSpy = vi
      .spyOn(apiClientModule, 'updateLinkDestination')
      .mockResolvedValue(
        buildLinkDestinationSettings({
          serverIdentity: 'b11f61896ee13a128488bf6687a03ce3',
          linkStatus: {
            state: 'connecting',
            message: 'Attempting to connect',
            serverIdentity: 'b11f61896ee13a128488bf6687a03ce3',
          },
        }),
      );

    render(<DashboardPage />);

    const user = userEvent.setup();
    const input = await screen.findByLabelText(/server identity/i);
    await user.clear(input);
    await user.type(input, 'B11F61896EE13A128488BF6687A03CE3');
    await user.click(screen.getByRole('button', { name: /save link destination/i }));

    expect(updateSpy).toHaveBeenCalledWith({
      serverIdentity: 'B11F61896EE13A128488BF6687A03CE3',
    });
    expect(await screen.findByText('Link destination saved.')).toBeInTheDocument();
  });

  it('clears the link destination when requested', async () => {
    vi.spyOn(apiClientModule.apiClient, 'get').mockResolvedValueOnce(buildGatewayInfoResponse());
    vi.spyOn(apiClientModule, 'getLinkDestinationSettings')
      .mockResolvedValueOnce(buildLinkDestinationSettings())
      .mockResolvedValueOnce(
        buildLinkDestinationSettings({
          serverIdentity: null,
          linkStatus: {
            state: 'unconfigured',
            message: 'Server identity hash not configured.',
          },
        }),
      );
    const deleteSpy = vi.spyOn(apiClientModule, 'deleteLinkDestination').mockResolvedValue();

    render(<DashboardPage />);
    const user = userEvent.setup();

    const clearButton = await screen.findByRole('button', { name: /clear/i });
    await user.click(clearButton);

    expect(deleteSpy).toHaveBeenCalled();
    expect(await screen.findByText('Link destination removed.')).toBeInTheDocument();
    expect(await screen.findByLabelText(/server identity/i)).toHaveValue('');
  });
});
