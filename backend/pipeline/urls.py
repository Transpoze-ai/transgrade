# pipeline/urls.py - URL Configuration for Pipeline APIs

from django.urls import path
from . import views

urlpatterns = [
    # Main pipeline endpoints
    path('start/', views.start_pdf_pipeline, name='start_pdf_pipeline'),
    path('job/<str:job_id>/status/', views.job_status, name='job_status'),
    path('student/<str:question_paper_uuid>/<str:roll_no>/status/', views.student_status, name='student_status'),
    
    # Management endpoints
    path('dashboard/', views.pipeline_dashboard, name='pipeline_dashboard'),
    path('queue/status/', views.queue_status, name='queue_status'),
    path('workers/restart/', views.restart_pipeline_workers, name='restart_workers'),
    
    # Retry endpoints
    path('student/<str:question_paper_uuid>/<str:roll_no>/retry/', views.retry_failed_student, name='retry_student'),
]