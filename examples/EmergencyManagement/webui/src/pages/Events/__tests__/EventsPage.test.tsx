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

function toLocalInput(value: string): string {
  const parsed = new Date(value);
  const pad = (input: number) => input.toString().padStart(2, '0');
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}T${pad(parsed.getHours())}:${pad(
    parsed.getMinutes(),
  )}`;
}

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
      {
        uid: 1,
        type: 'Initial',
        how: 'Mesh',
        detail: {
          emergencyActionMessage: {
            callsign: 'Alpha',
            groupName: 'Team One',
            securityStatus: 'Yellow',
            medicalStatus: 'Green',
            commsMethod: 'Mesh',
          },
        },
      },
    ];
    listMock.mockResolvedValue(initialEvents);
    createMock.mockResolvedValue({
      uid: 2,
      type: 'New',
      detail: {
        emergencyActionMessage: {
          callsign: 'Bravo',
          groupName: 'Rescue',
          securityStatus: 'Green',
          commsStatus: 'Yellow',
          commsMethod: 'VHF',
        },
      },
    });
    updateMock.mockResolvedValue({
      uid: 1,
      type: 'Initial',
      how: 'Mesh',
      detail: {
        emergencyActionMessage: {
          callsign: 'Alpha',
          groupName: 'Updated Team',
          securityStatus: 'Red',
          medicalStatus: 'Green',
          commsMethod: 'Mesh',
        },
      },
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Initial')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'New' }));
    await user.type(screen.getByLabelText('UID'), '2');
    await user.type(screen.getByLabelText('Type'), 'New');
    await user.type(screen.getByLabelText('Start'), '2025-09-19T10:30');
    await user.type(screen.getByLabelText('Stale'), '2025-09-20T11:00');
    await user.selectOptions(screen.getByLabelText('Access'), 'Restricted');
    await user.click(screen.getByLabelText('Include emergency action message detail'));
    await user.type(screen.getByLabelText('EAM Callsign'), 'Bravo');
    await user.type(screen.getByLabelText('EAM Group name'), 'Rescue');
    await user.selectOptions(screen.getByLabelText('Security status'), 'Green');
    await user.selectOptions(screen.getByLabelText('Comms status'), 'Yellow');
    await user.type(screen.getByLabelText('Comms method'), 'VHF');
    await user.click(screen.getByRole('button', { name: 'Create event' }));

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledTimes(1);
    });
    const expectedStart = new Date('2025-09-19T10:30').toISOString();
    const expectedStale = new Date('2025-09-20T11:00').toISOString();
    expect(createMock.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        uid: 2,
        start: expectedStart,
        stale: expectedStale,
        access: 'Restricted',
        detail: {
          emergencyActionMessage: expect.objectContaining({
            callsign: 'Bravo',
            groupName: 'Rescue',
            securityStatus: 'Green',
            commsStatus: 'Yellow',
            commsMethod: 'VHF',
          }),
        },
      }),
    );
    expect(await screen.findByText('Method: VHF')).toBeInTheDocument();

    await user.click(screen.getAllByRole('button', { name: 'Edit' })[0]);
    const callsignToggle = screen.getByLabelText('Include emergency action message detail');
    expect(callsignToggle).toBeChecked();
    const groupField = screen.getByLabelText('EAM Group name');
    await user.clear(groupField);
    await user.type(groupField, 'Updated Team');
    await user.selectOptions(screen.getByLabelText('Security status'), 'Red');
    await user.click(screen.getByRole('button', { name: 'Save event' }));

    await waitFor(() => {
      expect(updateMock).toHaveBeenCalledTimes(1);
    });
    expect(updateMock.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        uid: 1,
        detail: {
          emergencyActionMessage: expect.objectContaining({
            callsign: 'Alpha',
            groupName: 'Updated Team',
            securityStatus: 'Red',
            medicalStatus: 'Green',
            commsMethod: 'Mesh',
          }),
        },
      }),
    );
    expect(await screen.findByText(/Updated Team/)).toBeInTheDocument();
    expect(await screen.findByText('Security: Red')).toBeInTheDocument();
  });

  it('validates UID input', async () => {
    listMock.mockResolvedValue([]);

    renderPage();

    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: 'New' }));
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

  it('prefills date/time and access inputs when editing an event', async () => {
    const startIso = '2025-05-01T09:15:00.000Z';
    const staleIso = '2025-05-02T10:30:00.000Z';
    listMock.mockResolvedValue([
      {
        uid: 5,
        type: 'Drill',
        start: startIso,
        stale: staleIso,
        access: 'Public',
        detail: {
          emergencyActionMessage: {
            callsign: 'Delta',
            groupName: 'Logistics',
            securityStatus: 'Green',
            commsMethod: 'HF',
          },
        },
      },
    ]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Drill')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Edit' }));

    expect(screen.getByLabelText('Start')).toHaveValue(toLocalInput(startIso));
    expect(screen.getByLabelText('Stale')).toHaveValue(toLocalInput(staleIso));
    expect(screen.getByLabelText('Access')).toHaveValue('Public');
    const detailToggle = screen.getByLabelText('Include emergency action message detail');
    expect(detailToggle).toBeChecked();
    expect(screen.getByLabelText('EAM Callsign')).toHaveValue('Delta');
    expect(screen.getByLabelText('EAM Group name')).toHaveValue('Logistics');
    expect(screen.getByLabelText('Security status')).toHaveValue('Green');
    expect(screen.getByLabelText('Comms method')).toHaveValue('HF');
  });
});
