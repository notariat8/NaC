-- NaC ATP runtime anchor schema artifact.
-- Scope: safe runtime metadata anchors only; no mandate data and no secret values.
-- This artifact is contract-first. Applying it requires a separate Owner Apply gate.

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE q'[
        CREATE TABLE nac_tenants (
            tenant_id VARCHAR2(128) NOT NULL,
            tenant_slug VARCHAR2(80) NOT NULL,
            public_label VARCHAR2(160) NOT NULL,
            tenant_status VARCHAR2(32) NOT NULL,
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_tenants_pk PRIMARY KEY (tenant_id),
            CONSTRAINT nac_tenants_slug_uq UNIQUE (tenant_slug),
            CONSTRAINT nac_tenants_status_ck CHECK (
                tenant_status IN ('prepared', 'active', 'suspended', 'archived')
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
        CREATE TABLE nac_user_bindings (
            user_binding_id VARCHAR2(128) NOT NULL,
            tenant_id VARCHAR2(128) NOT NULL,
            subject_hash VARCHAR2(128) NOT NULL,
            role_class VARCHAR2(80) NOT NULL,
            binding_status VARCHAR2(32) NOT NULL,
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_user_bindings_pk PRIMARY KEY (user_binding_id),
            CONSTRAINT nac_user_bindings_status_ck CHECK (
                binding_status IN ('prepared', 'active', 'revoked', 'expired')
            ),
            CONSTRAINT nac_user_bindings_tenant_fk FOREIGN KEY (tenant_id)
                REFERENCES nac_tenants (tenant_id)
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
        CREATE TABLE nac_matters (
            matter_id VARCHAR2(128) NOT NULL,
            tenant_id VARCHAR2(128) NOT NULL,
            matter_type VARCHAR2(80) NOT NULL,
            matter_status VARCHAR2(32) NOT NULL,
            redacted_reference VARCHAR2(160) NOT NULL,
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_matters_pk PRIMARY KEY (matter_id),
            CONSTRAINT nac_matters_status_ck CHECK (
                matter_status IN ('prepared', 'open', 'blocked', 'closed', 'archived')
            ),
            CONSTRAINT nac_matters_tenant_fk FOREIGN KEY (tenant_id)
                REFERENCES nac_tenants (tenant_id)
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
        CREATE TABLE nac_process_templates (
            process_template_id VARCHAR2(128) NOT NULL,
            template_slug VARCHAR2(120) NOT NULL,
            git_reference VARCHAR2(240) NOT NULL,
            template_version VARCHAR2(80) NOT NULL,
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_process_templates_pk PRIMARY KEY (process_template_id),
            CONSTRAINT nac_process_templates_git_uq UNIQUE (template_slug, git_reference)
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
        CREATE TABLE nac_process_instances (
            process_instance_id VARCHAR2(128) NOT NULL,
            tenant_id VARCHAR2(128) NOT NULL,
            matter_id VARCHAR2(128) NOT NULL,
            process_template_id VARCHAR2(128) NOT NULL,
            process_status VARCHAR2(32) NOT NULL,
            duration_band VARCHAR2(80),
            critical_path_status VARCHAR2(80),
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            updated_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_process_instances_pk PRIMARY KEY (process_instance_id),
            CONSTRAINT nac_process_instances_status_ck CHECK (
                process_status IN ('prepared', 'active', 'waiting_external', 'blocked', 'completed', 'cancelled')
            ),
            CONSTRAINT nac_process_instances_tenant_fk FOREIGN KEY (tenant_id)
                REFERENCES nac_tenants (tenant_id),
            CONSTRAINT nac_process_instances_matter_fk FOREIGN KEY (matter_id)
                REFERENCES nac_matters (matter_id),
            CONSTRAINT nac_process_instances_template_fk FOREIGN KEY (process_template_id)
                REFERENCES nac_process_templates (process_template_id)
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
        CREATE TABLE nac_process_events (
            process_event_id VARCHAR2(128) NOT NULL,
            tenant_id VARCHAR2(128) NOT NULL,
            process_instance_id VARCHAR2(128) NOT NULL,
            event_type VARCHAR2(80) NOT NULL,
            event_status VARCHAR2(32) NOT NULL,
            redacted_external_system_label VARCHAR2(120),
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_process_events_pk PRIMARY KEY (process_event_id),
            CONSTRAINT nac_process_events_status_ck CHECK (
                event_status IN ('recorded', 'waiting_external', 'completed', 'failed', 'cancelled')
            ),
            CONSTRAINT nac_process_events_tenant_fk FOREIGN KEY (tenant_id)
                REFERENCES nac_tenants (tenant_id),
            CONSTRAINT nac_process_events_instance_fk FOREIGN KEY (process_instance_id)
                REFERENCES nac_process_instances (process_instance_id)
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
        CREATE TABLE nac_audit_events (
            audit_event_id VARCHAR2(128) NOT NULL,
            tenant_id VARCHAR2(128) NOT NULL,
            audit_subject_type VARCHAR2(80) NOT NULL,
            audit_status VARCHAR2(32) NOT NULL,
            redacted_actor_reference VARCHAR2(160),
            payload_json CLOB CHECK (payload_json IS JSON),
            created_at VARCHAR2(32) NOT NULL,
            CONSTRAINT nac_audit_events_pk PRIMARY KEY (audit_event_id),
            CONSTRAINT nac_audit_events_status_ck CHECK (
                audit_status IN ('recorded', 'reviewed', 'rejected', 'superseded')
            ),
            CONSTRAINT nac_audit_events_tenant_fk FOREIGN KEY (tenant_id)
                REFERENCES nac_tenants (tenant_id)
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
    EXECUTE IMMEDIATE 'CREATE INDEX nac_user_bindings_tenant_i ON nac_user_bindings (tenant_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_user_bindings_subject_i ON nac_user_bindings (subject_hash)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_matters_tenant_i ON nac_matters (tenant_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_process_instances_tenant_i ON nac_process_instances (tenant_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_process_instances_matter_i ON nac_process_instances (matter_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_process_events_tenant_i ON nac_process_events (tenant_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_process_events_instance_i ON nac_process_events (process_instance_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/

DECLARE
    already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT(already_exists, -955);
BEGIN
    EXECUTE IMMEDIATE 'CREATE INDEX nac_audit_events_tenant_i ON nac_audit_events (tenant_id)';
EXCEPTION
    WHEN already_exists THEN NULL;
END;
/
