from django.db import models
from django.contrib.postgres.fields import ArrayField


class AnswerScript(models.Model):
    id = models.AutoField(primary_key=True)
    question_paper_uuid = models.UUIDField(help_text="UUID of the question paper")
    roll_no = models.CharField(max_length=50, help_text="Student roll number")
    image_urls = ArrayField(
        models.URLField(max_length=500),
        size=50,
        default=list,
        help_text="Array of S3 image URLs"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'answer_scripts'
        verbose_name = 'Answer Script'
        verbose_name_plural = 'Answer Scripts'
        # Composite unique constraint: combination of roll_no and question_paper_uuid must be unique
        unique_together = ('roll_no', 'question_paper_uuid')
        indexes = [
            models.Index(fields=['roll_no']),
            models.Index(fields=['question_paper_uuid']),
            models.Index(fields=['question_paper_uuid', 'roll_no']),
        ]
    
    def __str__(self):
        return f"ID: {self.id} - Roll: {self.roll_no} - QP: {self.question_paper_uuid}"
    
    def get_s3_folder_path(self):
        return f"answer-images/{self.question_paper_uuid}/{self.roll_no}/"
    
    def get_image_count(self):
        return len(self.image_urls)