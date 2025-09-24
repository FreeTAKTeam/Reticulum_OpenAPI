import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AxiosResponse } from 'axios';

import * as apiClientModule from '../../lib/apiClient';
import { DashboardPage } from '../DashboardPage';

describe('DashboardPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders backend error message when loading gateway info fails', async () => {
    const backendMessage = 'Gateway temporarily offline';
    const error = new Error('503 Service Unavailable');
    vi.spyOn(apiClientModule.apiClient, 'get').mockRejectedValueOnce(error);
    const extractSpy = vi
      .spyOn(apiClientModule, 'extractApiErrorMessage')
      .mockReturnValue(backendMessage);

    render(<DashboardPage />);

    expect(await screen.findByText(backendMessage)).toBeInTheDocument();
    expect(extractSpy).toHaveBeenCalledWith(error);
  });

  it('clears dashboard errors after successfully loading gateway info', async () => {
    const gatewayInfoResponse = {
      data: { version: '1.2.3', uptime: '4 hours' },
    } as AxiosResponse<{ version: string; uptime: string }>;
    vi.spyOn(apiClientModule.apiClient, 'get').mockResolvedValueOnce(gatewayInfoResponse);

    render(<DashboardPage />);

    expect(await screen.findByText('1.2.3')).toBeInTheDocument();
    expect(screen.getByText('4 hours')).toBeInTheDocument();
    expect(
      screen.queryByText((_, element) => element?.classList.contains('page-error') ?? false),
    ).not.toBeInTheDocument();
  });
});
