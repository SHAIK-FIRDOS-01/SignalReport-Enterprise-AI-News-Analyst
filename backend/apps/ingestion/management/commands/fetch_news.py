"""
Django management command to ingest news intelligence from GNews with smart quota budgeting.
Command: python manage.py fetch_news [--force] [--daemon] [--interval 1800]
Ponytail: Standard BaseCommand with atomic transactions, SHA-256 deduplication, and budget protection.
Security-audit: Uses parameterized queries and atomic transaction boundaries to prevent partial corruption.
"""

import time
import hashlib
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.feed.models import Article
from apps.ingestion.services.gnews_client import GNewsClient, normalize_article_data

logger = logging.getLogger("fetch_news_command")

DEFAULT_CATEGORIES = ["general", "business", "technology", "nation"]


class Command(BaseCommand):
    help = "Ingests top news headlines across categories from GNews API respecting quota limits."

    def add_arguments(self, parser):
        parser.add_argument(
            "--categories",
            nargs="+",
            default=DEFAULT_CATEGORIES,
            help="List of news categories to fetch (default: general business technology nation)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force fetch bypassing cooldown and daily budget checks.",
        )
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Run continuously in the background with round-robin category fetching.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=1800,
            help="Interval in seconds between round-robin fetches in daemon mode (default: 1800 = 30m).",
        )

    def _ingest_category(self, category: str, client: GNewsClient, force: bool = False) -> int:
        cat_name = category.lower().strip()
        raw_articles = client.fetch_top_headlines(category=cat_name, force=force)
        if not raw_articles:
            self.stdout.write(self.style.NOTICE(f"No new articles fetched for '{cat_name}' (cooldown or quota)."))
            return 0

        normalized = []
        for item in raw_articles:
            norm = normalize_article_data(item, default_category=cat_name)
            if norm:
                normalized.append(norm)

        if not normalized:
            return 0

        # URL deduplication within batch using URL hash mapping
        unique_by_hash = {}
        for art in normalized:
            url_hash = hashlib.sha256(art["url"].strip().encode("utf-8")).hexdigest()
            if url_hash not in unique_by_hash:
                unique_by_hash[url_hash] = art

        candidate_batch = list(unique_by_hash.values())

        # Filter out existing URLs from database
        candidate_urls = [a["url"] for a in candidate_batch]
        existing_urls = set(
            Article.objects.filter(url__in=candidate_urls).values_list("url", flat=True)
        )

        new_articles = [
            Article(**data)
            for data in candidate_batch
            if data["url"] not in existing_urls
        ]

        if new_articles:
            with transaction.atomic():
                created = Article.objects.bulk_create(new_articles, ignore_conflicts=True)
                count = len(created)
                self.stdout.write(
                    self.style.SUCCESS(f"Persisted {count} new articles for '{cat_name}'")
                )
                return count
        else:
            self.stdout.write(
                self.style.NOTICE(f"All {len(candidate_batch)} articles for '{cat_name}' already exist.")
            )
            return 0

    def handle(self, *args, **options):
        categories = options["categories"]
        force = options["force"]
        daemon = options["daemon"]
        interval = options["interval"]
        client = GNewsClient()

        if daemon:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Starting GNews ingestion daemon (interval: {interval}s, categories: {categories})..."
                )
            )
            cat_index = 0
            while True:
                try:
                    current_cat = categories[cat_index % len(categories)]
                    self.stdout.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Fetching '{current_cat}'...")
                    self._ingest_category(current_cat, client, force=force)
                    cat_index += 1
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"Error during ingestion cycle: {exc}"))

                self.stdout.write(f"Sleeping for {interval} seconds until next category cycle...")
                try:
                    time.sleep(interval)
                except KeyboardInterrupt:
                    self.stdout.write(self.style.WARNING("Ingestion daemon stopped by user."))
                    break
        else:
            self.stdout.write(self.style.NOTICE(f"Starting news ingestion across categories: {categories}"))
            total = 0
            for cat in categories:
                total += self._ingest_category(cat, client, force=force)
            self.stdout.write(self.style.SUCCESS(f"Ingestion complete. Total new articles: {total}"))
