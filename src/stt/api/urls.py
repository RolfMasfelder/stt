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
]
