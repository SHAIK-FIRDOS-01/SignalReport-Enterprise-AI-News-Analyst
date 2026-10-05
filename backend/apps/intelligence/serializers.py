"""
Serializers for AI intelligence analysis.
"""

from rest_framework import serializers


class AnalyzeRequestSerializer(serializers.Serializer):
    """Input validation for news intelligence analysis requests."""
    title = serializers.CharField(max_length=500, required=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    content = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    category = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
