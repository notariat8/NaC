export const CLIENT_OBSERVATION_RECEIPT_FILENAME =
  'nac-issue748-client-observation.json';

const MAX_OBSERVATION_WINDOW_MS = 15 * 60 * 1000;

export interface ClientObservation {
  readonly startUtc: string;
  readonly correlationBinding: Promise<string>;
  takeCorrelationIdForRequest(): string;
  discardCorrelationId(): void;
}

export interface ClientObservationReceipt {
  readonly end_utc: string;
  readonly request_correlation_binding_sha256: string;
  readonly spfx_subject_available: boolean;
  readonly start_utc: string;
  readonly ui_state: 'no_access';
  readonly window_binding_sha256: string;
}

export interface CompletedClientObservation {
  readonly receipt: ClientObservationReceipt;
  readonly canonicalJson: string;
}

export function beginClientObservation(nowUtc: string = new Date().toISOString()): ClientObservation {
  const cryptoApi = globalThis.crypto;
  if (!cryptoApi?.randomUUID || !cryptoApi.subtle || !isCanonicalUtc(nowUtc)) {
    throw new Error('NAC_CLIENT_OBSERVATION_UNAVAILABLE');
  }
  let correlationId: string | undefined = 'spfx-' + cryptoApi.randomUUID();
  const correlationBinding = sha256(correlationId);
  return {
    startUtc: nowUtc,
    correlationBinding,
    takeCorrelationIdForRequest: (): string => {
      if (correlationId === undefined) {
        throw new Error('NAC_CLIENT_OBSERVATION_CORRELATION_CONSUMED');
      }
      const value = correlationId;
      correlationId = undefined;
      return value;
    },
    discardCorrelationId: (): void => {
      correlationId = undefined;
    }
  };
}

export async function completeClientObservation(
  observation: ClientObservation,
  spfxSubjectAvailable: boolean,
  endUtc: string = new Date().toISOString()
): Promise<CompletedClientObservation> {
  if (!isCanonicalUtc(observation.startUtc) || !isCanonicalUtc(endUtc)) {
    throw new Error('NAC_CLIENT_OBSERVATION_INVALID');
  }
  const startMs = Date.parse(observation.startUtc);
  const endMs = Date.parse(endUtc);
  if (endMs <= startMs || endMs - startMs > MAX_OBSERVATION_WINDOW_MS) {
    throw new Error('NAC_CLIENT_OBSERVATION_INVALID');
  }
  observation.discardCorrelationId();
  const requestCorrelationBinding = await observation.correlationBinding;
  const windowCore = {
    end_utc: endUtc,
    request_correlation_binding_sha256: requestCorrelationBinding,
    spfx_subject_available: spfxSubjectAvailable,
    start_utc: observation.startUtc,
    ui_state: 'no_access' as const
  };
  const receipt: ClientObservationReceipt = {
    ...windowCore,
    window_binding_sha256: await sha256(JSON.stringify(windowCore))
  };
  return { receipt, canonicalJson: JSON.stringify(receipt) };
}

export function downloadClientObservationReceipt(canonicalJson: string): void {
  const blob = new Blob([canonicalJson], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = CLIENT_OBSERVATION_RECEIPT_FILENAME;
    anchor.rel = 'noopener';
    anchor.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}

async function sha256(value: string): Promise<string> {
  const cryptoApi = globalThis.crypto;
  if (!cryptoApi?.subtle) {
    throw new Error('NAC_CLIENT_OBSERVATION_UNAVAILABLE');
  }
  const digest = await cryptoApi.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(value)
  );
  return Array.from(new Uint8Array(digest))
    .map(byte => ('0' + byte.toString(16)).slice(-2))
    .join('');
}

function isCanonicalUtc(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) {
    return false;
  }
  const parsed = new Date(value);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString() === value;
}
