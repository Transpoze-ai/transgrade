from django.urls import path
from . import views

app_name = 'qa_data'

urlpatterns = [
    # Process QA JSON endpoint
    path('process-qa-json/', views.process_qa_json, name='process_qa_json'),
    
    # CRUD operations
    path('', views.list_qa_data, name='list_qa_data'),
    path('create/', views.create_qa_data, name='create_qa_data'),
    path('search/', views.search_qa_data, name='search_qa_data'),
    path('bulk-create/', views.bulk_create_qa_data, name='bulk_create_qa_data'),

    # Get by ID
    path('id/<int:qa_id>/', views.get_qa_data_by_id, name='get_qa_data_by_id'),
    path('id/<int:qa_id>/update/', views.update_qa_data, name='update_qa_data'),
    path('id/<int:qa_id>/delete/', views.delete_qa_data, name='delete_qa_data'),

    # VLM-specific operations
    path('id/<int:qa_id>/vlm/', views.get_vlm_data, name='get_vlm_data'),
    path('id/<int:qa_id>/vlm/update/', views.update_vlm_data, name='update_vlm_data'),
    path('id/<int:qa_id>/vlm/delete/', views.delete_vlm_data, name='delete_vlm_data'),
    
    # VLM operations by roll and UUID
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/vlm/',
         views.get_vlm_data_by_roll_and_uuid,
         name='get_vlm_data_by_roll_and_uuid'),
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/vlm/update/',
         views.update_vlm_data_by_roll_and_uuid,
         name='update_vlm_data_by_roll_and_uuid'),

    # Get by roll number and UUID
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/',
         views.get_qa_data_by_roll_and_uuid,
         name='get_qa_data_by_roll_and_uuid'),

    # Filter by question paper UUID
    path('by-qp/<uuid:question_paper_uuid>/',
         views.filter_by_question_paper,
         name='filter_by_question_paper'),
]