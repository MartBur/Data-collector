from prices.management.recording_command import ShopRecordCommand
from prices.models import Shop


class Command(ShopRecordCommand):
    help: str = "Record today's promo price for DOZ pages only."
    shop_code: str = Shop.DOZ
