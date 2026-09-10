"""Tests for the Vinted data-access boundary (issue #12).

No live network calls: the underlying vinted_scraper client is faked with a
canned response shaped like a live capture of api/v2/catalog/items (see the
field list in issue #12), so the test suite itself can't trigger anti-bot
blocking.
"""

from vinted_bot.vinted_client import Listing, VintedClient

# Shaped like a live api/v2/catalog/items response item (issue #12's confirmed
# field capture). Deliberately omits catalog_id/category fields: the original
# research doc claimed a catalog_id field exists, but it does not appear in
# the live response, and the client must not depend on it.
CANNED_ITEM = {
    "id": 5216383972,
    "title": "RTX 3070 Gigabyte",
    "price": {"amount": "180.00", "currency_code": "EUR"},
    "total_item_price": {"amount": "184.50", "currency_code": "EUR"},
    "status": "Très bon état",
    "brand_title": "Nvidia",
    "photo": {"id": 111, "url": "https://images.vinted.net/photo1.jpg"},
    "photos": [{"id": 111, "url": "https://images.vinted.net/photo1.jpg"}],
    "url": "https://www.vinted.fr/items/5216383972-rtx-3070-gigabyte",
    "path": "/items/5216383972-rtx-3070-gigabyte",
    "is_visible": True,
    "is_favourite": False,
    "favourite_count": 3,
    "view_count": 120,
    "promoted": False,
    "content_source": "search",
    "conversion": None,
    "item_box": {},
    "search_tracking_params": {},
    "service_fee": {"amount": "2.50", "currency_code": "EUR"},
    "size_title": None,
    "show_1st_time_seller_discount": False,
    "user": {"id": 42},
}


class FakeScraper:
    """Stands in for vinted_scraper.VintedScraper: no HTTP, canned items."""

    def __init__(self, items):
        self._items = items
        self.search_calls = []

    def search(self, params=None):
        self.search_calls.append(params)
        return self._items

    def item(self, *args, **kwargs):
        raise AssertionError(
            "HTML/OpenGraph fallback must not be used on the main search path"
        )


def _vinted_item(json_data):
    from vinted_scraper.models import VintedItem

    return VintedItem(json_data=json_data)


def test_search_normalizes_the_confirmed_fields_into_a_listing():
    scraper = FakeScraper([_vinted_item(CANNED_ITEM)])
    client = VintedClient(scraper=scraper)

    [listing] = client.search("RTX 3070")

    assert listing == Listing(
        id=5216383972,
        title="RTX 3070 Gigabyte",
        price=180.0,
        total_item_price=184.5,
        status="Très bon état",
        brand_title="Nvidia",
        photo_url="https://images.vinted.net/photo1.jpg",
        url="https://www.vinted.fr/items/5216383972-rtx-3070-gigabyte",
        is_visible=True,
    )


def test_search_queries_with_the_given_gpu_model_as_search_text():
    scraper = FakeScraper([_vinted_item(CANNED_ITEM)])
    client = VintedClient(scraper=scraper)

    client.search("RTX 3070")

    assert scraper.search_calls == [{"search_text": "RTX 3070"}]


def test_search_returns_a_listing_per_matching_item():
    other_item = dict(CANNED_ITEM, id=999, title="RTX 3080 Asus")
    scraper = FakeScraper([_vinted_item(CANNED_ITEM), _vinted_item(other_item)])
    client = VintedClient(scraper=scraper)

    listings = client.search("RTX 30")

    assert [listing.id for listing in listings] == [5216383972, 999]


def test_search_returns_empty_list_when_nothing_matches():
    scraper = FakeScraper([])
    client = VintedClient(scraper=scraper)

    assert client.search("RTX 3070") == []


def test_search_skips_a_listing_with_no_id_without_discarding_the_rest():
    item_without_id = dict(CANNED_ITEM)
    del item_without_id["id"]
    other_item = dict(CANNED_ITEM, id=999, title="RTX 3080 Asus")
    scraper = FakeScraper([_vinted_item(item_without_id), _vinted_item(other_item)])
    client = VintedClient(scraper=scraper)

    listings = client.search("RTX 30")

    assert [listing.id for listing in listings] == [999]


def test_search_handles_a_listing_with_no_photo():
    item_without_photo = dict(CANNED_ITEM)
    del item_without_photo["photo"]
    del item_without_photo["photos"]
    scraper = FakeScraper([_vinted_item(item_without_photo)])
    client = VintedClient(scraper=scraper)

    [listing] = client.search("RTX 3070")

    assert listing.photo_url is None
