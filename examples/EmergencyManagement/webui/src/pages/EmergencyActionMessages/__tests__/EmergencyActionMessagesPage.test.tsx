import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../lib/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../lib/apiClient')>();
  return {
    ...actual,
    listEmergencyActionMessages: vi.fn(),
    createEmergencyActionMessage: vi.fn(),
    updateEmergencyActionMessage: vi.fn(),
    deleteEmergencyActionMessage: vi.fn(),
    extractApiErrorMessage: vi.fn((error: unknown) => {
      if (error instanceof Error) {
        return error.message;
      }
      return 'error';
    }),
  };
});

import { ToastProvider } from '../../../components/toast';
import { EmergencyActionMessagesPage } from '../EmergencyActionMessagesPage';
import {
  createEmergencyActionMessage,
  deleteEmergencyActionMessage,
  listEmergencyActionMessages,
  updateEmergencyActionMessage,
  type EmergencyActionMessage,
} from '../../../lib/apiClient';

const listMock = vi.mocked(listEmergencyActionMessages);
const createMock = vi.mocked(createEmergencyActionMessage);
const updateMock = vi.mocked(updateEmergencyActionMessage);
const deleteMock = vi.mocked(deleteEmergencyActionMessage);

function renderPage(): void {
  render(
    <ToastProvider>
      <EmergencyActionMessagesPage />
    </ToastProvider>,
  );
}

describe('EmergencyActionMessagesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders messages and supports creating and updating records', async () => {
    const initialMessages: EmergencyActionMessage[] = [
      {
        callsign: 'Alpha-1',
        groupName: 'Alpha',
        securityStatus: 'Green',
      },
      {
        callsign: 'Bravo-2',
        groupName: 'Bravo',
        securityStatus: 'Yellow',
      },
    ];
    listMock.mockResolvedValue(initialMessages);
    createMock.mockResolvedValue({
      callsign: 'Charlie-3',
      groupName: 'Charlie',
      securityStatus: 'Red',
    });
    updateMock.mockResolvedValue({
      callsign: 'Alpha-1',
      groupName: 'Alpha Updated',
      securityStatus: 'Green',
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Alpha-1').length).toBeGreaterThan(0);
      expect(screen.getByText('Bravo-2')).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'New message' }));
    const createButton = await screen.findByRole('button', { name: 'Create message' });
    await user.type(screen.getByLabelText('Callsign'), 'Charlie-3');
    await user.type(screen.getByLabelText('Group name'), 'Charlie');
    await user.selectOptions(screen.getByLabelText('Security Status'), 'Red');
    await user.click(createButton);

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledTimes(1);
    });
    expect(createMock).toHaveBeenCalledWith(
      expect.objectContaining({ callsign: 'Charlie-3', securityStatus: 'Red' }),
    );
    expect(screen.getAllByText('Charlie-3').length).toBeGreaterThan(0);

    await user.click(screen.getByText('Alpha-1'));
    const groupInput = screen.getByLabelText('Group name');
    await user.clear(groupInput);
    await user.type(groupInput, 'Alpha Updated');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() => {
      expect(updateMock).toHaveBeenCalledTimes(1);
    });
    expect(updateMock).toHaveBeenCalledWith(
      expect.objectContaining({ callsign: 'Alpha-1', groupName: 'Alpha Updated' }),
    );
    expect(screen.getAllByText('Alpha Updated').length).toBeGreaterThan(0);
  });

  it('shows validation errors when required fields are missing', async () => {
    listMock.mockResolvedValue([]);

    renderPage();

    const user = userEvent.setup();
    const submitButton = await screen.findByRole('button', { name: 'Create message' });
    await user.click(submitButton);

    expect(await screen.findByText('Callsign is required.')).toBeInTheDocument();
    expect(createMock).not.toHaveBeenCalled();
  });

  it('confirms deletion before removing a message', async () => {
    const message: EmergencyActionMessage = {
      callsign: 'Alpha-1',
      groupName: 'Alpha',
      securityStatus: 'Green',
    };
    listMock.mockResolvedValue([message]);
    deleteMock.mockResolvedValue({ status: 'deleted', callsign: 'Alpha-1' });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Alpha-1').length).toBeGreaterThan(0);
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    const dialog = await screen.findByRole('dialog');
    expect(
      within(dialog).getByText((content) =>
        content.includes('Are you sure you want to delete the message for'),
      ),
    ).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    await waitFor(() => {
      expect(deleteMock).toHaveBeenCalledWith('Alpha-1');
      expect(screen.queryByText('Alpha-1')).not.toBeInTheDocument();
    });
  });
});
