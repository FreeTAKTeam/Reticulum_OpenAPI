import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { EmergencyActionMessage } from '../../../lib/apiClient';
import { MessagesTable } from '../MessagesTable';

function getCallsignOrder(): string[] {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => {
      const callsignElement = within(row).getByText((_, element) =>
        element?.classList.contains('callsign') ?? false,
      );
      return callsignElement.textContent?.trim() ?? '';
    });
}

describe('MessagesTable', () => {
  it('sorts messages by callsign and toggles direction', async () => {
    const messages: EmergencyActionMessage[] = [
      { callsign: 'Bravo', medicalStatus: 'Green' },
      { callsign: 'Alpha', medicalStatus: 'Yellow' },
      { callsign: 'Charlie', medicalStatus: 'Red' },
    ];

    render(
      <MessagesTable
        messages={messages}
        isLoading={false}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onCreateNew={vi.fn()}
      />,
    );

    expect(getCallsignOrder()).toEqual(['Alpha', 'Bravo', 'Charlie']);

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Sort by Callsign/i }));

    expect(getCallsignOrder()).toEqual(['Charlie', 'Bravo', 'Alpha']);
  });

  it('sorts messages by status severity', async () => {
    const messages: EmergencyActionMessage[] = [
      { callsign: 'Alpha', securityStatus: 'Red' },
      { callsign: 'Bravo', securityStatus: 'Green' },
      { callsign: 'Charlie', securityStatus: 'Yellow' },
    ];

    render(
      <MessagesTable
        messages={messages}
        isLoading={false}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onCreateNew={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Sort by Security/i }));

    expect(getCallsignOrder()).toEqual(['Bravo', 'Charlie', 'Alpha']);

    await user.click(screen.getByRole('button', { name: /Sort by Security/i }));

    expect(getCallsignOrder()).toEqual(['Alpha', 'Charlie', 'Bravo']);
  });
});
