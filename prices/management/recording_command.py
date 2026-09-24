from django.core.management.base import BaseCommand
from django.utils import timezone

from prices import collect
from prices.models import ShopPage


class ShopRecordCommand(BaseCommand):
    shop_code: str | None = None

    def handle(self, *args: str, **options: object) -> None:
        pages = ShopPage.objects.all()
        if self.shop_code is not None:
            pages = pages.filter(shop=self.shop_code)
        collect.record_shop_pages(
            pages,
            collect.fetch_html,
            timezone.localdate(),
            self.stdout.write,
        )
