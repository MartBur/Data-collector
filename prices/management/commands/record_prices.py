from prices.management.recording_command import ShopRecordCommand


class Command(ShopRecordCommand):
    help: str = "Record today's promo price for every shop page."
