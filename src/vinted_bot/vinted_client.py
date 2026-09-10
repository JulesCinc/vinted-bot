"""Vinted data-access boundary.

Wraps vinted_scraper's catalog search (api/v2/catalog/items) as a thin,
swappable adapter: `VintedClient.search(gpu_model) -> list[Listing]`. Only
fields confirmed present in a live response are surfaced (see issue #12) —
nothing here assumes a category/catalog_id field exists.

The single-item JSON endpoint and the HTML/OpenGraph fallback are not used
on this path: the catalog search response already carries everything the
rest of the bot needs (price, Condition, title, brand, photo, url, id).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Protocol

from vinted_scraper import VintedScraper
from vinted_scraper.models import VintedItem

_log = logging.getLogger(__name__)

VINTED_BASE_URL = "https://www.vinted.fr"


@dataclass(frozen=True)
class Listing:
    """A single GPU Listing, normalized from a Vinted catalog search result."""

    id: int
    title: Optional[str]
    price: Optional[float]
    total_item_price: Optional[float]
    status: Optional[str]
    brand_title: Optional[str]
    photo_url: Optional[str]
    url: Optional[str]
    is_visible: Optional[bool]


class SearchesVintedItems(Protocol):
    """The slice of vinted_scraper's client interface VintedClient needs."""

    def search(self, params: Optional[dict] = None) -> List[VintedItem]: ...


class VintedClient:
    """Thin adapter over vinted_scraper's catalog search endpoint."""

    def __init__(self, scraper: Optional[SearchesVintedItems] = None) -> None:
        self._scraper = (
            scraper if scraper is not None else VintedScraper(baseurl=VINTED_BASE_URL)
        )

    def search(self, gpu_model: str) -> List[Listing]:
        """Search Vinted's catalog for Listings matching a GPU Model.

        One call per tracked GPU Model per Pass (ADR 0003) — no per-item
        detail calls.
        """
        items = self._scraper.search({"search_text": gpu_model})
        listings = []
        for item in items:
            listing = _to_listing(item)
            if listing is not None:
                listings.append(listing)
        return listings


def _to_listing(item: VintedItem) -> Optional[Listing]:
    if item.id is None:
        _log.warning("Skipping Vinted search result with no listing id: %r", item.title)
        return None
    photo_url = item.photos[0].url if item.photos else None
    return Listing(
        id=item.id,
        title=item.title,
        price=item.price,
        total_item_price=item.total_item_price,
        status=item.status,
        brand_title=item.brand_title,
        photo_url=photo_url,
        url=item.url,
        is_visible=item.is_visible,
    )
