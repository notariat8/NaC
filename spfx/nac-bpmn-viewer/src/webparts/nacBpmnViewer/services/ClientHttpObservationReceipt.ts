export const CLIENT_HTTP_OBSERVATION_FILENAME =
  'nac-issue748-client-http-observation.json';

export type ClientHttpClass = 'none' | '401' | '403';

export interface ClientHttpObservationReceipt {
  readonly base_receipt_sha256: string;
  readonly client_http_class: ClientHttpClass;
  readonly observation_binding_sha256: string;
  readonly schema_version: 'nac.client-http-observation/v0.1';
}

export interface CompletedClientHttpObservation {
  readonly receipt: ClientHttpObservationReceipt;
  readonly canonicalJson: string;
}

export async function completeClientHttpObservation(
  baseReceiptJson: string,
  clientHttpClass: ClientHttpClass
): Promise<CompletedClientHttpObservation> {
  const subjectAvailable = canonicalBaseSubjectAvailability(baseReceiptJson);
  if (
    !['none', '401', '403'].includes(clientHttpClass) ||
    subjectAvailable === undefined ||
    (!subjectAvailable && clientHttpClass !== 'none')
  ) {
    throw new Error('NAC_CLIENT_HTTP_OBSERVATION_INVALID');
  }
  const core = {
    base_receipt_sha256: await sha256(baseReceiptJson),
    client_http_class: clientHttpClass,
    schema_version: 'nac.client-http-observation/v0.1' as const
  };
  const receipt: ClientHttpObservationReceipt = {
    base_receipt_sha256: core.base_receipt_sha256,
    client_http_class: core.client_http_class,
    observation_binding_sha256: await sha256(JSON.stringify(core)),
    schema_version: core.schema_version
  };
  const canonicalJson = JSON.stringify(receipt);
  if (new TextEncoder().encode(canonicalJson).byteLength > 1024) {
    throw new Error('NAC_CLIENT_HTTP_OBSERVATION_INVALID');
  }
  return { receipt, canonicalJson };
}

export function downloadClientHttpObservationReceipt(canonicalJson: string): void {
  const blob = new Blob([canonicalJson], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = CLIENT_HTTP_OBSERVATION_FILENAME;
    anchor.rel = 'noopener';
    anchor.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}

function canonicalBaseSubjectAvailability(value: string): boolean | undefined {
  try {
    const parsed: unknown = JSON.parse(value);
    if (
      typeof parsed !== 'object' || parsed === null || Array.isArray(parsed) ||
      JSON.stringify(parsed) !== value ||
      Object.keys(parsed).sort().join(',') !==
        'end_utc,request_correlation_binding_sha256,spfx_subject_available,start_utc,ui_state,window_binding_sha256'
    ) {
      return undefined;
    }
    const receipt = parsed as Record<string, unknown>;
    return receipt.ui_state === 'no_access' &&
      typeof receipt.spfx_subject_available === 'boolean'
      ? receipt.spfx_subject_available
      : undefined;
  } catch {
    return undefined;
  }
}

async function sha256(value: string): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error('NAC_CLIENT_HTTP_OBSERVATION_UNAVAILABLE');
  }
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest))
    .map(byte => ('0' + byte.toString(16)).slice(-2))
    .join('');
}
