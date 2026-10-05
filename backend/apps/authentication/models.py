"""
Custom User Model for SignalReport.
Replaces: backend/app/models/user.py
Ponytail: Inherits native AbstractBaseUser and PermissionsMixin, using Django's standard password hashers.
Security-audit: Enforces email normalization, verification state, and session invalidation checkpoint (tokens_valid_after).
"""

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager enforcing email-as-username credentials."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address must be provided.")
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    User entity representing identity, credentials, verification state,
    and bulk token revocation checkpoints.
    """
    email = models.EmailField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name="Email Address",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=True)
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    verification_code_expires_at = models.DateTimeField(null=True, blank=True)
    tokens_valid_after = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.email
