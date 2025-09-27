import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { type AddressInfo } from 'node:net';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { type EventRecord } from '../apiClient';

function readJsonBody(request: IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    let body = '';
    request.setEncoding('utf8');
    request.on('data', (chunk: string) => {
      body += chunk;
    });
    request.on('error', (error) => {
      reject(error);
    });
    request.on('end', () => {
      if (!body) {
        resolve(null);
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch (error) {
        reject(error);
      }
    });
  });
}

function sendJson(response: ServerResponse, status: number, payload: unknown): void {
  response.statusCode = status;
  response.setHeader('Content-Type', 'application/json');
  response.setHeader('Access-Control-Allow-Origin', '*');
  response.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Server-Identity');
  response.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  response.end(JSON.stringify(payload));
}

interface RequestLogEntry {
  method: string;
  path: string;
  identity?: string;
}

describe('apiClient HTTP integration', () => {
  let server = createServer();
  let baseUrl = '';
  let requests: RequestLogEntry[] = [];
  let messages = new Map<string, Record<string, unknown>>();
  let events = new Map<string, Record<string, unknown>>();

  beforeEach(async () => {
    vi.resetModules();
    vi.unstubAllEnvs();

    messages = new Map();
    events = new Map();
    requests = [];

    server = createServer((request, response) => {
      const handle = async () => {
        const identityHeader = request.headers['x-server-identity'];
        const url = new URL(request.url ?? '/', baseUrl || 'http://127.0.0.1');
        const method = request.method ?? 'GET';

        const identity = Array.isArray(identityHeader)
          ? identityHeader[0]
          : typeof identityHeader === 'string'
            ? identityHeader
            : undefined;
        requests.push({ method, path: url.pathname, identity });

        if (method === 'OPTIONS') {
          response.statusCode = 204;
          response.setHeader('Access-Control-Allow-Origin', '*');
          response.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Server-Identity');
          response.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
          response.end();
          return;
        }

        if (method === 'POST' && url.pathname === '/emergency-action-messages') {
          const body = (await readJsonBody(request)) as Record<string, unknown>;
          const callsign = `${body.callsign ?? ''}`;
          messages.set(callsign, body);
          sendJson(response, 200, body);
          return;
        }

        if (method === 'GET' && url.pathname === '/emergency-action-messages') {
          sendJson(response, 200, Array.from(messages.values()));
          return;
        }

        if (method === 'GET' && url.pathname.startsWith('/emergency-action-messages/')) {
          const segments = url.pathname.split('/').filter(Boolean);
          const callsign = segments[1] ?? '';
          sendJson(response, 200, messages.get(callsign) ?? null);
          return;
        }

        if (method === 'POST' && url.pathname === '/events') {
          const body = (await readJsonBody(request)) as Record<string, unknown>;
          const uid = `${body.uid ?? ''}`;
          events.set(uid, body);
          sendJson(response, 200, body);
          return;
        }

        if (method === 'GET' && url.pathname === '/events') {
          sendJson(response, 200, Array.from(events.values()));
          return;
        }

        if (method === 'GET' && url.pathname.startsWith('/events/')) {
          const segments = url.pathname.split('/').filter(Boolean);
          const uid = segments[1] ?? '';
          sendJson(response, 200, events.get(uid) ?? null);
          return;
        }

        sendJson(response, 404, { detail: 'Not found' });
      };

      handle().catch((error) => {
        sendJson(response, 500, { error: error instanceof Error ? error.message : String(error) });
      });
    });

    await new Promise<void>((resolve) => {
      server.listen(0, '127.0.0.1', () => {
        resolve();
      });
    });

    const address = server.address();
    if (!address || typeof address === 'string') {
      throw new Error('Failed to determine server address');
    }

    baseUrl = `http://127.0.0.1:${(address as AddressInfo).port}`;
    vi.stubEnv('VITE_API_BASE_URL', baseUrl);
    vi.stubEnv('VITE_SERVER_IDENTITY', 'AA55');
  });

  afterEach(async () => {
    await new Promise<void>((resolve) => {
      server.close(() => {
        resolve();
      });
    });
    vi.unstubAllEnvs();
  });

  it('posts and retrieves emergency action messages via HTTP', async () => {
    const {
      createEmergencyActionMessage,
      listEmergencyActionMessages,
      retrieveEmergencyActionMessage,
    } = await import('../apiClient');

    const message = {
      callsign: 'ALPHA1',
      groupName: 'Alpha Team',
      commsMethod: 'HF',
    };

    const created = await createEmergencyActionMessage(message);
    expect(created).toMatchObject(message);

    const allMessages = await listEmergencyActionMessages();
    expect(allMessages).toHaveLength(1);
    expect(allMessages[0]).toMatchObject(message);

    const retrieved = await retrieveEmergencyActionMessage(message.callsign);
    expect(retrieved).toMatchObject(message);

    const authenticatedRequests = requests.filter((entry) => entry.method !== 'OPTIONS');
    expect(authenticatedRequests).toHaveLength(3);
    expect(authenticatedRequests.every((entry) => entry.identity === 'AA55')).toBe(true);
  });

  it('posts and retrieves events via HTTP', async () => {
    const { createEvent, listEvents, retrieveEvent } = await import('../apiClient');

    const event: EventRecord = {
      uid: 42,
      type: 'drill',
      detail: {
        emergencyActionMessage: {
          callsign: 'BRAVO2',
          securityStatus: 'Yellow',
        },
      },
      access: 'orange',
      start: '2025-09-25T08:15:00Z',
    };

    const created = await createEvent(event);
    expect(created).toMatchObject({ uid: 42, type: 'drill' });

    const allEvents = await listEvents();
    expect(allEvents).toHaveLength(1);
    expect(allEvents[0]).toMatchObject({ uid: 42, type: 'drill' });

    const retrieved = await retrieveEvent(event.uid);
    expect(retrieved).toMatchObject({ uid: 42, type: 'drill' });

    const authenticatedRequests = requests.filter((entry) => entry.method !== 'OPTIONS');
    expect(authenticatedRequests).toHaveLength(3);
    expect(authenticatedRequests.every((entry) => entry.identity === 'AA55')).toBe(true);
  });
});
