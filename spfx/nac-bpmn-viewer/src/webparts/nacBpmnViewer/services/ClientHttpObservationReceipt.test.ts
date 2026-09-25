/// <reference types="node" />
import { createHash } from 'crypto';
import { TextEncoder } from 'util';

import {
  completeClientHttpObservation,
  CLIENT_HTTP_OBSERVATION_FILENAME
} from './ClientHttpObservationReceipt';

describe('client HTTP companion receipt', () => {
  const baseCore = {
    end_utc: '2026-09-25T08:00:01.000Z',
    request_correlation_binding_sha256: 'a'.repeat(64),
    spfx_subject_available: true,
    start_utc: '2026-09-25T08:00:00.000Z',
    ui_state: 'no_access'
  };
  const baseReceipt = JSON.stringify({
    ...baseCore,
    window_binding_sha256: createHash('sha256').update(JSON.stringify(baseCore)).digest('hex')
  });
  beforeEach(() => {
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: {
        subtle: {
          digest: async (_algorithm: AlgorithmIdentifier, data: BufferSource): Promise<ArrayBuffer> => {
            const bytes = data instanceof ArrayBuffer
              ? new Uint8Array(data)
              : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
            return Uint8Array.from(createHash('sha256').update(bytes).digest()).buffer;
          }
        }
      }
    });
    Object.defineProperty(globalThis, 'TextEncoder', { configurable: true, value: TextEncoder });
  });

  it.each(['none', '401', '403'] as const)('binds the exact base bytes and closed class %s', async clientHttpClass => {
    const base = baseReceipt;
    const result = await completeClientHttpObservation(base, clientHttpClass);
    expect(CLIENT_HTTP_OBSERVATION_FILENAME).toBe('nac-issue748-client-http-observation.json');
    expect(result.receipt.base_receipt_sha256).toBe(createHash('sha256').update(base).digest('hex'));
    expect(result.receipt.client_http_class).toBe(clientHttpClass);
    expect(Object.keys(result.receipt).sort()).toEqual([
      'base_receipt_sha256', 'client_http_class', 'observation_binding_sha256', 'schema_version'
    ]);
    expect(result.canonicalJson).toBe(JSON.stringify(result.receipt));
    expect(new TextEncoder().encode(result.canonicalJson).byteLength).toBeLessThanOrEqual(1024);
    expect(result.canonicalJson).not.toMatch(/subject|email|tenant|token|header|url|body/i);
  });

  it('rejects unknown classes and noncanonical base receipts', async () => {
    await expect(completeClientHttpObservation('{}', '200' as '401')).rejects.toThrow();
    await expect(completeClientHttpObservation('{ "ui_state": "no_access" }', '403'))
      .rejects.toThrow();
    const noSubject = JSON.stringify({ ...baseCore, spfx_subject_available: false,
      window_binding_sha256: '0'.repeat(64) });
    await expect(completeClientHttpObservation(noSubject, '401')).rejects.toThrow();
  });
});
