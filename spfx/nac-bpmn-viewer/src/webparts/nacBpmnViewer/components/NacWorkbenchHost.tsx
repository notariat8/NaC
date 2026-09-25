import * as React from 'react';

import { WorkbenchSnapshot } from '../../../workbench/core/WorkbenchContracts';
import { snapshotEffectiveExpiry } from '../../../workbench/core/WorkbenchSelectors';
import { WorkbenchPanel } from '../../../workbench/react/WorkbenchPanel';
import {
  beginClientObservation,
  ClientObservation,
  completeClientObservation,
  downloadClientObservationReceipt
} from '../services/ClientObservationReceipt';
import {
  ClientHttpClass,
  completeClientHttpObservation,
  downloadClientHttpObservationReceipt
} from '../services/ClientHttpObservationReceipt';
import { NacBffHttpAccessDeniedError } from '../services/NacBffHttpAccessDeniedError';
import { nacWorkbenchHostStyleSheet } from './NacWorkbenchHost.styles';

const LOAD_TIMEOUT_MS = 10_000;
const REFRESH_FRACTION = 0.8;
let hostInstanceCounter = 0;

type HostSurface = 'workbench' | 'detail';

type HostState =
  | { readonly kind: 'loading' }
  | { readonly kind: 'accessDenied'; readonly receiptJson?: string; readonly httpReceiptJson?: string }
  | { readonly kind: 'unavailable' }
  | { readonly kind: 'ready'; readonly snapshot: WorkbenchSnapshot };

export interface NacWorkbenchHostProps {
  readonly expectedSubjectId: string | undefined;
  readonly loadSnapshot: (
    signal: AbortSignal,
    observationCorrelationId?: string
  ) => Promise<WorkbenchSnapshot>;
  readonly detailSurface: React.ReactNode;
  readonly downloadReceipt?: (canonicalJson: string) => void;
  readonly downloadHttpReceipt?: (canonicalJson: string) => void;
}

