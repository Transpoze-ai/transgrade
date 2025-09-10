from django.db import models


class OCRData(models.Model):
    id = models.AutoField(primary_key=True)
    question_paper_uuid = models.UUIDField(help_text="UUID of the question paper")
    roll_no = models.CharField(max_length=50, help_text="Student roll number")
    page_number = models.PositiveIntegerField(help_text="Page number of the answer script")
    ocr_json_dump = models.JSONField(help_text="Complete OCR response JSON data")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ocr_data'
        verbose_name = 'OCR Data'
        verbose_name_plural = 'OCR Data'
        # Composite unique constraint: combination of roll_no, question_paper_uuid, and page_number must be unique
        unique_together = ('roll_no', 'question_paper_uuid', 'page_number')
        indexes = [
            models.Index(fields=['roll_no']),
            models.Index(fields=['question_paper_uuid']),
            models.Index(fields=['question_paper_uuid', 'roll_no']),
            models.Index(fields=['question_paper_uuid', 'roll_no', 'page_number']),
        ]
        ordering = ['question_paper_uuid', 'roll_no', 'page_number']

    def __str__(self):
        return f"OCR ID: {self.id} - Roll: {self.roll_no} - QP: {self.question_paper_uuid} - Page: {self.page_number}"

    def get_text_content(self):
        """Extract text content from OCR JSON if available"""
        if self.ocr_json_dump and isinstance(self.ocr_json_dump, dict):
            # Check if extracted_text exists and extract text from it
            if 'extracted_text' in self.ocr_json_dump and self.ocr_json_dump['extracted_text']:
                texts = []
                for text_item in self.ocr_json_dump['extracted_text']:
                    if isinstance(text_item, dict) and 'text' in text_item:
                        texts.append(text_item['text'])
                return ' '.join(texts)
            # Fallback to generic fields
            return self.ocr_json_dump.get('text', '') or self.ocr_json_dump.get('content', '')
        return ""

    def get_confidence_score(self):
        """Extract average confidence score from OCR JSON if available"""
        if self.ocr_json_dump and isinstance(self.ocr_json_dump, dict):
            # Calculate average confidence from extracted_text
            if 'extracted_text' in self.ocr_json_dump and self.ocr_json_dump['extracted_text']:
                confidences = []
                for text_item in self.ocr_json_dump['extracted_text']:
                    if isinstance(text_item, dict) and 'confidence' in text_item:
                        confidences.append(float(text_item['confidence']))
                if confidences:
                    return sum(confidences) / len(confidences)
            # Fallback to generic fields
            return self.ocr_json_dump.get('confidence', 0) or self.ocr_json_dump.get('score', 0)
        return 0