from prices.management.recording_command import ShopRecordCommand
from prices.models import Shop


class Command(ShopRecordCommand):
    help = "Record today's promo price for DOZ pages only."
    shop_code = Shop.DOZ
