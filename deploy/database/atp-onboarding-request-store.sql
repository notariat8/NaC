-- NaC ATP onboarding request store bootstrap.
-- Scope: customer onboarding request metadata only; no mandate data.

CREATE TABLE onboarding_requests (
    request_id VARCHAR2(96) NOT NULL,
    tenant_id VARCHAR2(128) NOT NULL,
    tenant_slug VARCHAR2(64) NOT NULL,
    domain VARCHAR2(253) NOT NULL,
    admin_email VARCHAR2(254) NOT NULL,
    dns_status VARCHAR2(32) NOT NULL,
    request_status VARCHAR2(32) NOT NULL,
    invitation_status VARCHAR2(32) NOT NULL,
    created_at VARCHAR2(32) NOT NULL,
    updated_at VARCHAR2(32) NOT NULL,
    created_by_surface VARCHAR2(128) NOT NULL,
    CONSTRAINT onboarding_requests_pk PRIMARY KEY (request_id),
    CONSTRAINT onboarding_requests_dns_status_ck CHECK (dns_status IN ('verified')),
    CONSTRAINT onboarding_requests_request_status_ck CHECK (
        request_status IN ('submitted', 'in_review', 'approved', 'rejected', 'cancelled')
    ),
    CONSTRAINT onboarding_requests_invitation_status_ck CHECK (
        invitation_status IN ('not_sent', 'sent', 'failed')
    )
);

CREATE INDEX onboarding_requests_tenant_slug_i
    ON onboarding_requests (tenant_slug);

CREATE INDEX onboarding_requests_domain_i
    ON onboarding_requests (domain);

CREATE INDEX onboarding_requests_created_at_i
    ON onboarding_requests (created_at);
