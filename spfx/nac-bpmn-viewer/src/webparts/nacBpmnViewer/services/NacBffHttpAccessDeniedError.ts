// An actual workbench response is the only source of this closed client status.
// The product message remains deliberately neutral.
export class NacBffHttpAccessDeniedError extends Error {
  public readonly clientHttpClass: '401' | '403';

  public constructor(status: 401 | 403) {
    super('NAC_BFF_ACCESS_DENIED');
    Object.setPrototypeOf(this, NacBffHttpAccessDeniedError.prototype);
    this.name = 'NacBffHttpAccessDeniedError';
    this.clientHttpClass = status === 401 ? '401' : '403';
  }
}
