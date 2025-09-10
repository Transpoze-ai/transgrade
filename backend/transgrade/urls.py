from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/answer-scripts/', include('answer_scripts.urls')),
    path('api/ocr-data/',include('ocr_data.urls')),
    path('api/chunk-data/', include('chunk_data.urls')),
    path('api/qa-data/', include('qa_data.urls')), 
    path('api/qp-data/', include('qp_data.urls')),
    path('api/pipeline/', include('pipeline.urls')),
]