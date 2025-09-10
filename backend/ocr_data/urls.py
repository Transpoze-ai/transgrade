from django.urls import path
from . import views

app_name = 'ocr_data'

urlpatterns = [
    # NEW: Process OCR JSON endpoint
    path('process-ocr-json/', views.process_ocr_json, name='process_ocr_json'),
    
    # List and create
    path('', views.list_ocr_data, name='list_ocr_data'),
    path('create/', views.create_ocr_data, name='create_ocr_data'),
    path('bulk-create/', views.bulk_create_ocr_data, name='bulk_create_ocr_data'),
    path('search/', views.search_ocr_data, name='search_ocr_data'),

    # Get by ID
    path('id/<int:ocr_id>/', views.get_ocr_data_by_id, name='get_ocr_data_by_id'),
    path('id/<int:ocr_id>/update/', views.update_ocr_data, name='update_ocr_data'),
    path('id/<int:ocr_id>/delete/', views.delete_ocr_data, name='delete_ocr_data'),

    # Get by roll number and UUID
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/',
         views.get_ocr_data_by_roll_and_uuid,
         name='get_ocr_data_by_roll_and_uuid'),

    # Get by roll number, UUID, and page number
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/page/<int:page_number>/',
         views.get_ocr_data_by_roll_uuid_page,
         name='get_ocr_data_by_roll_uuid_page'),

    # Filter by question paper UUID
    path('by-qp/<uuid:question_paper_uuid>/',
         views.filter_by_question_paper,
         name='filter_by_question_paper'),
]