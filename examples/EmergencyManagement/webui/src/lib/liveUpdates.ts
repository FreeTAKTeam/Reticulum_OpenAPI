import { useEffect } from 'react';

import type { EmergencyActionMessage, EventRecord } from './apiClient';
import { getLiveUpdatesUrl } from './apiClient';

export type GatewayResource = 'emergency-action-message' | 'event';

export type GatewayUpdateAction = 'created' | 'updated' | 'deleted' | 'synced';

export interface GatewayUpdate<T = unknown> {
  resource: GatewayResource;
  action: GatewayUpdateAction;
  data?: T;
}

type Listener = (update: GatewayUpdate) => void;

interface EventSourceLike {
  close(): void;
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void;
  removeEventListener(type: string, listener: (event: MessageEvent<string>) => void): void;
}

class GatewayEventBus {
  private listeners: Set<Listener> = new Set();

  private eventSource: EventSourceLike | null = null;

  private readonly messageHandler = (event: MessageEvent<string>): void => {
    const update = this.parseUpdate(event.data);
    if (!update) {
      return;
    }
    this.emit(update);
  };

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    if (this.listeners.size === 1) {
      this.connect();
    }
    return () => {
      this.listeners.delete(listener);
      if (this.listeners.size === 0) {
        this.disconnect();
      }
    };
  }

  emit(update: GatewayUpdate): void {
    for (const listener of this.listeners) {
      listener(update);
    }
  }

  private connect(): void {
    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
      return;
    }
    if (this.eventSource) {
      return;
    }
    try {
      const eventSource = new window.EventSource(getLiveUpdatesUrl());
      eventSource.addEventListener('message', this.messageHandler as never);
      eventSource.addEventListener('error', () => {
        // Reason: FastAPI may recycle idle SSE connections. Attempt to reconnect automatically.
        this.disconnect();
        window.setTimeout(() => {
          if (this.listeners.size > 0) {
            this.connect();
          }
        }, 2000);
      });
      this.eventSource = eventSource;
    } catch (error) {
      // Reason: Some browsers may block EventSource for mixed-content or CORS issues.
      console.warn('Unable to initialise live updates stream', error);
    }
  }

  private disconnect(): void {
    if (!this.eventSource) {
      return;
    }
    this.eventSource.removeEventListener('message', this.messageHandler as never);
    this.eventSource.close();
    this.eventSource = null;
  }

  private parseUpdate(rawData: string): GatewayUpdate | null {
    try {
      const parsed = JSON.parse(rawData) as Record<string, unknown>;
      const resourceValue = this.normaliseResource(parsed);
      if (!resourceValue) {
        return null;
      }
      const actionValue = this.normaliseAction(parsed) ?? 'updated';
      const data = (parsed['payload'] ?? parsed['data'] ?? parsed['record'] ?? parsed['message'] ?? parsed['body']) as
        | EmergencyActionMessage
        | EventRecord
        | undefined;
      return {
        resource: resourceValue,
        action: actionValue,
        data,
      };
    } catch (error) {
      console.warn('Unable to parse live update payload', error);
      return null;
    }
  }

  private normaliseResource(parsed: Record<string, unknown>): GatewayResource | null {
    const candidate = this.extractString(parsed, ['resource', 'resourceType', 'type']);
    if (!candidate) {
      return null;
    }
    const normalised = candidate.toLowerCase();
    if (normalised.includes('message')) {
      return 'emergency-action-message';
    }
    if (normalised.includes('event')) {
      return 'event';
    }
    return null;
  }

  private normaliseAction(parsed: Record<string, unknown>): GatewayUpdateAction | null {
    const candidate = this.extractString(parsed, ['action', 'event', 'operation']);
    if (!candidate) {
      return null;
    }
    const normalised = candidate.toLowerCase();
    if (normalised.includes('create')) {
      return 'created';
    }
    if (normalised.includes('delete')) {
      return 'deleted';
    }
    if (normalised.includes('sync')) {
      return 'synced';
    }
    return 'updated';
  }

  private extractString(parsed: Record<string, unknown>, keys: string[]): string | null {
    for (const key of keys) {
      const value = parsed[key];
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
    }
    return null;
  }
}

const bus = new GatewayEventBus();

export function subscribeToGatewayUpdates(listener: Listener): () => void {
  return bus.subscribe(listener);
}

export function emitGatewayUpdate(update: GatewayUpdate): void {
  bus.emit(update);
}

export function useGatewayLiveUpdates(
  resource: GatewayResource,
  listener: (update: GatewayUpdate) => void,
): void {
  useEffect(() => {
    return subscribeToGatewayUpdates((update) => {
      if (update.resource === resource) {
        listener(update);
      }
    });
  }, [resource, listener]);
}
