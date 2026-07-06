-- NaC ATP agent runtime registry schema artifact.
-- Scope: safe agent, endpoint, sandbox binding and lease metadata only.
-- This artifact is contract-first. Applying it requires a separate Owner Apply gate.

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE q'[
        CREATE TABLE nac_agent_registry (
            agent_id VARCHAR2(128) NOT NULL,
            agent_type VARCHAR2(80) NOT NULL,
            runtime_class VARCHAR2(80) NOT NULL,
            capability_set VARCHAR2(160) NOT NULL,
            git_contract_reference VARCHAR2(240) NOT NULL,
            registry_status VARCHAR2(32) NOT NULL,
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_agent_registry_pk PRIMARY KEY (agent_id),
            CONSTRAINT nac_agent_registry_status_ck CHECK (
                registry_status IN ('prepared', 'active', 'suspended', 'retired')
            )
        )
    ]';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE q'[
        CREATE TABLE nac_agent_endpoints (
            endpoint_id VARCHAR2(128) NOT NULL,
            agent_id VARCHAR2(128) NOT NULL,
            target_host_label VARCHAR2(80) NOT NULL,
            connector_mode VARCHAR2(80) NOT NULL,
            endpoint_status VARCHAR2(32) NOT NULL,
            redacted_health_state VARCHAR2(160),
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_agent_endpoints_pk PRIMARY KEY (endpoint_id),
            CONSTRAINT nac_agent_endpoints_status_ck CHECK (
                endpoint_status IN ('prepared', 'connected', 'degraded', 'disconnected', 'revoked')
            ),
            CONSTRAINT nac_agent_endpoints_mode_ck CHECK (
                connector_mode IN ('outbound_mtls', 'outbound_websocket_https')
            ),
            CONSTRAINT nac_agent_endpoints_agent_fk FOREIGN KEY (agent_id)
                REFERENCES nac_agent_registry (agent_id)
        )
    ]';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE q'[
        CREATE TABLE nac_sandbox_bindings (
            sandbox_binding_id VARCHAR2(128) NOT NULL,
            tenant_id VARCHAR2(128) NOT NULL,
            user_binding_id VARCHAR2(128) NOT NULL,
            role_class VARCHAR2(80) NOT NULL,
            matter_id VARCHAR2(128),
            agent_id VARCHAR2(128) NOT NULL,
            sandbox_reference VARCHAR2(160) NOT NULL,
            binding_status VARCHAR2(32) NOT NULL,
            isolation_key VARCHAR2(80) NOT NULL,
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_sandbox_bindings_pk PRIMARY KEY (sandbox_binding_id),
            CONSTRAINT nac_sandbox_bindings_status_ck CHECK (
                binding_status IN ('prepared', 'active', 'revoked', 'expired')
            ),
            CONSTRAINT nac_sandbox_bindings_isolation_ck CHECK (
                isolation_key IN ('tenant_user', 'tenant_user_matter_role')
            ),
            CONSTRAINT nac_sandbox_bindings_tenant_fk FOREIGN KEY (tenant_id)
                REFERENCES nac_tenants (tenant_id),
            CONSTRAINT nac_sandbox_bindings_user_fk FOREIGN KEY (user_binding_id)
                REFERENCES nac_user_bindings (user_binding_id),
            CONSTRAINT nac_sandbox_bindings_agent_fk FOREIGN KEY (agent_id)
                REFERENCES nac_agent_registry (agent_id)
        )
    ]';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE q'[
        CREATE TABLE nac_sandbox_leases (
            sandbox_lease_id VARCHAR2(128) NOT NULL,
            sandbox_binding_id VARCHAR2(128) NOT NULL,
            lease_status VARCHAR2(32) NOT NULL,
            lease_started_at VARCHAR2(32) NOT NULL,
            lease_expires_at VARCHAR2(32) NOT NULL,
            revoked_at VARCHAR2(32),
            revocation_reason VARCHAR2(160),
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_sandbox_leases_pk PRIMARY KEY (sandbox_lease_id),
            CONSTRAINT nac_sandbox_leases_status_ck CHECK (
                lease_status IN ('prepared', 'active', 'expired', 'revoked')
            ),
            CONSTRAINT nac_sandbox_leases_binding_fk FOREIGN KEY (sandbox_binding_id)
                REFERENCES nac_sandbox_bindings (sandbox_binding_id)
        )
    ]';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE q'[
        CREATE TABLE nac_agent_session_bindings (
            agent_session_binding_id VARCHAR2(128) NOT NULL,
            session_reference_hash VARCHAR2(128) NOT NULL,
            sandbox_lease_id VARCHAR2(128) NOT NULL,
            binding_status VARCHAR2(32) NOT NULL,
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_agent_session_bindings_pk PRIMARY KEY (agent_session_binding_id),
            CONSTRAINT nac_agent_session_bindings_status_ck CHECK (
                binding_status IN ('prepared', 'active', 'revoked', 'expired')
            ),
            CONSTRAINT nac_agent_session_lease_fk FOREIGN KEY (sandbox_lease_id)
                REFERENCES nac_sandbox_leases (sandbox_lease_id)
        )
    ]';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_agent_endpoints_agent_i ON nac_agent_endpoints (agent_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_sandbox_bindings_tenant_i ON nac_sandbox_bindings (tenant_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_sandbox_bindings_user_i ON nac_sandbox_bindings (user_binding_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_sandbox_leases_binding_i ON nac_sandbox_leases (sandbox_binding_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_agent_session_lease_i ON nac_agent_session_bindings (sandbox_lease_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/
