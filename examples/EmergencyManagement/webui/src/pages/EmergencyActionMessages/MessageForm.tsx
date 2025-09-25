import { type FormEvent, useEffect, useMemo, useState } from 'react';

import type { EAMStatus, EmergencyActionMessage } from '../../lib/apiClient';

const STATUS_OPTIONS: Array<EAMStatus | ''> = ['', 'Green', 'Yellow', 'Red'];

function createEmptyMessage(): EmergencyActionMessage {
  return {
    callsign: '',
    groupName: '',
    securityStatus: null,
    securityCapability: null,
    preparednessStatus: null,
    medicalStatus: null,
    mobilityStatus: null,
    commsStatus: null,
    commsMethod: '',
  };
}

export interface MessageFormProps {
  initialValue?: EmergencyActionMessage | null;
  onSubmit: (message: EmergencyActionMessage) => void;
  onCancelEdit?: () => void;
  isSubmitting: boolean;
}

interface FormState {
  values: EmergencyActionMessage;
  error: string | null;
}

function normaliseStatus(value: string): EAMStatus | null {
  if (!value) {
    return null;
  }
  if (value === 'Green' || value === 'Yellow' || value === 'Red') {
    return value;
  }
  return null;
}

function cleanString(value?: string | null): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function MessageForm({
  initialValue,
  onSubmit,
  onCancelEdit,
  isSubmitting,
}: MessageFormProps): JSX.Element {
  const [state, setState] = useState<FormState>({
    values: initialValue ? { ...createEmptyMessage(), ...initialValue } : createEmptyMessage(),
    error: null,
  });

  useEffect(() => {
    if (initialValue) {
      setState({
        values: { ...createEmptyMessage(), ...initialValue },
        error: null,
      });
    } else {
      setState({ values: createEmptyMessage(), error: null });
    }
  }, [initialValue]);

  const isEditing = useMemo(() => Boolean(initialValue?.callsign), [initialValue]);
  const dismissLabel = isEditing ? 'Cancel edit' : 'Close';

  const statusFields: Array<keyof EmergencyActionMessage> = useMemo(
    () => [
      'securityStatus',
      'securityCapability',
      'preparednessStatus',
      'medicalStatus',
      'mobilityStatus',
      'commsStatus',
    ],
    [],
  );

  function handleChange(field: keyof EmergencyActionMessage, value: string): void {
    setState((current) => {
      const nextValues = { ...current.values };
      if (statusFields.includes(field)) {
        nextValues[field] = normaliseStatus(value) as never;
      } else {
        nextValues[field] = value as never;
      }
      return {
        ...current,
        values: nextValues,
      };
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const callsign = state.values.callsign.trim();
    if (!callsign) {
      setState((current) => ({ ...current, error: 'Callsign is required.' }));
      return;
    }

    const message: EmergencyActionMessage = {
      callsign,
      groupName: cleanString(state.values.groupName),
      securityStatus: state.values.securityStatus ?? null,
      securityCapability: state.values.securityCapability ?? null,
      preparednessStatus: state.values.preparednessStatus ?? null,
      medicalStatus: state.values.medicalStatus ?? null,
      mobilityStatus: state.values.mobilityStatus ?? null,
      commsStatus: state.values.commsStatus ?? null,
      commsMethod: cleanString(state.values.commsMethod),
    };

    setState((current) => ({ ...current, error: null }));
    onSubmit(message);
  }

  return (
    <form className="form-card" onSubmit={handleSubmit} noValidate>
      <header className="form-card__header">
        <div>
          <h3>{isEditing ? `Update ${state.values.callsign}` : 'Create new message'}</h3>
          <p>Capture an updated readiness snapshot for each callsign.</p>
        </div>
        {onCancelEdit && (
          <button
            type="button"
            className="button button--secondary"
            onClick={onCancelEdit}
            disabled={isSubmitting}
          >
            {dismissLabel}
          </button>
        )}
      </header>

      {state.error && <p className="form-error" role="alert">{state.error}</p>}

      <div className="form-grid">
        <label className="form-field">
          <span>Callsign</span>
          <input
            type="text"
            value={state.values.callsign}
            onChange={(event) => handleChange('callsign', event.target.value)}
            placeholder="e.g. Alpha-1"
            required
            disabled={isEditing}
          />
        </label>

        <label className="form-field">
          <span>Group name</span>
          <input
            type="text"
            value={state.values.groupName ?? ''}
            onChange={(event) => handleChange('groupName', event.target.value)}
            placeholder="Logistics Team"
          />
        </label>

        <label className="form-field">
          <span>Security status</span>
          <select
            value={(state.values.securityStatus as EAMStatus | '') ?? ''}
            onChange={(event) => handleChange('securityStatus', event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || 'blank'} value={option}>
                {option || 'Unknown'}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>Security capability</span>
          <select
            value={(state.values.securityCapability as EAMStatus | '') ?? ''}
            onChange={(event) => handleChange('securityCapability', event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || 'blank'} value={option}>
                {option || 'Unknown'}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>Preparedness</span>
          <select
            value={(state.values.preparednessStatus as EAMStatus | '') ?? ''}
            onChange={(event) => handleChange('preparednessStatus', event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || 'blank'} value={option}>
                {option || 'Unknown'}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>Medical status</span>
          <select
            value={(state.values.medicalStatus as EAMStatus | '') ?? ''}
            onChange={(event) => handleChange('medicalStatus', event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || 'blank'} value={option}>
                {option || 'Unknown'}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>Mobility</span>
          <select
            value={(state.values.mobilityStatus as EAMStatus | '') ?? ''}
            onChange={(event) => handleChange('mobilityStatus', event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || 'blank'} value={option}>
                {option || 'Unknown'}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>Comms status</span>
          <select
            value={(state.values.commsStatus as EAMStatus | '') ?? ''}
            onChange={(event) => handleChange('commsStatus', event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || 'blank'} value={option}>
                {option || 'Unknown'}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field form-field--wide">
          <span>Comms method</span>
          <input
            type="text"
            value={state.values.commsMethod ?? ''}
            onChange={(event) => handleChange('commsMethod', event.target.value)}
            placeholder="e.g. VHF 145.625 MHz, PL 123.0"
          />
        </label>
      </div>

      <footer className="form-card__footer">
        <button type="submit" className="button" disabled={isSubmitting}>
          {isEditing ? 'Save message' : 'Create message'}
        </button>
      </footer>
    </form>
  );
}
