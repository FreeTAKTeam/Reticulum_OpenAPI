import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../lib/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../lib/apiClient')>();
  return {
    ...actual,
    listEvents: vi.fn(),
    createEvent: vi.fn(),
    updateEvent: vi.fn(),
    deleteEvent: vi.fn(),
    extractApiErrorMessage: vi.fn((error: unknown) => {
      if (error instanceof Error) {
        return error.message;
      }
      return 'error';
    }),
  };
});

import { ToastProvider } from '../../../components/toast';
import { emitGatewayUpdate } from '../../../lib/liveUpdates';
import { EventsPage } from '../EventsPage';
import { createEvent, deleteEvent, listEvents, updateEvent, type EventRecord } from '../../../lib/apiClient';

const listMock = vi.mocked(listEvents);
const createMock = vi.mocked(createEvent);
const updateMock = vi.mocked(updateEvent);
const deleteMock = vi.mocked(deleteEvent);

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <EventsPage />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe('EventsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('supports creating and updating events', async () => {
    const initialEvents: EventRecord[] = [
      { uid: 1, type: 'Initial', detail: 'Existing', how: 'Mesh' },
    ];
    listMock.mockResolvedValue(initialEvents);
    createMock.mockResolvedValue({ uid: 2, type: 'New', detail: 'Created' });
    updateMock.mockResolvedValue({ uid: 1, type: 'Initial', detail: 'Updated', how: 'Mesh' });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Initial')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText('UID'), '2');
    await user.type(screen.getByLabelText('Type'), 'New');
    await user.click(screen.getByRole('button', { name: 'Create event' }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledTimes(1);
    });
    expect(createMock.mock.calls[0][0]).toEqual(expect.objectContaining({ uid: 2 }));
    expect(screen.getAllByText('New').length).toBeGreaterThan(0);

    await user.click(screen.getAllByRole('button', { name: 'Edit' })[0]);
    const detailField = screen.getByLabelText('Detail');
    await user.clear(detailField);
    await user.type(detailField, 'Updated');
    await user.click(screen.getByRole('button', { name: 'Save event' }));

    await waitFor(() => {
      expect(updateMock).toHaveBeenCalledTimes(1);
    });
    expect(updateMock.mock.calls[0][0]).toEqual(
      expect.objectContaining({ uid: 1, detail: 'Updated' }),
    );
    expect(screen.getAllByText('Updated').length).toBeGreaterThan(0);
  });

  it('validates UID input', async () => {
    listMock.mockResolvedValue([]);

    renderPage();

    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: 'Create event' }));

    expect(await screen.findByText('UID must be a valid number.')).toBeInTheDocument();
    expect(createMock).not.toHaveBeenCalled();
  });

  it('confirms deletion of events', async () => {
    const event: EventRecord = { uid: 1, type: 'Initial' };
    listMock.mockResolvedValue([event]);
    deleteMock.mockResolvedValue({ status: 'deleted', uid: 1 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Initial')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => {
      expect(deleteMock).toHaveBeenCalledTimes(1);
    });
    expect(deleteMock.mock.calls[0][0]).toBe(1);
    confirmSpy.mockRestore();
  });

  it('refetches events when live updates arrive', async () => {
    listMock.mockResolvedValue([{ uid: 1, type: 'Initial' }]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Initial')).toBeInTheDocument();
    });

    listMock.mockResolvedValueOnce([
      { uid: 1, type: 'Initial' },
      { uid: 2, type: 'Follow-up' },
    ]);
    emitGatewayUpdate({ resource: 'event', action: 'created' });

    await waitFor(() => {
      expect(listMock).toHaveBeenCalledTimes(2);
      expect(screen.getByText('Follow-up')).toBeInTheDocument();
    });
  });
});
