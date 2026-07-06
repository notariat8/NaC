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

-- Server-side portal sessions.
-- Scope: redacted runtime session metadata only; no tokens, claims, credentials or mandate data.

CREATE TABLE nac_sessions (
    session_id_hash VARCHAR2(64) NOT NULL,
    tenant_slug VARCHAR2(80) NOT NULL,
    subject_hash VARCHAR2(128) NOT NULL,
    role_class VARCHAR2(80) NOT NULL,
    usecase_slug VARCHAR2(120) NOT NULL,
    purpose VARCHAR2(80) NOT NULL,
    issued_at NUMBER(19) NOT NULL,
    expires_at NUMBER(19) NOT NULL,
    revoked_at NUMBER(19),
    audit_event_id VARCHAR2(120),
    contains_credentials NUMBER(1) DEFAULT 0 NOT NULL,
    tokens_stored NUMBER(1) DEFAULT 0 NOT NULL,
    claims_stored NUMBER(1) DEFAULT 0 NOT NULL,
    CONSTRAINT nac_sessions_pk PRIMARY KEY (session_id_hash),
    CONSTRAINT nac_sessions_time_ck CHECK (expires_at > issued_at),
    CONSTRAINT nac_sessions_guardrails_ck CHECK (
        contains_credentials = 0 AND tokens_stored = 0 AND claims_stored = 0
    )
);

CREATE INDEX nac_sessions_tenant_i
    ON nac_sessions (tenant_slug);

CREATE INDEX nac_sessions_subject_i
    ON nac_sessions (subject_hash);

CREATE INDEX nac_sessions_expiry_i
    ON nac_sessions (expires_at);
