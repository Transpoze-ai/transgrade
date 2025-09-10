# models.py for chunk_data app
from django.db import models


class ChunkData(models.Model):
    id = models.AutoField(primary_key=True)
    question_paper_uuid = models.UUIDField(help_text="UUID of the question paper")
    roll_no = models.CharField(max_length=50, help_text="Student roll number")
    chunk_data = models.JSONField(help_text="Complete chunks JSON data")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chunk_data'
        verbose_name = 'Chunk Data'
        verbose_name_plural = 'Chunk Data'
        # Composite unique constraint: combination of roll_no and question_paper_uuid must be unique
        unique_together = ('roll_no', 'question_paper_uuid')
        indexes = [
            models.Index(fields=['roll_no']),
            models.Index(fields=['question_paper_uuid']),
            models.Index(fields=['question_paper_uuid', 'roll_no']),
        ]
        ordering = ['question_paper_uuid', 'roll_no']

    def __str__(self):
        return f"Chunk ID: {self.id} - Roll: {self.roll_no} - QP: {self.question_paper_uuid}"

    def get_total_chunks(self):
        """Get total number of chunks"""
        if self.chunk_data and isinstance(self.chunk_data, dict):
            return self.chunk_data.get('total_chunks', 0)
        return 0

    def get_total_pages(self):
        """Get total number of pages"""
        if self.chunk_data and isinstance(self.chunk_data, dict):
            return self.chunk_data.get('total_pages', 0)
        return 0

    def get_chunks(self):
        """Get chunks array from chunk_data"""
        if self.chunk_data and isinstance(self.chunk_data, dict):
            return self.chunk_data.get('chunks', [])
        return []

    def get_page_info(self):
        """Get page_info array from chunk_data"""
        if self.chunk_data and isinstance(self.chunk_data, dict):
            return self.chunk_data.get('page_info', [])
        return []