# ============================================================================
# qp_data/apps.py
# ============================================================================

from django.apps import AppConfig


class QpDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'qp_data'
    verbose_name = 'Question Paper Data Management'
