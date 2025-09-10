from django.urls import path
from . import views

app_name = 'answer_scripts'

urlpatterns = [
    # List and create
    path('', views.list_answer_scripts, name='list_answer_scripts'),
    path('create/', views.create_answer_script, name='create_answer_script'),
    path('search/', views.search_answer_scripts, name='search_answer_scripts'),
    
    # Get by ID
    path('id/<int:script_id>/', views.get_answer_script_by_id, name='get_answer_script_by_id'),
    path('id/<int:script_id>/update/', views.update_answer_script, name='update_answer_script'),
    path('id/<int:script_id>/delete/', views.delete_answer_script, name='delete_answer_script'),
    
    # Get by roll number and UUID
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/', 
         views.get_answer_script_by_roll_and_uuid, 
         name='get_answer_script_by_roll_and_uuid'),
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/images/', 
         views.get_image_urls_by_roll_and_uuid, 
         name='get_image_urls_by_roll_and_uuid'),
    
    # Filter by question paper UUID
    path('by-qp/<uuid:question_paper_uuid>/', 
         views.filter_by_question_paper, 
         name='filter_by_question_paper'),




    # List and create
    path('', views.list_answer_scripts, name='list_answer_scripts'),
    path('create/', views.create_answer_script, name='create_answer_script'),
    path('search/', views.search_answer_scripts, name='search_answer_scripts'),

    # NEW ENDPOINT - Add this line
    path('process-extraction/', views.process_extraction_results, name='process_extraction_results'),

    # Get by ID
    path('id/<int:script_id>/', views.get_answer_script_by_id, name='get_answer_script_by_id'),
    path('id/<int:script_id>/update/', views.update_answer_script, name='update_answer_script'),
    path('id/<int:script_id>/delete/', views.delete_answer_script, name='delete_answer_script'),

    # Get by roll number and UUID
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/',
         views.get_answer_script_by_roll_and_uuid,
         name='get_answer_script_by_roll_and_uuid'),
    path('roll/<str:roll_no>/uuid/<uuid:question_paper_uuid>/images/',
         views.get_image_urls_by_roll_and_uuid,
         name='get_image_urls_by_roll_and_uuid'),

    # Filter by question paper UUID
    path('by-qp/<uuid:question_paper_uuid>/',
         views.filter_by_question_paper,
         name='filter_by_question_paper'),


]