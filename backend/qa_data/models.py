from django.db import models
import uuid


class QAData(models.Model):
    id = models.AutoField(primary_key=True)
    question_paper_uuid = models.UUIDField(help_text="UUID of the question paper")
    roll_no = models.CharField(max_length=50, help_text="Student roll number")
    qa_mapping = models.JSONField(help_text="Complete QA mapping JSON data")
    vlm_json = models.JSONField(null=True, blank=True, help_text="VLM JSON data")
    vlm_restructured_json = models.JSONField(null=True, blank=True, help_text="VLM restructured JSON data")
    total_questions_processed = models.PositiveIntegerField(default=0, help_text="Number of questions processed")
    processing_timestamp = models.DateTimeField(null=True, blank=True, help_text="Processing timestamp from JSON")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'qa_data'
        verbose_name = 'QA Data'
        verbose_name_plural = 'QA Data'
        unique_together = ('roll_no', 'question_paper_uuid')
        indexes = [
            models.Index(fields=['roll_no']),
            models.Index(fields=['question_paper_uuid']),
            models.Index(fields=['question_paper_uuid', 'roll_no']),
        ]
        ordering = ['question_paper_uuid', 'roll_no']

    def __str__(self):
        return f"QA ID: {self.id} - Roll: {self.roll_no} - QP: {self.question_paper_uuid}"

    def get_questions_count(self):
        """Get the number of questions in qa_mapping"""
        if self.qa_mapping and isinstance(self.qa_mapping, list):
            return len(self.qa_mapping)
        return 0

    def get_answered_questions_count(self):
        """Get the number of questions that have student answers (not PARSING_ERROR)"""
        if self.qa_mapping and isinstance(self.qa_mapping, list):
            answered_count = 0
            for item in self.qa_mapping:
                if isinstance(item, dict) and 'student_answer' in item:
                    if item['student_answer'] != 'PARSING_ERROR':
                        answered_count += 1
            return answered_count
        return 0

    def get_parsing_errors_count(self):
        """Get the number of questions with parsing errors"""
        if self.qa_mapping and isinstance(self.qa_mapping, list):
            error_count = 0
            for item in self.qa_mapping:
                if isinstance(item, dict) and 'student_answer' in item:
                    if item['student_answer'] == 'PARSING_ERROR':
                        error_count += 1
            return error_count
        return 0

    def has_vlm_data(self):
        """Check if VLM JSON data exists"""
        return bool(self.vlm_json)

    def has_vlm_restructured_data(self):
        """Check if VLM restructured JSON data exists"""
        return bool(self.vlm_restructured_json)

    def get_vlm_items_count(self):
        """Get count of items in vlm_json"""
        if self.vlm_json:
            if isinstance(self.vlm_json, list):
                return len(self.vlm_json)
            elif isinstance(self.vlm_json, dict):
                return len(self.vlm_json.keys())
        return 0

    def get_vlm_restructured_items_count(self):
        """Get count of items in vlm_restructured_json"""
        if self.vlm_restructured_json:
            if isinstance(self.vlm_restructured_json, list):
                return len(self.vlm_restructured_json)
            elif isinstance(self.vlm_restructured_json, dict):
                return len(self.vlm_restructured_json.keys())
        return 0

    def save(self, *args, **kwargs):
        """Override save to update total_questions_processed"""
        if self.qa_mapping:
            self.total_questions_processed = self.get_questions_count()
        super().save(*args, **kwargs)