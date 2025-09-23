import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  createEmergencyActionMessage,
  deleteEmergencyActionMessage,
  extractApiErrorMessage,
  listEmergencyActionMessages,
  updateEmergencyActionMessage,
  type EmergencyActionMessage,
} from '../../lib/apiClient';
import { useToast } from '../../components/toast';

import { DeleteMessageDialog } from './DeleteMessageDialog';
import { MessageDetails } from './MessageDetails';
import { MessageForm, type MessageFormMode } from './MessageForm';
import { MessagesTable } from './MessagesTable';

function cloneMessages(messages: EmergencyActionMessage[]): EmergencyActionMessage[] {
  return messages.map((message) => ({ ...message }));
}

export function EmergencyActionMessagesPage(): JSX.Element {
  const [messages, setMessages] = useState<EmergencyActionMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedCallsign, setSelectedCallsign] = useState<string | null>(null);
  const [formMode, setFormMode] = useState<MessageFormMode>('create');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState<boolean>(false);

  const { pushToast } = useToast();
  const messagesRef = useRef<EmergencyActionMessage[]>(messages);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const selectedMessage = useMemo(() => {
    return messages.find((message) => message.callsign === selectedCallsign) ?? null;
  }, [messages, selectedCallsign]);

  useEffect(() => {
    let isMounted = true;
    const fetchMessages = async () => {
      try {
        const items = await listEmergencyActionMessages();
        if (!isMounted) {
          return;
        }
        setMessages(items);
        setSelectedCallsign(items[0]?.callsign ?? null);
        setLoadError(null);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        const message = extractApiErrorMessage(error);
        setLoadError(message);
        pushToast({ type: 'error', message: `Failed to load messages: ${message}` });
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchMessages();
    return () => {
      isMounted = false;
    };
  }, [pushToast]);

  useEffect(() => {
    if (selectedMessage) {
      setFormMode('edit');
    } else {
      setFormMode('create');
    }
  }, [selectedMessage]);

  const handleSelectMessage = useCallback((callsign: string) => {
    setSelectedCallsign(callsign);
  }, []);

  const handleResetForm = useCallback(() => {
    setSelectedCallsign(null);
    setFormMode('create');
  }, []);

  const handleCreate = useCallback(
    async (message: EmergencyActionMessage) => {
      const previousMessages = cloneMessages(messagesRef.current);
      setIsSubmitting(true);
      pushToast({ type: 'info', message: `Saving message ${message.callsign}…` });
      setMessages((current) => {
        const hasExisting = current.some((item) => item.callsign === message.callsign);
        if (hasExisting) {
          return current.map((item) =>
            item.callsign === message.callsign ? { ...item, ...message } : item,
          );
        }
        return [...current, { ...message }];
      });
      setSelectedCallsign(message.callsign);

      try {
        const saved = await createEmergencyActionMessage(message);
        setMessages((current) =>
          current.map((item) =>
            item.callsign === saved.callsign ? { ...item, ...saved } : item,
          ),
        );
        pushToast({ type: 'success', message: `Gateway confirmed ${message.callsign}.` });
      } catch (error) {
        const errorMessage = extractApiErrorMessage(error);
        setMessages(previousMessages);
        const previousSelection = previousMessages.find(
          (item) => item.callsign === message.callsign,
        );
        setSelectedCallsign(previousSelection ? previousSelection.callsign : null);
        pushToast({
          type: 'error',
          message: `Failed to create ${message.callsign}: ${errorMessage}`,
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [pushToast],
  );

  const handleUpdate = useCallback(
    async (message: EmergencyActionMessage) => {
      const previousMessages = cloneMessages(messagesRef.current);
      setIsSubmitting(true);
      pushToast({ type: 'info', message: `Updating message ${message.callsign}…` });
      setMessages((current) =>
        current.map((item) =>
          item.callsign === message.callsign ? { ...item, ...message } : item,
        ),
      );

      try {
        const updated = await updateEmergencyActionMessage(message);
        if (!updated) {
          setMessages(previousMessages);
          pushToast({
            type: 'error',
            message: `${message.callsign} no longer exists on the server.`,
          });
          return;
        }
        setMessages((current) =>
          current.map((item) =>
            item.callsign === updated.callsign ? { ...item, ...updated } : item,
          ),
        );
        pushToast({ type: 'success', message: `Gateway updated ${message.callsign}.` });
      } catch (error) {
        const errorMessage = extractApiErrorMessage(error);
        setMessages(previousMessages);
        pushToast({
          type: 'error',
          message: `Failed to update ${message.callsign}: ${errorMessage}`,
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [pushToast],
  );

  const handleSubmit = useCallback(
    async (message: EmergencyActionMessage) => {
      if (formMode === 'edit') {
        await handleUpdate(message);
      } else {
        await handleCreate(message);
      }
    },
    [formMode, handleCreate, handleUpdate],
  );

  const handleDelete = useCallback(() => {
    if (!selectedMessage) {
      return;
    }
    setDeleteDialogOpen(true);
  }, [selectedMessage]);

  const handleConfirmDelete = useCallback(async () => {
    if (!selectedMessage) {
      return;
    }
    const target = selectedMessage;
    const previousMessages = cloneMessages(messagesRef.current);
    setDeleteDialogOpen(false);
    setMessages((current) => current.filter((item) => item.callsign !== target.callsign));
    setSelectedCallsign(null);
    pushToast({ type: 'info', message: `Deleting ${target.callsign}…` });

    try {
      await deleteEmergencyActionMessage(target.callsign);
      pushToast({ type: 'success', message: `Deleted ${target.callsign}.` });
    } catch (error) {
      const errorMessage = extractApiErrorMessage(error);
      setMessages(previousMessages);
      setSelectedCallsign(target.callsign);
      pushToast({
        type: 'error',
        message: `Failed to delete ${target.callsign}: ${errorMessage}`,
      });
    }
  }, [pushToast, selectedMessage]);

  return (
    <section className="page-section">
      <header className="page-header">
        <h2>Emergency Action Messages</h2>
        <p>
          Review and dispatch emergency action messages across the mesh network.
        </p>
      </header>
      <div className="page-card">
        <p>
          Manage emergency action message readiness, update unit statuses, and coordinate
          communications through the FastAPI gateway.
        </p>
      </div>
      {loading ? (
        <div className="page-card">Loading messages…</div>
      ) : loadError ? (
        <div className="page-card page-error">{loadError}</div>
      ) : (
        <div className="page-grid">
          <div className="page-card">
            <MessagesTable
              messages={messages}
              selectedCallsign={selectedCallsign}
              onSelect={handleSelectMessage}
            />
          </div>
          <div className="page-card">
            <MessageDetails
              message={selectedMessage}
              onEdit={() => setFormMode('edit')}
              onDelete={handleDelete}
            />
          </div>
          <div className="page-card">
            <MessageForm
              mode={formMode}
              initialValue={formMode === 'edit' ? selectedMessage : null}
              onSubmit={handleSubmit}
              onReset={handleResetForm}
              isSubmitting={isSubmitting}
            />
          </div>
        </div>
      )}
      <DeleteMessageDialog
        callsign={selectedMessage?.callsign ?? null}
        isOpen={deleteDialogOpen}
        onCancel={() => setDeleteDialogOpen(false)}
        onConfirm={handleConfirmDelete}
      />
    </section>
  );
}
