"""URL patterns for the STT API."""

from django.urls import path

from . import views

urlpatterns = [
    path("health", views.HealthView.as_view(), name="health"),
    path("v1/transcribe", views.TranscribeView.as_view(), name="transcribe"),
    path("v1/diarize", views.DiarizeView.as_view(), name="diarize"),
    path("v1/process", views.ProcessView.as_view(), name="process"),
    path("v1/jobs", views.JobCreateView.as_view(), name="job-create"),
    path("v1/jobs/<str:job_id>", views.JobDetailView.as_view(), name="job-detail"),
    # Correction workflow (2d)
    path(
        "v1/jobs/<str:job_id>/correct",
        views.JobUpdateView.as_view(),
        name="job-correct",
    ),
    path(
        "v1/jobs/<str:job_id>/reprocess",
        views.JobReprocessView.as_view(),
        name="job-reprocess",
    ),
    path(
        "v1/jobs/<str:job_id>/versions",
        views.JobVersionListView.as_view(),
        name="job-versions",
    ),
    # Storage config (ADR-12)
    path(
        "v1/config/storage",
        views.StorageConfigListView.as_view(),
        name="storage-config-list",
    ),
    path(
        "v1/config/storage/<str:config_id>",
        views.StorageConfigDetailView.as_view(),
        name="storage-config-detail",
    ),
    path(
        "v1/config/storage/<str:config_id>/test",
        views.StorageConfigTestView.as_view(),
        name="storage-config-test",
    ),
    # GDPR endpoints (2e)
    path(
        "v1/jobs/<str:job_id>/delete",
        views.JobDeleteView.as_view(),
        name="job-delete",
    ),
    path(
        "v1/user/data",
        views.UserDataDeleteView.as_view(),
        name="user-data-delete",
    ),
    path(
        "v1/user/data/export",
        views.UserDataExportView.as_view(),
        name="user-data-export",
    ),
]
