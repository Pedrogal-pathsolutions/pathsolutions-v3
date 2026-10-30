"""Minimal schema of Phase 4 (plan, sections 9.1 and 19.2): tenants, slides and jobs.

Revision ID: 0001
"""
from alembic import op

revision = "0001"
down_revision = None

# A transaction that set the tenant leaves it as '' in the session: nullif
# makes that read nothing, like an unset tenant, instead of failing on the cast.
TENANT = "nullif(current_setting('app.tenant_id', true), '')::uuid"

# The pointer of a .h5 and of the focus scores starts with its own tenant and
# slide; the middle part is the short hash of the extractor_version.
POINTER = r"'^' || tenant_id::text || '/' || slide_id::text || '/[0-9a-f]{{12}}/' || id::text || '\.{suffix}$'"


def upgrade():
    op.execute(
        rf"""
        -- The WSI container of a tenant is wsi-<slug> (infra/terraform/main/wsi.tf).
        create table tenants (
            id uuid primary key,
            slug text not null unique check (slug ~ '^[a-z0-9]{{2,20}}$'),
            created_at timestamptz not null default now()
        );

        create table slides (
            tenant_id uuid not null references tenants (id),
            id uuid primary key,
            -- Named after the slide, never after the scanner's file, which can carry the case number.
            wsi_name text not null check (wsi_name ~ ('^' || id::text || '\.[a-z0-9]{{2,5}}$')),
            wsi_sha256 text not null check (wsi_sha256 ~ '^[0-9a-f]{{64}}$'),
            organ text check (organ ~ '^[a-z_]{{2,40}}$'),
            material text not null check (material in ('biopsia', 'peca', 'citologia')),
            stain text not null check (stain ~ '^[A-Z0-9_]{{1,20}}$'),
            created_at timestamptz not null default now(),
            unique (tenant_id, id)
        );

        create table jobs (
            tenant_id uuid not null,
            id uuid primary key,
            slide_id uuid not null,
            status text not null default 'QUEUED'
                check (status in ('QUEUED', 'RUNNING', 'COMPLETED', 'QC_FAILED', 'UNSUPPORTED_FORMAT', 'DEAD_LETTER')),
            -- What the lab sees (pathsol-contrato-h5, terminal states).
            reason text,
            -- Technical failures, counted here and not by queue deliveries (plan 9.1).
            attempt integer not null default 0 check (attempt >= 0),
            pipeline_version text not null,
            extractor_version text,
            h5_blob text,
            h5_size bigint check (h5_size > 0),
            h5_sha256 text check (h5_sha256 ~ '^[0-9a-f]{{64}}$'),
            qc_scores_blob text,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now(),
            unique (tenant_id, id),
            foreign key (tenant_id, slide_id) references slides (tenant_id, id),
            check (case status
                when 'QC_FAILED' then coalesce(reason in ('empty_glass', 'insufficient_material', 'focus'), false)
                when 'UNSUPPORTED_FORMAT' then coalesce(reason in ('format', 'scale_unavailable'), false)
                else reason is null
            end),
            -- The commit of a .h5 is its pointer, written with COMPLETED in one transaction.
            check ((status = 'COMPLETED') = (h5_blob is not null)),
            check (h5_blob is null or (h5_size is not null and h5_sha256 is not null and extractor_version is not null)),
            check (h5_blob ~ ({POINTER.format(suffix="h5")})),
            check ((qc_scores_blob is not null) = coalesce(status = 'QC_FAILED' and reason = 'focus', false)),
            check (qc_scores_blob ~ ({POINTER.format(suffix=r"qc\.h5")}))
        );

        alter table tenants enable row level security;
        alter table tenants force row level security;
        create policy isolamento on tenants using (id = {TENANT}) with check (id = {TENANT});

        alter table slides enable row level security;
        alter table slides force row level security;
        create policy isolamento on slides using (tenant_id = {TENANT}) with check (tenant_id = {TENANT});

        alter table jobs enable row level security;
        alter table jobs force row level security;
        create policy isolamento on jobs using (tenant_id = {TENANT}) with check (tenant_id = {TENANT});

        -- The worker reads the job and its slide and moves only the state columns.
        grant select on tenants, slides to pathsol_worker;
        grant select, update (status, reason, attempt, extractor_version, h5_blob, h5_size, h5_sha256,
                              qc_scores_blob, updated_at) on jobs to pathsol_worker;
        -- Decision 7: the test producer, until Phase 5.
        grant select on tenants to pathsol_produtor;
        grant insert on slides, jobs to pathsol_produtor
        """
    )
