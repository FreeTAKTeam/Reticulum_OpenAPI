import { useCallback, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useToast } from '../../components/toast';
import {
  createEvent,
  deleteEvent,
  extractApiErrorMessage,
  listEvents,
  updateEvent,
  type EventRecord,
} from '../../lib/apiClient';
import { useGatewayLiveUpdates } from '../../lib/liveUpdates';

import { EventForm } from './EventForm';
import { EventsTable } from './EventsTable';

const QUERY_KEY = ['events'];

export function EventsPage(): JSX.Element {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [editingEvent, setEditingEvent] = useState<EventRecord | null>(null);
  const [isFormVisible, setFormVisible] = useState(false);

  const handleCloseForm = useCallback(() => {
    setEditingEvent(null);
    setFormVisible(false);
  }, []);

  const eventsQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: listEvents,
  });

  const handleLiveUpdate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEY });
  }, [queryClient]);

  useGatewayLiveUpdates('event', handleLiveUpdate);

  const events = useMemo(() => [...(eventsQuery.data ?? [])].sort((a, b) => a.uid - b.uid), [
    eventsQuery.data,
  ]);

  const createMutation = useMutation({
    mutationFn: createEvent,
    onSuccess: (created) => {
      queryClient.setQueryData<EventRecord[]>(QUERY_KEY, (current) => {
        const events = current ?? [];
        const filtered = events.filter((item) => item.uid !== created.uid);
        return [...filtered, created].sort((a, b) => a.uid - b.uid);
      });
      pushToast({ type: 'success', message: `Created event ${created.uid}.` });
      handleCloseForm();
    },
    onError: (error, variables) => {
      pushToast({
        type: 'error',
        message: `Failed to create event ${variables.uid}: ${extractApiErrorMessage(error)}`,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: updateEvent,
    onSuccess: (updated, variables) => {
      if (!updated) {
        pushToast({
          type: 'error',
          message: `Event ${variables.uid} is no longer available on the gateway.`,
        });
        queryClient.invalidateQueries({ queryKey: QUERY_KEY });
        return;
      }
      queryClient.setQueryData<EventRecord[]>(QUERY_KEY, (current) => {
        const events = current ?? [];
        return events
          .map((item) => (item.uid === updated.uid ? updated : item))
          .sort((a, b) => a.uid - b.uid);
      });
      pushToast({ type: 'success', message: `Updated event ${updated.uid}.` });
      handleCloseForm();
    },
    onError: (error, variables) => {
      pushToast({
        type: 'error',
        message: `Failed to update event ${variables.uid}: ${extractApiErrorMessage(error)}`,
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteEvent,
    onSuccess: (_response, uid) => {
      queryClient.setQueryData<EventRecord[]>(QUERY_KEY, (current) =>
        (current ?? []).filter((item) => item.uid !== Number(uid)),
      );
      pushToast({ type: 'success', message: `Deleted event ${uid}.` });
      if (editingEvent?.uid === Number(uid)) {
        handleCloseForm();
      }
    },
    onError: (error, uid) => {
      pushToast({
        type: 'error',
        message: `Failed to delete event ${uid}: ${extractApiErrorMessage(error)}`,
      });
    },
  });

  const handleSubmit = useCallback(
    (event: EventRecord) => {
      if (editingEvent && editingEvent.uid === event.uid) {
        updateMutation.mutate(event);
      } else {
        createMutation.mutate(event);
      }
    },
    [createMutation, updateMutation, editingEvent],
  );

  const handleEdit = useCallback((event: EventRecord) => {
    setEditingEvent(event);
    setFormVisible(true);
  }, []);

  const handleDelete = useCallback(
    (event: EventRecord) => {
      const confirmed = window.confirm(`Delete event ${event.uid}?`);
      if (confirmed) {
        deleteMutation.mutate(event.uid);
      }
    },
    [deleteMutation],
  );

  const handleCreateNew = useCallback(() => {
    setEditingEvent(null);
    setFormVisible(true);
  }, []);

  return (
    <section className="page-section">
      <header className="page-header">
        <h2>Events</h2>
        <p>Track operational events and dispatch notes as they arrive from the mesh.</p>
      </header>

      <div className="page-grid">
        <EventsTable
          events={events}
          isLoading={eventsQuery.isFetching && !eventsQuery.isFetched}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onCreateNew={handleCreateNew}
        />
      </div>
      {isFormVisible && (
        <div className="form-drawer" role="dialog" aria-modal="true" aria-label="Event form">
          <button
            type="button"
            className="form-drawer__backdrop"
            aria-label="Close"
            onClick={handleCloseForm}
          />
          <div className="form-drawer__panel">
            <EventForm
              initialValue={editingEvent}
              onSubmit={handleSubmit}
              onCancelEdit={handleCloseForm}
              isSubmitting={createMutation.isPending || updateMutation.isPending}
            />
          </div>
        </div>
      )}
    </section>
  );
}
