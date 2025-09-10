# urls.py for chunk_data app
from django.urls import path
from . import views

app_name = 'chunk_data'

urlpatterns = [
    # NEW: Process chunk JSON endpoint
    path('process-chunk-json/', views.process_chunk_json, name='process_chunk_json'),
    
    # List and create
    path('', views.list_chunk_data, name='list_chunk_data'),
    path('create/', views.create_chunk_data, name='create_chunk_data'),
    path('search/', views.search_chunk_data, name='search_chunk_data'),

    # Get by ID
    path('id/<int:chunk_id>/', views.get_chunk_data_by_id, name='get_chunk_data_by_id'),
    path('id/<int:chunk_id>/update/', views.update_chunk_data, name='update_chunk_data'),
    path('id/<int:chunk_id>/delete/', views.delete_chunk_data, name='delete_chunk_data'),

    # Get by roll number and UUID
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/',
         views.get_chunk_data_by_roll_and_uuid,
         name='get_chunk_data_by_roll_and_uuid'),

    # Filter by question paper UUID
    path('by-qp/<uuid:question_paper_uuid>/',
         views.filter_by_question_paper,
         name='filter_by_question_paper'),
]