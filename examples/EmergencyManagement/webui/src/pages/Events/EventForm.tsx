import { type FormEvent, useEffect, useMemo, useState } from 'react';

import type {
  EAMStatus,
  EmergencyActionMessage,
  EventPoint,
  EventRecord,
} from '../../lib/apiClient';

const DEFAULT_ACCESS_OPTIONS: string[] = ['', 'Public', 'Restricted', 'Confidential'];
const EAM_STATUS_OPTIONS: Array<'' | EAMStatus> = ['', 'Green', 'Yellow', 'Red'];

interface EventFormProps {
  initialValue?: EventRecord | null;
  onSubmit: (event: EventRecord) => void;
  onCancelEdit?: () => void;
  isSubmitting: boolean;
}

interface FormState {
  uid: string;
  type: string;
  how: string;
  start: string;
  stale: string;
  access: string;
  qos: string;
  opex: string;
  pointLat: string;
  pointLon: string;
  detailIncludeEam: boolean;
  detailCallsign: string;
  detailGroupName: string;
  detailSecurityStatus: string;
  detailSecurityCapability: string;
  detailPreparednessStatus: string;
  detailMedicalStatus: string;
  detailMobilityStatus: string;
  detailCommsStatus: string;
  detailCommsMethod: string;
  error: string | null;
}

type FormFieldKey = Exclude<keyof FormState, 'detailIncludeEam' | 'error'>;

function createEmptyState(): FormState {
  return {
    uid: '',
    type: '',
    how: '',
    start: '',
    stale: '',
    access: '',
    qos: '',
    opex: '',
    pointLat: '',
    pointLon: '',
    detailIncludeEam: false,
    detailCallsign: '',
    detailGroupName: '',
    detailSecurityStatus: '',
    detailSecurityCapability: '',
    detailPreparednessStatus: '',
    detailMedicalStatus: '',
    detailMobilityStatus: '',
    detailCommsStatus: '',
    detailCommsMethod: '',
    error: null,
  };
}

function createStateFromRecord(record?: EventRecord | null): FormState {
  if (!record) {
    return createEmptyState();
  }

  const message = record.detail?.emergencyActionMessage ?? null;

  return {
    uid: String(record.uid ?? ''),
    type: record.type ?? '',
    how: record.how ?? '',
    start: formatDateTimeLocal(record.start),
    stale: formatDateTimeLocal(record.stale),
    access: record.access ?? '',
    qos: record.qos?.toString() ?? '',
    opex: record.opex?.toString() ?? '',
    pointLat: record.point?.lat?.toString() ?? '',
    pointLon: record.point?.lon?.toString() ?? '',
    detailIncludeEam: Boolean(message),
    detailCallsign: message?.callsign ?? '',
    detailGroupName: message?.groupName ?? '',
    detailSecurityStatus: message?.securityStatus ?? '',
    detailSecurityCapability: message?.securityCapability ?? '',
    detailPreparednessStatus: message?.preparednessStatus ?? '',
    detailMedicalStatus: message?.medicalStatus ?? '',
    detailMobilityStatus: message?.mobilityStatus ?? '',
    detailCommsStatus: message?.commsStatus ?? '',
    detailCommsMethod: message?.commsMethod ?? '',
    error: null,
  };
}

function normaliseNumber(value: string): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return null;
  }
  return parsed;
}

