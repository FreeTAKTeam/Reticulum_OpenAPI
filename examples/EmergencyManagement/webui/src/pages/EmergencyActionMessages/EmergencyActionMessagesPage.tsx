import { useCallback, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useToast } from '../../components/toast';
import {
  createEmergencyActionMessage,
  deleteEmergencyActionMessage,
  extractApiErrorMessage,
  listEmergencyActionMessages,
  updateEmergencyActionMessage,
  type EmergencyActionMessage,
} from '../../lib/apiClient';
import { useGatewayLiveUpdates } from '../../lib/liveUpdates';

import { MessageForm } from './MessageForm';
import { MessagesTable } from './MessagesTable';

const QUERY_KEY = ['emergency-action-messages'];

function sortMessages(messages: EmergencyActionMessage[]): EmergencyActionMessage[] {
  return [...messages].sort((a, b) => a.callsign.localeCompare(b.callsign));
}

export function EmergencyActionMessagesPage(): JSX.Element {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [editingMessage, setEditingMessage] = useState<EmergencyActionMessage | null>(null);

  const messagesQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: listEmergencyActionMessages,
  });

  const handleLiveUpdate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEY });
  }, [queryClient]);

  useGatewayLiveUpdates('emergency-action-message', handleLiveUpdate);

  const messages = useMemo(() => sortMessages(messagesQuery.data ?? []), [messagesQuery.data]);

  const createMutation = useMutation({
    mutationFn: createEmergencyActionMessage,
    onSuccess: (created) => {
      queryClient.setQueryData<EmergencyActionMessage[]>(QUERY_KEY, (current) => {
        const messages = current ?? [];
        const filtered = messages.filter((item) => item.callsign !== created.callsign);
        return sortMessages([...filtered, created]);
      });
      pushToast({ type: 'success', message: `Created ${created.callsign}.` });
      setEditingMessage(null);
    },
    onError: (error, variables) => {
      pushToast({
        type: 'error',
        message: `Failed to create ${variables.callsign}: ${extractApiErrorMessage(error)}`,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: updateEmergencyActionMessage,
    onSuccess: (updated, variables) => {
      if (!updated) {
        pushToast({
          type: 'error',
          message: `${variables.callsign} no longer exists on the gateway.`,
        });
        queryClient.invalidateQueries({ queryKey: QUERY_KEY });
        return;
      }
      queryClient.setQueryData<EmergencyActionMessage[]>(QUERY_KEY, (current) => {
        const messages = current ?? [];
        return sortMessages(
          messages.map((item) => (item.callsign === updated.callsign ? updated : item)),
        );
      });
      pushToast({ type: 'success', message: `Updated ${updated.callsign}.` });
      setEditingMessage(null);
    },
    onError: (error, variables) => {
      pushToast({
        type: 'error',
        message: `Failed to update ${variables.callsign}: ${extractApiErrorMessage(error)}`,
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteEmergencyActionMessage,
    onSuccess: (_response, callsign) => {
      queryClient.setQueryData<EmergencyActionMessage[]>(QUERY_KEY, (current) =>
        (current ?? []).filter((item) => item.callsign !== callsign),
      );
      pushToast({ type: 'success', message: `Deleted ${callsign}.` });
      if (editingMessage?.callsign === callsign) {
        setEditingMessage(null);
      }
    },
    onError: (error, callsign) => {
      pushToast({
        type: 'error',
        message: `Failed to delete ${callsign}: ${extractApiErrorMessage(error)}`,
      });
    },
  });

  const handleSubmit = useCallback(
    (message: EmergencyActionMessage) => {
      if (editingMessage && editingMessage.callsign === message.callsign) {
        updateMutation.mutate(message);
      } else {
        createMutation.mutate(message);
      }
    },
    [createMutation, updateMutation, editingMessage],
  );

  const handleEdit = useCallback((message: EmergencyActionMessage) => {
    setEditingMessage(message);
  }, []);

  const handleDelete = useCallback(
    (message: EmergencyActionMessage) => {
      const confirmed = window.confirm(
        `Delete emergency action message for ${message.callsign}?`,
      );
      if (confirmed) {
        deleteMutation.mutate(message.callsign);
      }
    },
    [deleteMutation],
  );

  return (
    <section className="page-section">
      <header className="page-header">
        <h2>Emergency Action Messages</h2>
        <p>Coordinate readiness across the mesh with live status and dispatch updates.</p>
      </header>

      <div className="page-grid">
        <MessagesTable
          messages={messages}
          isLoading={messagesQuery.isFetching && !messagesQuery.isFetched}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
        <MessageForm
          initialValue={editingMessage}
          onSubmit={handleSubmit}
          onCancelEdit={() => setEditingMessage(null)}
          isSubmitting={createMutation.isPending || updateMutation.isPending}
        />
      </div>
    </section>
  );
}
