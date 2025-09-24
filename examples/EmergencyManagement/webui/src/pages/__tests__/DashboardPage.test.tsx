import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

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
});
