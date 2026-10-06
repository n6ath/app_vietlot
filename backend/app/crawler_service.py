"""Backward-compatible facade for the immutable crawler service."""
from .crawler.crawler_service import CrawlerService, CONFIGS


def crawl(game_type: str, **options):
    try:
        config = CONFIGS[game_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported game_type: {game_type}") from exc
    return CrawlerService(config).crawl(**options)