export function NacWorkbenchHost(props: NacWorkbenchHostProps): React.ReactElement {
  const [state, setState] = React.useState<HostState>({ kind: 'loading' });
  const [surface, setSurface] = React.useState<HostSurface>('workbench');
  const generation = React.useRef(0);
  const workbenchTab = React.useRef<HTMLButtonElement>(null);
  const detailTab = React.useRef<HTMLButtonElement>(null);
  const [hostId] = React.useState(() => {
    hostInstanceCounter += 1;
    return 'nac-workbench-host-' + hostInstanceCounter;
  });

  React.useEffect(() => {
    const subjectId = props.expectedSubjectId;
    let disposed = false;
    const closeDeniedObservation = (
      observation: ClientObservation | undefined,
      spfxSubjectAvailable: boolean,
      requestGeneration: number,
      clientHttpClass?: ClientHttpClass
    ): void => {
      if (disposed || generation.current !== requestGeneration) return;
      setState({ kind: 'accessDenied' });
      if (!observation) return;
      const endUtc = new Date(Math.max(
        Date.now(),
        Date.parse(observation.startUtc) + 1
      )).toISOString();
      completeClientObservation(
        observation,
        spfxSubjectAvailable,
        endUtc
      ).then(async completed => {
        const httpCompleted = clientHttpClass === undefined
          ? undefined
          : await completeClientHttpObservation(completed.canonicalJson, clientHttpClass)
            .catch(() => undefined);
        if (!disposed && generation.current === requestGeneration) {
          setState({
            kind: 'accessDenied',
            receiptJson: completed.canonicalJson,
            httpReceiptJson: httpCompleted?.canonicalJson
          });
        }
      }).catch(() => {
        // The product remains fail-closed and neutral; only the optional receipt is omitted.
      });
    };
    if (subjectId === undefined || subjectId.trim().length === 0) {
      const requestGeneration = generation.current + 1;
      generation.current = requestGeneration;
      let observation: ClientObservation | undefined;
      try {
        observation = beginClientObservation();
      } catch {
        observation = undefined;
      }
      closeDeniedObservation(observation, false, requestGeneration, 'none');
      return () => {
        disposed = true;
        generation.current += 1;
      };
    }

    let activeController: AbortController | undefined;
    let refreshTimer: number | undefined;
    let expiryTimer: number | undefined;
    let timeoutTimer: number | undefined;

    const clearTimer = (timer: number | undefined): void => {
      if (timer !== undefined) window.clearTimeout(timer);
    };
    const clearAllTimers = (): void => {
      clearTimer(refreshTimer);
      clearTimer(expiryTimer);
      clearTimer(timeoutTimer);
      refreshTimer = undefined;
      expiryTimer = undefined;
      timeoutTimer = undefined;
    };
    const discard = (kind: 'accessDenied' | 'unavailable', requestGeneration: number): void => {
      if (!disposed && generation.current === requestGeneration) {
        generation.current += 1;
        clearAllTimers();
        setSurface('workbench');
        setState({ kind });
      }
    };

    const startLoad = (isRefresh: boolean): void => {
      const requestGeneration = generation.current + 1;
      generation.current = requestGeneration;
      activeController?.abort();
      activeController = new AbortController();
      let observation: ClientObservation | undefined;
      let observationCorrelationId: string | undefined;
      try {
        observation = beginClientObservation();
        observationCorrelationId = observation.takeCorrelationIdForRequest();
      } catch {
        observation = undefined;
        observationCorrelationId = undefined;
      }
      clearTimer(refreshTimer);
      clearTimer(timeoutTimer);
      refreshTimer = undefined;
      timeoutTimer = window.setTimeout(() => {
        activeController?.abort();
        discard('unavailable', requestGeneration);
      }, LOAD_TIMEOUT_MS);
      if (!isRefresh) {
        clearTimer(expiryTimer);
        expiryTimer = undefined;
        setSurface('workbench');
        setState({ kind: 'loading' });
      }

      props.loadSnapshot(activeController.signal, observationCorrelationId).then(snapshot => {
        if (disposed || generation.current !== requestGeneration) return;
        clearAllTimers();
        const now = Date.now();
        const effectiveExpiry = snapshotEffectiveExpiry(snapshot);
        if (!Number.isFinite(effectiveExpiry) || effectiveExpiry <= now) {
          discard('unavailable', requestGeneration);
          return;
        }
        const remaining = effectiveExpiry - now;
        setState({ kind: 'ready', snapshot });
        refreshTimer = window.setTimeout(
          () => startLoad(true),
          Math.max(1, Math.floor(remaining * REFRESH_FRACTION))
        );
        expiryTimer = window.setTimeout(
          () => {
            if (!disposed) {
              generation.current += 1;
              activeController?.abort();
              clearAllTimers();
              setSurface('workbench');
              setState({ kind: 'unavailable' });
            }
          },
          remaining + 1
        );
      }).catch(error => {
        if (disposed || generation.current !== requestGeneration) return;
        const failure = classifyFailure(error);
        if (failure === 'accessDenied') {
          clearAllTimers();
          setSurface('workbench');
          const clientHttpClass = error instanceof NacBffHttpAccessDeniedError
            ? error.clientHttpClass
            : undefined;
          closeDeniedObservation(observation, true, requestGeneration, clientHttpClass);
        } else {
          discard(failure, requestGeneration);
        }
      });
    };

    startLoad(false);
    return () => {
      disposed = true;
      generation.current += 1;
      clearAllTimers();
      activeController?.abort();
    };
  }, [props.expectedSubjectId, props.loadSnapshot]);

  if (state.kind === 'loading') {
    return <HostMessage kind="status">Arbeitsbereich wird geladen.</HostMessage>;
  }
  if (state.kind === 'accessDenied') {
    const receiptJson = state.receiptJson;
    const httpReceiptJson = state.httpReceiptJson;
    return <div className="nacWorkbenchHost" data-nac-component="workbench-host-denied">
      <style>{nacWorkbenchHostStyleSheet}</style>
      <HostMessage kind="alert">Kein Zugriff auf diesen Arbeitsbereich.</HostMessage>
      {receiptJson !== undefined && <button
        type="button"
        className="nacWorkbenchHost__receiptDownload"
        onClick={() => (props.downloadReceipt ?? downloadClientObservationReceipt)(
          receiptJson
        )}
      >Diagnosebeleg speichern</button>}
      {httpReceiptJson !== undefined && <button
        type="button"
        className="nacWorkbenchHost__receiptDownload"
        onClick={() => (props.downloadHttpReceipt ?? downloadClientHttpObservationReceipt)(
          httpReceiptJson
        )}
      >HTTP-Diagnosebeleg speichern</button>}
    </div>;
  }
  if (state.kind === 'unavailable') {
    return <HostMessage kind="alert">Arbeitsbereich ist derzeit nicht verfügbar.</HostMessage>;
  }

  const tabIds: Record<HostSurface, string> = {
    workbench: hostId + '-tab-workbench',
    detail: hostId + '-tab-detail'
  };
  const panelIds: Record<HostSurface, string> = {
    workbench: hostId + '-panel-workbench',
    detail: hostId + '-panel-detail'
  };
  const selectTabFromKeyboard = (
    event: React.KeyboardEvent<HTMLButtonElement>,
    currentSurface: HostSurface
  ): void => {
    let nextSurface: HostSurface | undefined;
    if (event.key === 'ArrowRight') {
      nextSurface = currentSurface === 'workbench' ? 'detail' : 'workbench';
    } else if (event.key === 'ArrowLeft') {
      nextSurface = currentSurface === 'workbench' ? 'detail' : 'workbench';
    } else if (event.key === 'Home') {
      nextSurface = 'workbench';
    } else if (event.key === 'End') {
      nextSurface = 'detail';
    }
    if (nextSurface === undefined) return;
    event.preventDefault();
    setSurface(nextSurface);
    (nextSurface === 'workbench' ? workbenchTab : detailTab).current?.focus();
  };

  return <div className="nacWorkbenchHost" data-nac-component="workbench-host">
    <style>{nacWorkbenchHostStyleSheet}</style>
    <div
      className="nacWorkbenchHost__tabs"
      role="tablist"
      aria-label="Arbeitsansicht"
      aria-orientation="horizontal"
    >
      <button
        ref={workbenchTab}
        id={tabIds.workbench}
        type="button"
        role="tab"
        aria-selected={surface === 'workbench'}
        aria-controls={panelIds.workbench}
        tabIndex={surface === 'workbench' ? 0 : -1}
        onClick={() => setSurface('workbench')}
        onKeyDown={event => selectTabFromKeyboard(event, 'workbench')}
      >Arbeitsbereich</button>
      <button
        ref={detailTab}
        id={tabIds.detail}
        type="button"
        role="tab"
        aria-selected={surface === 'detail'}
        aria-controls={panelIds.detail}
        tabIndex={surface === 'detail' ? 0 : -1}
        onClick={() => setSurface('detail')}
        onKeyDown={event => selectTabFromKeyboard(event, 'detail')}
      >BPMN-Detail</button>
    </div>
    <div
      className="nacWorkbenchHost__tabpanel"
      id={panelIds.workbench}
      role="tabpanel"
      aria-labelledby={tabIds.workbench}
      hidden={surface !== 'workbench'}
    >
      {surface === 'workbench' && <WorkbenchPanel snapshot={state.snapshot} />}
    </div>
    <div
      className="nacWorkbenchHost__tabpanel"
      id={panelIds.detail}
      role="tabpanel"
      aria-labelledby={tabIds.detail}
      hidden={surface !== 'detail'}
    >
      {surface === 'detail' && props.detailSurface}
    </div>
  </div>;
}

function HostMessage(props: {
  readonly kind: 'status' | 'alert';
  readonly children: React.ReactNode;
}): React.ReactElement {
  return <div className="nacWorkbenchHost">
    <style>{nacWorkbenchHostStyleSheet}</style>
    <div className="nacWorkbenchHost__state" role={props.kind}>{props.children}</div>
  </div>;
}

function classifyFailure(error: unknown): 'accessDenied' | 'unavailable' {
  return error instanceof Error && error.message === 'NAC_BFF_ACCESS_DENIED'
    ? 'accessDenied'
    : 'unavailable';
}
