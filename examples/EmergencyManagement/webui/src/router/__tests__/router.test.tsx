import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/apiClient')>();
  return {
    ...actual,
    listEmergencyActionMessages: vi.fn(),
  };
});

import { ToastProvider } from '../../components/toast';
import { listEmergencyActionMessages } from '../../lib/apiClient';
import { routes } from '../index';

const listMock = vi.mocked(listEmergencyActionMessages);

describe('router', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('redirects the root path to the emergency action messages list', async () => {
    listMock.mockResolvedValue([
      { callsign: 'Alpha-1', securityStatus: 'Green' },
      { callsign: 'Bravo-2', securityStatus: 'Yellow' },
    ]);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    const router = createMemoryRouter(routes, { initialEntries: ['/'] });

    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Emergency Action Messages' })).toBeInTheDocument();
      expect(screen.getByText('Alpha-1')).toBeInTheDocument();
      expect(screen.getByText('Bravo-2')).toBeInTheDocument();
    });
  });
});
