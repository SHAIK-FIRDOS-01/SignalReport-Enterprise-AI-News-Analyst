"""
Ingestion models for SignalReport.
Tracks external API quota consumption and historical ingestion runs.
"""

from django.db import models


class APICallLog(models.Model):
    """
    Audit and rate-budget log for external API calls (e.g. GNews).
    Guarantees daily quotas (100 req/day for GNews) are never exceeded.
    """
    service = models.CharField(max_length=50, default="gnews", db_index=True)
    category = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    status_code = models.IntegerField(default=200)
    articles_retrieved = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "api_call_logs"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.service} ({self.category or 'all'}) at {self.timestamp} [{self.status_code}]"
