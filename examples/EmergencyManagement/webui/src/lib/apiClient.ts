import axios, { AxiosError } from 'axios';

export type EAMStatus = 'Red' | 'Yellow' | 'Green';

export interface EmergencyActionMessage {
  callsign: string;
  groupName?: string | null;
  securityStatus?: EAMStatus | null;
  securityCapability?: EAMStatus | null;
  preparednessStatus?: EAMStatus | null;
  medicalStatus?: EAMStatus | null;
  mobilityStatus?: EAMStatus | null;
  commsStatus?: EAMStatus | null;
  commsMethod?: string | null;
}

export interface DeleteEmergencyActionMessageResponse {
  status: 'deleted' | 'not_found';
  callsign: string;
}

export interface EventPoint {
  lat?: number | null;
  lon?: number | null;
  ce?: number | null;
  le?: number | null;
  hae?: number | null;
}

export interface EventDetail {
  emergencyActionMessage?: EmergencyActionMessage | null;
}

export interface EventRecord {
  uid: number;
  type?: string | null;
  detail?: EventDetail | null;
  how?: string | null;
  start?: string | null;
  stale?: string | null;
  access?: string | null;
  opex?: number | null;
  qos?: number | null;
  time?: number | null;
  version?: number | null;
  point?: EventPoint | null;
}

export interface DeleteEventResponse {
  status: 'deleted' | 'not_found';
  uid: number | string;
}

const apiBaseUrl = (import.meta.env?.VITE_API_BASE_URL as string | undefined) ??
  'http://localhost:8000';
const updatesUrl = (import.meta.env?.VITE_UPDATES_URL as string | undefined)?.trim();
const serverIdentity = (import.meta.env?.VITE_SERVER_IDENTITY as string | undefined)?.trim();

export function getApiBaseUrl(): string {
  return apiBaseUrl;
}

export function getLiveUpdatesUrl(): string {
  if (updatesUrl) {
    if (updatesUrl.startsWith('http://') || updatesUrl.startsWith('https://')) {
      return updatesUrl;
    }
    return `${apiBaseUrl.replace(/\/$/, '')}${updatesUrl.startsWith('/') ? '' : '/'}${updatesUrl}`;
  }
  return `${apiBaseUrl.replace(/\/$/, '')}/stream`;
}

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

if (serverIdentity) {
  apiClient.defaults.headers.common['X-Server-Identity'] = serverIdentity;
}

export async function listEmergencyActionMessages(): Promise<EmergencyActionMessage[]> {
  const response = await apiClient.get<EmergencyActionMessage[] | null>(
    '/emergency-action-messages',
  );
  return response.data ?? [];
}

export async function retrieveEmergencyActionMessage(
  callsign: string,
): Promise<EmergencyActionMessage | null> {
  const response = await apiClient.get<EmergencyActionMessage | null>(
    `/emergency-action-messages/${encodeURIComponent(callsign)}`,
  );
  return response.data ?? null;
}

export async function createEmergencyActionMessage(
  message: EmergencyActionMessage,
): Promise<EmergencyActionMessage> {
  const response = await apiClient.post<EmergencyActionMessage>(
    '/emergency-action-messages',
    message,
  );
  return response.data;
}

export async function updateEmergencyActionMessage(
  message: EmergencyActionMessage,
): Promise<EmergencyActionMessage | null> {
  const response = await apiClient.put<EmergencyActionMessage | null>(
    `/emergency-action-messages/${encodeURIComponent(message.callsign)}`,
    message,
  );
  return response.data ?? null;
}

export async function deleteEmergencyActionMessage(
  callsign: string,
): Promise<DeleteEmergencyActionMessageResponse> {
  const response = await apiClient.delete<DeleteEmergencyActionMessageResponse>(
    `/emergency-action-messages/${encodeURIComponent(callsign)}`,
  );
  return response.data;
}

export async function listEvents(): Promise<EventRecord[]> {
  const response = await apiClient.get<EventRecord[] | null>('/events');
  return response.data ?? [];
}

export async function retrieveEvent(uid: number | string): Promise<EventRecord | null> {
  const response = await apiClient.get<EventRecord | null>(`/events/${encodeURIComponent(uid)}`);
  return response.data ?? null;
}

export async function createEvent(event: EventRecord): Promise<EventRecord> {
  const response = await apiClient.post<EventRecord>('/events', event);
  return response.data;
}

export async function updateEvent(event: EventRecord): Promise<EventRecord | null> {
  const response = await apiClient.put<EventRecord | null>(`/events/${encodeURIComponent(event.uid)}`, event);
  return response.data ?? null;
}

export async function deleteEvent(uid: number | string): Promise<DeleteEventResponse> {
  const response = await apiClient.delete<DeleteEventResponse>(`/events/${encodeURIComponent(uid)}`);
  return response.data;
}

export function extractApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    const detail = axiosError.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (typeof axiosError.message === 'string' && axiosError.message.trim()) {
      return axiosError.message;
    }
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'Unexpected error communicating with the gateway.';
}
