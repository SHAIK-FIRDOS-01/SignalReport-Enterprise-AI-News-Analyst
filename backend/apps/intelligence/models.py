"""
Intelligence models for SignalReport.
Tracks IP and user account ban cooldowns to protect Groq LLM API quota limits.
"""

from django.db import models
from django.conf import settings


class LLMUsageBan(models.Model):
    """
    Persisted IP-address and user account ban cooldown for LLM analysis.
    Restricts user / IP from using Groq for configurable N hours after each usage.
    """
    ip_address = models.GenericIPAddressField(db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="llm_bans",
        db_index=True,
    )
    banned_until = models.DateTimeField(db_index=True)
    reason = models.CharField(max_length=255, default="LLM usage quota cooldown")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "llm_usage_bans"
        ordering = ["-banned_until"]
        indexes = [
            models.Index(fields=["ip_address", "banned_until"], name="ix_llm_ip_ban"),
        ]

    def __str__(self) -> str:
        return f"LLMBan(ip={self.ip_address}, until={self.banned_until})"


class LLMUsageLog(models.Model):
    """
    Log of each individual LLM analysis request by IP address and optional user account.
    Used to enforce a maximum quota of N requests before triggering a cooldown ban.
    """
    ip_address = models.GenericIPAddressField(db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="llm_usage_logs",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "llm_usage_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ip_address", "created_at"], name="ix_llm_log_ip_time"),
        ]

    def __str__(self) -> str:
        return f"LLMLog(ip={self.ip_address}, at={self.created_at})"
