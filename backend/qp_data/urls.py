# ============================================================================
# qp_data/urls.py
# ============================================================================

from django.urls import path
from . import views

app_name = 'qp_data'

urlpatterns = [
    # Process QP JSON from ML
    path('process-qp-json/', views.process_qp_json, name='process_qp_json'),
    path('process-rubric/', views.process_rubric_data, name='process_rubric_data'),
    path('process-rubric-separate/', views.process_rubric_separate, name='process_rubric_separate'),
    
    # CRUD operations
    path('', views.list_qp_data, name='list_qp_data'),
    path('create/', views.create_qp_data, name='create_qp_data'),
    path('search/', views.search_qp_data, name='search_qp_data'),
    path('status/', views.get_qp_data_status, name='get_qp_data_status'),

    # Get by ID
    path('id/<int:qp_id>/', views.get_qp_data_by_id, name='get_qp_data_by_id'),
    path('id/<int:qp_id>/update/', views.update_qp_data, name='update_qp_data'),
    path('id/<int:qp_id>/delete/', views.delete_qp_data, name='delete_qp_data'),

    # Get by UUID
    path('uuid/<uuid:question_paper_uuid>/', views.get_qp_data_by_uuid, name='get_qp_data_by_uuid'),
]