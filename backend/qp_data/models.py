# ============================================================================
# qp_data/models.py
# ============================================================================

from django.db import models
import uuid


class QPData(models.Model):
    id = models.AutoField(primary_key=True)
    question_paper_uuid = models.UUIDField(
        unique=True,
        help_text="Unique UUID for the question paper"
    )
    ocr_json = models.JSONField(
        help_text="OCR JSON data from ML processing",
        null=True,
        blank=True
    )
    rubric_json = models.JSONField(
        help_text="Rubric JSON data from ML processing",
        null=True,
        blank=True
    )
    reference_json = models.JSONField(
        help_text="Reference JSON data from ML processing",
        null=True,
        blank=True
    )
    vlm_json = models.JSONField(
        help_text="VLM JSON data from ML processing",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'qp_data'
        verbose_name = 'Question Paper Data'
        verbose_name_plural = 'Question Paper Data'
        indexes = [
            models.Index(fields=['question_paper_uuid']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"QP Data ID: {self.id} - UUID: {self.question_paper_uuid}"

    def has_ocr_data(self):
        """Check if OCR data exists"""
        return self.ocr_json is not None and bool(self.ocr_json)

    def has_rubric_data(self):
        """Check if Rubric data exists"""
        return self.rubric_json is not None and bool(self.rubric_json)

    def has_reference_data(self):
        """Check if Reference data exists"""
        return self.reference_json is not None and bool(self.reference_json)

    def has_vlm_data(self):
        """Check if VLM data exists"""
        return self.vlm_json is not None and bool(self.vlm_json)

    def is_complete(self):
        """Check if OCR, Rubric, Reference and VLM data exist"""
        return (self.has_ocr_data() and self.has_rubric_data() and 
                self.has_reference_data() and self.has_vlm_data())

    def get_ocr_summary(self):
        """Get summary of OCR data"""
        if not self.has_ocr_data():
            return "No OCR data"
        
        if isinstance(self.ocr_json, dict):
            return f"OCR data with {len(self.ocr_json)} keys"
        elif isinstance(self.ocr_json, list):
            return f"OCR data with {len(self.ocr_json)} items"
        else:
            return "OCR data available"

    def get_rubric_summary(self):
        """Get summary of Rubric data"""
        if not self.has_rubric_data():
            return "No Rubric data"
        
        if isinstance(self.rubric_json, dict):
            return f"Rubric data with {len(self.rubric_json)} keys"
        elif isinstance(self.rubric_json, list):
            return f"Rubric data with {len(self.rubric_json)} items"
        else:
            return "Rubric data available"

    def get_reference_summary(self):
        """Get summary of Reference data"""
        if not self.has_reference_data():
            return "No Reference data"
        
        if isinstance(self.reference_json, dict):
            return f"Reference data with {len(self.reference_json)} keys"
        elif isinstance(self.reference_json, list):
            return f"Reference data with {len(self.reference_json)} items"
        else:
            return "Reference data available"

    def get_vlm_summary(self):
        """Get summary of VLM data"""
        if not self.has_vlm_data():
            return "No VLM data"
        
        if isinstance(self.vlm_json, dict):
            return f"VLM data with {len(self.vlm_json)} keys"
        elif isinstance(self.vlm_json, list):
            return f"VLM data with {len(self.vlm_json)} items"
        else:
            return "VLM data available"