from __future__ import annotations

import logging
import signal
import time

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.core.management.base import BaseCommand

from crawlers.providers import CRAWLER_TYPES
from offers.services import crawl_once


class Command(BaseCommand):
    help = "Crawl VPS/cloud provider offers into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            action="append",
            choices=sorted(CRAWLER_TYPES),
            help="Provider slug. May be passed more than once.",
        )
        parser.add_argument("--worker", action="store_true", help="Run forever on a fixed interval.")
        parser.add_argument(
            "--interval-minutes",
            type=int,
            default=settings.CRAWL_INTERVAL_MINUTES,
            help="Worker crawl interval.",
        )

    def handle(self, *args, **options):
        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        providers = options["provider"] or list(settings.CRAWL_PROVIDERS)
        timeout = settings.HTTP_TIMEOUT_SECONDS
        cookies = settings.CRAWLER_COOKIES

        if not options["worker"]:
            summary = crawl_once(provider_slugs=providers, timeout=timeout, cookies=cookies)
            self.stdout.write(self.style.SUCCESS(f"Crawl complete: {summary}"))
            return

        crawl_once(provider_slugs=providers, timeout=timeout, cookies=cookies)
        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            crawl_once,
            "interval",
            minutes=options["interval_minutes"],
            kwargs={"provider_slugs": providers, "timeout": timeout, "cookies": cookies},
            id="crawl-offers",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        scheduler.start()
        self.stdout.write(self.style.SUCCESS(f"Crawler worker started: providers={providers}"))

        stop = False

        def request_stop(signum, frame):
            nonlocal stop
            stop = True

        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
        while not stop:
            time.sleep(1)

        scheduler.shutdown(wait=False)
        self.stdout.write(self.style.WARNING("Crawler worker stopped"))
