from django.db import models

class Report(models.Model):
    report_name = models.CharField(max_length=200)
    date = models.DateField()
    authors = models.CharField(max_length=200)
    description = models.TextField()
    type = models.CharField(max_length=100)
    subject = models.CharField(max_length=150)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.report_name
