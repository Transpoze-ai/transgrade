# apps.py for chunk_data app
from django.apps import AppConfig


class ChunkDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chunk_data'
    verbose_name = 'Chunk Data Management'