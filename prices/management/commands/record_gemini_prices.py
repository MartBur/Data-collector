from prices.management.recording_command import ShopRecordCommand
from prices.models import Shop


class Command(ShopRecordCommand):
    help = "Record today's promo price for Gemini pages only."
    shop_code = Shop.GEMINI
