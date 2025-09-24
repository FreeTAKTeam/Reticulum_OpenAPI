import { type FormEvent, useEffect, useMemo, useState } from 'react';

import type { EventPoint, EventRecord } from '../../lib/apiClient';

const DEFAULT_ACCESS_OPTIONS: string[] = ['', 'Public', 'Restricted', 'Confidential'];

interface EventFormProps {
  initialValue?: EventRecord | null;
  onSubmit: (event: EventRecord) => void;
  onCancelEdit?: () => void;
  isSubmitting: boolean;
}

interface FormState {
  uid: string;
  type: string;
  detail: string;
  how: string;
  start: string;
  stale: string;
  access: string;
  qos: string;
  opex: string;
  pointLat: string;
  pointLon: string;
  error: string | null;
}

function createEmptyState(): FormState {
  return {
    uid: '',
    type: '',
    detail: '',
    how: '',
    start: '',
    stale: '',
    access: '',
    qos: '',
    opex: '',
    pointLat: '',
    pointLon: '',
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

export function EventForm({
  initialValue,
  onSubmit,
  onCancelEdit,
  isSubmitting,
}: EventFormProps): JSX.Element {
  const [state, setState] = useState<FormState>(() => {
    if (!initialValue) {
      return createEmptyState();
    }
    return {
      uid: String(initialValue.uid ?? ''),
      type: initialValue.type ?? '',
      detail: initialValue.detail ?? '',
      how: initialValue.how ?? '',
      start: formatDateTimeLocal(initialValue.start),
      stale: formatDateTimeLocal(initialValue.stale),
      access: initialValue.access ?? '',
      qos: initialValue.qos?.toString() ?? '',
      opex: initialValue.opex?.toString() ?? '',
      pointLat: initialValue.point?.lat?.toString() ?? '',
      pointLon: initialValue.point?.lon?.toString() ?? '',
      error: null,
    };
  });

  useEffect(() => {
    if (!initialValue) {
      setState(createEmptyState());
      return;
    }
    setState({
      uid: String(initialValue.uid ?? ''),
      type: initialValue.type ?? '',
      detail: initialValue.detail ?? '',
      how: initialValue.how ?? '',
      start: formatDateTimeLocal(initialValue.start),
      stale: formatDateTimeLocal(initialValue.stale),
      access: initialValue.access ?? '',
      qos: initialValue.qos?.toString() ?? '',
      opex: initialValue.opex?.toString() ?? '',
      pointLat: initialValue.point?.lat?.toString() ?? '',
      pointLon: initialValue.point?.lon?.toString() ?? '',
      error: null,
    });
  }, [initialValue]);

  const isEditing = useMemo(() => Boolean(initialValue), [initialValue]);
  const accessOptions = useMemo(() => {
    const unique = new Set<string>(DEFAULT_ACCESS_OPTIONS);
    if (initialValue?.access) {
      unique.add(initialValue.access);
    }
    return Array.from(unique);
  }, [initialValue?.access]);

  function handleChange(field: keyof FormState, value: string): void {
    setState((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const uidNumber = Number(state.uid);
    if (!state.uid.trim() || Number.isNaN(uidNumber)) {
      setState((current) => ({ ...current, error: 'UID must be a valid number.' }));
      return;
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
      detail: normaliseString(state.detail),
      how: normaliseString(state.how),
      start: normaliseDateTime(state.start),
      stale: normaliseDateTime(state.stale),
      access: normaliseString(state.access),
      qos: normaliseNumber(state.qos),
      opex: normaliseNumber(state.opex),
      point,
    };

    setState((current) => ({ ...current, error: null }));
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
            onChange={(event) => handleChange('uid', event.target.value)}
            required
            disabled={isEditing}
          />
        </label>

        <label className="form-field">
          <span>Type</span>
          <input
            type="text"
            value={state.type}
            onChange={(event) => handleChange('type', event.target.value)}
            placeholder="E.g. Medevac"
          />
        </label>

        <label className="form-field form-field--wide">
          <span>Detail</span>
          <textarea
            rows={3}
            value={state.detail}
            onChange={(event) => handleChange('detail', event.target.value)}
            placeholder="Expanded notes or context"
          />
        </label>

        <label className="form-field">
          <span>How</span>
          <input
            type="text"
            value={state.how}
            onChange={(event) => handleChange('how', event.target.value)}
            placeholder="Voice, mesh, SMS, etc."
          />
        </label>

        <label className="form-field">
          <span>Start</span>
          <input
            type="datetime-local"
            value={state.start}
            onChange={(event) => handleChange('start', event.target.value)}
          />
        </label>

        <label className="form-field">
          <span>Stale</span>
          <input
            type="datetime-local"
            value={state.stale}
            onChange={(event) => handleChange('stale', event.target.value)}
          />
        </label>

        <label className="form-field">
          <span>Access</span>
          <select
            value={state.access}
            onChange={(event) => handleChange('access', event.target.value)}
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
            onChange={(event) => handleChange('qos', event.target.value)}
            min={0}
            step={1}
          />
        </label>

        <label className="form-field">
          <span>OpEx</span>
          <input
            type="number"
            value={state.opex}
            onChange={(event) => handleChange('opex', event.target.value)}
            min={0}
            step={1}
          />
        </label>

        <label className="form-field">
          <span>Latitude</span>
          <input
            type="number"
            value={state.pointLat}
            onChange={(event) => handleChange('pointLat', event.target.value)}
            step="any"
          />
        </label>

        <label className="form-field">
          <span>Longitude</span>
          <input
            type="number"
            value={state.pointLon}
            onChange={(event) => handleChange('pointLon', event.target.value)}
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