function normaliseString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function formatDateTimeLocal(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return '';
  }
  const pad = (input: number) => input.toString().padStart(2, '0');
  const year = parsed.getFullYear();
  const month = pad(parsed.getMonth() + 1);
  const day = pad(parsed.getDate());
  const hours = pad(parsed.getHours());
  const minutes = pad(parsed.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function normaliseDateTime(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = new Date(trimmed);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString();
}

function normaliseEamStatus(value: string): EAMStatus | null {
  if (value === 'Green' || value === 'Yellow' || value === 'Red') {
    return value;
  }
  return null;
}

export function EventForm({
  initialValue,
  onSubmit,
  onCancelEdit,
  isSubmitting,
}: EventFormProps): JSX.Element {
  const [state, setState] = useState<FormState>(() => createStateFromRecord(initialValue));

  useEffect(() => {
    setState(createStateFromRecord(initialValue));
  }, [initialValue]);

  const isEditing = useMemo(() => Boolean(initialValue), [initialValue]);
  const accessOptions = useMemo(() => {
    const unique = new Set<string>(DEFAULT_ACCESS_OPTIONS);
    if (initialValue?.access) {
      unique.add(initialValue.access);
    }
    return Array.from(unique);
  }, [initialValue?.access]);

  function handleFieldChange(field: FormFieldKey, value: string): void {
    setState((current) => ({
      ...current,
      [field]: value,
      error: null,
    }));
  }

  function handleToggleDetail(include: boolean): void {
    setState((current) => ({
      ...current,
      detailIncludeEam: include,
      error: null,
    }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setState((current) => ({ ...current, error: null }));

    const uidNumber = Number(state.uid.trim());
    if (!state.uid.trim() || Number.isNaN(uidNumber)) {
      setState((current) => ({ ...current, error: 'UID must be a valid number.' }));
      return;
    }

    let detail: EventRecord['detail'] = null;
    if (state.detailIncludeEam) {
      const callsign = state.detailCallsign.trim();
      if (!callsign) {
        setState((current) => ({
          ...current,
          error: 'Callsign is required when including emergency action message detail.',
        }));
        return;
      }

      const message: EmergencyActionMessage = { callsign };
      const groupName = normaliseString(state.detailGroupName);
      if (groupName !== null) {
        message.groupName = groupName;
      }
      const commsMethod = normaliseString(state.detailCommsMethod);
      if (commsMethod !== null) {
        message.commsMethod = commsMethod;
      }

      type StatusKey =
        | 'securityStatus'
        | 'securityCapability'
        | 'preparednessStatus'
        | 'medicalStatus'
        | 'mobilityStatus'
        | 'commsStatus';

      const statusEntries: Array<[StatusKey, string]> = [
        ['securityStatus', state.detailSecurityStatus],
        ['securityCapability', state.detailSecurityCapability],
        ['preparednessStatus', state.detailPreparednessStatus],
        ['medicalStatus', state.detailMedicalStatus],
        ['mobilityStatus', state.detailMobilityStatus],
        ['commsStatus', state.detailCommsStatus],
      ];

      statusEntries.forEach(([key, raw]) => {
        const value = normaliseEamStatus(raw);
        if (value) {
          message[key] = value;
        }
      });

      detail = { emergencyActionMessage: message };
    }

    const point: EventPoint | null = (() => {
      const lat = normaliseNumber(state.pointLat);
      const lon = normaliseNumber(state.pointLon);
      if (lat === null && lon === null) {
        return null;
      }
      return {
        lat: lat ?? undefined,
        lon: lon ?? undefined,
      };
    })();

    const record: EventRecord = {
      uid: uidNumber,
      type: normaliseString(state.type),
      detail,
      how: normaliseString(state.how),
      start: normaliseDateTime(state.start),
      stale: normaliseDateTime(state.stale),
      access: normaliseString(state.access),
      qos: normaliseNumber(state.qos),
      opex: normaliseNumber(state.opex),
      point,
    };

    onSubmit(record);
  }

  return (
    <form className="form-card" onSubmit={handleSubmit} noValidate>
      <header className="form-card__header">
        <div>
          <h3>{isEditing ? `Update event ${state.uid}` : 'Log new event'}</h3>
          <p>Track incident reports, dispatches, and situational notes.</p>
        </div>
        {isEditing && (
          <button
            type="button"
            className="button button--secondary"
            onClick={onCancelEdit}
            disabled={isSubmitting}
          >
            Cancel edit
          </button>
        )}
      </header>

      {state.error && <p className="form-error" role="alert">{state.error}</p>}

      <div className="form-grid">
        <label className="form-field">
          <span>UID</span>
          <input
            type="number"
            value={state.uid}
            onChange={(event) => handleFieldChange('uid', event.target.value)}
            required
            disabled={isEditing}
          />
        </label>

        <label className="form-field">
          <span>Type</span>
          <input
            type="text"
            value={state.type}
            onChange={(event) => handleFieldChange('type', event.target.value)}
            placeholder="E.g. Medevac"
          />
        </label>

        <div className="form-section form-field--wide">
          <div className="form-section__header">
            <h4>Emergency action message</h4>
            <p>Attach structured message detail from incoming reports.</p>
          </div>
          <label className="form-checkbox">
            <input
              type="checkbox"
              checked={state.detailIncludeEam}
              onChange={(event) => handleToggleDetail(event.target.checked)}
            />
            <span>Include emergency action message detail</span>
          </label>
          {state.detailIncludeEam && (
            <div className="form-section__grid">
              <label className="form-field">
                <span>EAM Callsign</span>
                <input
                  type="text"
                  value={state.detailCallsign}
                  onChange={(event) => handleFieldChange('detailCallsign', event.target.value)}
                  required={state.detailIncludeEam}
                  placeholder="Originating callsign"
                />
              </label>

              <label className="form-field">
                <span>EAM Group name</span>
                <input
                  type="text"
                  value={state.detailGroupName}
                  onChange={(event) => handleFieldChange('detailGroupName', event.target.value)}
                  placeholder="Unit or responder"
                />
              </label>

              <label className="form-field">
                <span>Security status</span>
                <select
                  value={state.detailSecurityStatus}
                  onChange={(event) => handleFieldChange('detailSecurityStatus', event.target.value)}
                >
                  {EAM_STATUS_OPTIONS.map((option) => (
                    <option key={option || 'blank'} value={option}>
                      {option || 'Unspecified'}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Security capability</span>
                <select
                  value={state.detailSecurityCapability}
                  onChange={(event) => handleFieldChange('detailSecurityCapability', event.target.value)}
                >
                  {EAM_STATUS_OPTIONS.map((option) => (
                    <option key={option || 'blank'} value={option}>
                      {option || 'Unspecified'}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Preparedness status</span>
                <select
                  value={state.detailPreparednessStatus}
                  onChange={(event) => handleFieldChange('detailPreparednessStatus', event.target.value)}
                >
                  {EAM_STATUS_OPTIONS.map((option) => (
                    <option key={option || 'blank'} value={option}>
                      {option || 'Unspecified'}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Medical status</span>
                <select
                  value={state.detailMedicalStatus}
                  onChange={(event) => handleFieldChange('detailMedicalStatus', event.target.value)}
                >
                  {EAM_STATUS_OPTIONS.map((option) => (
                    <option key={option || 'blank'} value={option}>
                      {option || 'Unspecified'}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Mobility status</span>
                <select
                  value={state.detailMobilityStatus}
                  onChange={(event) => handleFieldChange('detailMobilityStatus', event.target.value)}
                >
                  {EAM_STATUS_OPTIONS.map((option) => (
                    <option key={option || 'blank'} value={option}>
                      {option || 'Unspecified'}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Comms status</span>
                <select
                  value={state.detailCommsStatus}
                  onChange={(event) => handleFieldChange('detailCommsStatus', event.target.value)}
                >
                  {EAM_STATUS_OPTIONS.map((option) => (
                    <option key={option || 'blank'} value={option}>
                      {option || 'Unspecified'}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Comms method</span>
                <input
                  type="text"
                  value={state.detailCommsMethod}
                  onChange={(event) => handleFieldChange('detailCommsMethod', event.target.value)}
                  placeholder="Radio, mesh, phone, etc."
                />
              </label>
            </div>
          )}
        </div>

        <label className="form-field">
          <span>How</span>
          <input
            type="text"
            value={state.how}
            onChange={(event) => handleFieldChange('how', event.target.value)}
            placeholder="Voice, mesh, SMS, etc."
          />
        </label>

        <label className="form-field">
          <span>Start</span>
          <input
            type="datetime-local"
            value={state.start}
            onChange={(event) => handleFieldChange('start', event.target.value)}
          />
        </label>

        <label className="form-field">
          <span>Stale</span>
          <input
            type="datetime-local"
            value={state.stale}
            onChange={(event) => handleFieldChange('stale', event.target.value)}
          />
        </label>

        <label className="form-field">
          <span>Access</span>
          <select
            value={state.access}
            onChange={(event) => handleFieldChange('access', event.target.value)}
          >
            {accessOptions.map((option) => (
              <option key={option || 'blank'} value={option}>
                {option || 'Unspecified'}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>QoS</span>
          <input
            type="number"
            value={state.qos}
            onChange={(event) => handleFieldChange('qos', event.target.value)}
            min={0}
            step={1}
          />
        </label>

        <label className="form-field">
          <span>OpEx</span>
          <input
            type="number"
            value={state.opex}
            onChange={(event) => handleFieldChange('opex', event.target.value)}
            min={0}
            step={1}
          />
        </label>

        <label className="form-field">
          <span>Latitude</span>
          <input
            type="number"
            value={state.pointLat}
            onChange={(event) => handleFieldChange('pointLat', event.target.value)}
            step="any"
          />
        </label>

        <label className="form-field">
          <span>Longitude</span>
          <input
            type="number"
            value={state.pointLon}
            onChange={(event) => handleFieldChange('pointLon', event.target.value)}
            step="any"
          />
        </label>
      </div>

      <footer className="form-card__footer">
        <button type="submit" className="button" disabled={isSubmitting}>
          {isEditing ? 'Save event' : 'Create event'}
        </button>
      </footer>
    </form>
  );
}
