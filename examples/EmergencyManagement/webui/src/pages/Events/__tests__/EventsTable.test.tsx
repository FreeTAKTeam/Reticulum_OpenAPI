import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { EventRecord } from '../../../lib/apiClient';
import { EventsTable } from '../EventsTable';

function getUidOrder(): number[] {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => {
      const [uidCell] = within(row).getAllByRole('cell');
      return Number(uidCell.textContent?.trim() ?? '0');
    });
}

describe('EventsTable', () => {
  it('sorts events by uid and toggles direction', async () => {
    const events: EventRecord[] = [
      { uid: 5 },
      { uid: 2 },
      { uid: 9 },
    ];

    render(
      <EventsTable
        events={events}
        isLoading={false}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onCreateNew={vi.fn()}
      />,
    );

    expect(getUidOrder()).toEqual([2, 5, 9]);

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Sort by UID/i }));

    expect(getUidOrder()).toEqual([9, 5, 2]);
  });

  it('sorts events by start time', async () => {
    const events: EventRecord[] = [
      { uid: 1, start: '2025-09-20T10:00:00Z' },
      { uid: 2, start: '2025-09-18T08:00:00Z' },
      { uid: 3, start: '2025-09-19T09:30:00Z' },
    ];

    render(
      <EventsTable
        events={events}
        isLoading={false}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onCreateNew={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Sort by Start/i }));

    expect(getUidOrder()).toEqual([2, 3, 1]);

    await user.click(screen.getByRole('button', { name: /Sort by Start/i }));

    expect(getUidOrder()).toEqual([1, 3, 2]);
  });
});
