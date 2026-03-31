"""PostgreSQL Row-Level Security policies for multi-tenancy (FA-25, 2f.2).

Enables RLS on api_job, api_storageconfig, and api_auditlog tables.
Policies restrict row access to the current tenant set via
``SET app.current_tenant_id``.

The TenantMiddleware sets this session variable before each request.
"""

from django.db import migrations

_TABLES = ["api_job", "api_storageconfig", "api_auditlog"]


def enable_rls(apps, schema_editor):
    """Enable RLS and create isolation policies."""
    for table in _TABLES:
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        schema_editor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

        # Policy: rows visible only when tenant_id matches session variable,
        #         OR tenant_id IS NULL (backward compat / single-tenant mode).
        schema_editor.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', true)
                OR tenant_id IS NULL
                OR current_setting('app.current_tenant_id', true) = ''
            );
        """)


def disable_rls(apps, schema_editor):
    """Reverse: drop policies and disable RLS."""
    for table in _TABLES:
        schema_editor.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0006_add_tenant_model_and_tenant_fks"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
