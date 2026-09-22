/// <reference types="node" />

import { createHash } from 'crypto';
import { TextEncoder } from 'util';

import {
  beginClientObservation,
  completeClientObservation,
  CLIENT_OBSERVATION_RECEIPT_FILENAME,
  downloadClientObservationReceipt
} from './ClientObservationReceipt';

describe('privacy-minimal client observation receipt', () => {
  beforeEach(() => {
    const digest = jest.fn(async (
      _algorithm: AlgorithmIdentifier,
      data: BufferSource
    ): Promise<ArrayBuffer> => {
      const bytes = data instanceof ArrayBuffer
        ? new Uint8Array(data)
        : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
      return Uint8Array.from(createHash('sha256').update(bytes).digest()).buffer;
    });
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: {
        randomUUID: (): string => '11111111-2222-4333-8444-555555555555',
        subtle: { digest }
      }
    });
    Object.defineProperty(globalThis, 'TextEncoder', {
      configurable: true,
      value: TextEncoder
    });
  });

  it('emits only the closed privacy allowlist and never the raw correlation id', async () => {
    const observation = beginClientObservation('2026-09-21T08:00:00.000Z');
    const completed = await completeClientObservation(
      observation,
      false,
      '2026-09-21T08:00:01.000Z'
    );

    expect(CLIENT_OBSERVATION_RECEIPT_FILENAME)
      .toBe('nac-issue748-client-observation.json');
    expect(Object.keys(completed.receipt).sort()).toEqual([
      'end_utc',
      'request_correlation_binding_sha256',
      'spfx_subject_available',
      'start_utc',
      'ui_state',
      'window_binding_sha256'
    ]);
    expect(completed.receipt.ui_state).toBe('no_access');
    expect(completed.receipt.spfx_subject_available).toBe(false);
    expect(completed.canonicalJson)
      .not.toContain('spfx-11111111-2222-4333-8444-555555555555');
    expect(completed.canonicalJson).not.toMatch(/object|subjectId|email|tenant|token|header/i);
    expect(completed.canonicalJson).toBe(JSON.stringify(completed.receipt));
    expect(() => observation.takeCorrelationIdForRequest())
      .toThrow('NAC_CLIENT_OBSERVATION_CORRELATION_CONSUMED');
  });

  it('fails closed without cryptographically secure browser primitives', () => {
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: undefined
    });
    expect(() => beginClientObservation('2026-09-21T08:00:00.000Z'))
      .toThrow('NAC_CLIENT_OBSERVATION_UNAVAILABLE');
  });

  it('rejects an open or reversed observation window', async () => {
    const observation = beginClientObservation('2026-09-21T08:00:02.000Z');
    await expect(completeClientObservation(
      observation,
      true,
      '2026-09-21T08:00:01.000Z'
    )).rejects.toThrow('NAC_CLIENT_OBSERVATION_INVALID');
  });

  it('allows the raw correlation id to be consumed exactly once', () => {
    const observation = beginClientObservation('2026-09-21T08:00:00.000Z');
    expect(observation.takeCorrelationIdForRequest())
      .toBe('spfx-11111111-2222-4333-8444-555555555555');
    expect(() => observation.takeCorrelationIdForRequest())
      .toThrow('NAC_CLIENT_OBSERVATION_CORRELATION_CONSUMED');
  });

  it('downloads the exact canonical bytes only after an explicit call', async () => {
    let createdBlob: Blob | undefined;
    let clickedDownload = '';
    const createObjectURL = jest.fn((blob: Blob): string => {
      createdBlob = blob;
      return 'blob:nac-issue748';
    });
    const revokeObjectURL = jest.fn();
    Object.defineProperty(globalThis.URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL
    });
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectURL
    });
    const click = jest.spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(function (this: HTMLAnchorElement): void {
        clickedDownload = this.download;
      });
    const canonicalJson = '{"ui_state":"no_access"}';

    downloadClientObservationReceipt(canonicalJson);

    expect(click).toHaveBeenCalledTimes(1);
    expect(clickedDownload).toBe(CLIENT_OBSERVATION_RECEIPT_FILENAME);
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:nac-issue748');
    expect(createdBlob?.type).toBe('application/json');
    const reader = new FileReader();
    const body = await new Promise<string>((resolve, reject) => {
      reader.onerror = () => reject(reader.error);
      reader.onload = () => resolve(String(reader.result));
      reader.readAsText(createdBlob as Blob);
    });
    expect(body).toBe(canonicalJson);
    click.mockRestore();
  });
});
