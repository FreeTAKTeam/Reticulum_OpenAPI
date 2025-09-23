import { useEffect, useMemo, useState } from 'react';

import type { EAMStatus, EmergencyActionMessage } from '../../lib/apiClient';

export type MessageFormMode = 'create' | 'edit';

interface MessageFormProps {
  mode: MessageFormMode;
  initialValue: EmergencyActionMessage | null;
  onSubmit: (message: EmergencyActionMessage) => Promise<void> | void;
  onReset: () => void;
  isSubmitting: boolean;
}

const STATUS_FIELDS: Array<keyof EmergencyActionMessage> = [
  'securityStatus',
  'securityCapability',
  'preparednessStatus',
  'medicalStatus',
  'mobilityStatus',
  'commsStatus',
];

const STATUS_OPTIONS: Array<EAMStatus | ''> = ['', 'Red', 'Yellow', 'Green'];

interface FormState extends EmergencyActionMessage {}

interface FormErrors {
  callsign?: string;
}

function buildInitialState(value: EmergencyActionMessage | null): FormState {
  return {
    callsign: value?.callsign ?? '',
    groupName: value?.groupName ?? '',
    securityStatus: value?.securityStatus ?? null,
    securityCapability: value?.securityCapability ?? null,
    preparednessStatus: value?.preparednessStatus ?? null,
    medicalStatus: value?.medicalStatus ?? null,
    mobilityStatus: value?.mobilityStatus ?? null,
    commsStatus: value?.commsStatus ?? null,
    commsMethod: value?.commsMethod ?? '',
  };
}

export function MessageForm({
  mode,
  initialValue,
  onSubmit,
  onReset,
  isSubmitting,
}: MessageFormProps): JSX.Element {
  const [state, setState] = useState<FormState>(() => buildInitialState(initialValue));
  const [errors, setErrors] = useState<FormErrors>({});

  useEffect(() => {
    setState(buildInitialState(initialValue));
    setErrors({});
  }, [initialValue]);

  const isEditMode = mode === 'edit';
  const statusLegend = useMemo(
    () =>
      STATUS_FIELDS.map((field) => ({
        field,
        label: field.replace(/([A-Z])/g, ' $1').replace(/^./, (char) => char.toUpperCase()),
      })),
    [],
  );

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: FormErrors = {};
    if (!state.callsign.trim()) {
      nextErrors.callsign = 'Callsign is required.';
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    await onSubmit({
      ...state,
      callsign: state.callsign.trim(),
      groupName: state.groupName?.trim() || undefined,
      commsMethod: state.commsMethod?.trim() || undefined,
    });
  };

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = event.target;
    setState((current) => ({
      ...current,
      [name]: value === '' ? '' : value,
    }));
  };

  const handleStatusChange = (
    event: React.ChangeEvent<HTMLSelectElement>,
    field: keyof EmergencyActionMessage,
  ) => {
    const value = event.target.value as EAMStatus | '';
    setState((current) => ({
      ...current,
      [field]: value === '' ? null : value,
    }));
  };

  return (
    <form className="message-form" onSubmit={handleSubmit}>
      <header className="message-form-header">
        <h3>{isEditMode ? 'Update message' : 'Create a new message'}</h3>
        <button type="button" className="secondary-button" onClick={onReset}>
          New message
        </button>
      </header>
      <div className="form-field">
        <label htmlFor="eam-callsign">Callsign</label>
        <input
          id="eam-callsign"
          name="callsign"
          type="text"
          value={state.callsign}
          onChange={handleInputChange}
          disabled={isEditMode}
          aria-invalid={errors.callsign ? 'true' : 'false'}
        />
        {errors.callsign && <p className="field-error">{errors.callsign}</p>}
      </div>
      <div className="form-field">
        <label htmlFor="eam-group-name">Group name</label>
        <input
          id="eam-group-name"
          name="groupName"
          type="text"
          value={state.groupName ?? ''}
          onChange={handleInputChange}
        />
      </div>
      {statusLegend.map(({ field, label }) => (
        <div className="form-field" key={field}>
          <label htmlFor={`eam-${field}`}>{label}</label>
          <select
            id={`eam-${field}`}
            value={state[field] ?? ''}
            onChange={(event) => handleStatusChange(event, field)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || 'empty'} value={option}>
                {option || 'Not specified'}
              </option>
            ))}
          </select>
        </div>
      ))}
      <div className="form-field">
        <label htmlFor="eam-comms-method">Comms method</label>
        <input
          id="eam-comms-method"
          name="commsMethod"
          type="text"
          value={state.commsMethod ?? ''}
          onChange={handleInputChange}
        />
      </div>
      <button type="submit" className="primary-button" disabled={isSubmitting}>
        {isEditMode ? 'Save changes' : 'Create message'}
      </button>
    </form>
  );
}
