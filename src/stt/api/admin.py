"""Django admin configuration for Multi-Tenant management (2f.7, ADR-09)."""

from django.contrib import admin

from .models import AuditLog, Job, ResultVersion, StorageConfig, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "short_id",
        "job_type",
        "status",
        "original_filename",
        "results_delivered",
        "tenant",
        "owner",
        "created_at",
    )
    list_filter = (
        "status",
        "job_type",
        "tenant",
        "enable_diarize",
        "results_delivered",
    )
    search_fields = ("id", "original_filename", "owner__username")
    readonly_fields = ("id", "created_at", "updated_at", "results_delivered_at")
    raw_id_fields = ("owner", "tenant")
    date_hierarchy = "created_at"

    @admin.display(description="Job ID")
    def short_id(self, obj: Job) -> str:
        return str(obj.id)[:8]


@admin.register(StorageConfig)
class StorageConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "backend_type", "is_default", "tenant", "created_at")
    list_filter = ("backend_type", "is_default", "tenant", "encrypt_at_rest")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at", "masked_s3_secret_key")
    raw_id_fields = ("tenant",)

    fieldsets = (
        (None, {"fields": ("id", "name", "backend_type", "is_default", "tenant")}),
        ("Pfade", {"fields": ("base_path",)}),
        (
            "S3-Konfiguration",
            {
                "fields": (
                    "s3_endpoint_url",
                    "s3_bucket",
                    "s3_access_key",
                    "masked_s3_secret_key",
                    "s3_region",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Sicherheit", {"fields": ("encrypt_at_rest",)}),
        ("Zeitstempel", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="S3 Secret Key")
    def masked_s3_secret_key(self, obj: StorageConfig) -> str:
        if obj.s3_secret_key:
            return f"{'*' * 20}{obj.s3_secret_key[-4:]}"
        return ""


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "actor",
        "resource_type",
        "resource_id",
        "tenant",
    )
    list_filter = ("action", "tenant", "resource_type")
    search_fields = ("actor", "resource_id", "detail")
    readonly_fields = [
        f.name for f in AuditLog._meta.get_fields() if hasattr(f, "name")
    ]
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # type: ignore[override]
        return False


@admin.register(ResultVersion)
class ResultVersionAdmin(admin.ModelAdmin):
    list_display = ("job", "version", "source", "created_at")
    list_filter = ("source",)
    search_fields = ("job__id",)
    readonly_fields = ("id", "created_at")
    raw_id_fields = ("job",)
