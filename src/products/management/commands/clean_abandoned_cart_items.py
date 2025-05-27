from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from products.models import PillItem

class Command(BaseCommand):
    help = 'Remove abandoned cart items older than 30 days'

    def handle(self, *args, **kwargs):
        threshold = timezone.now() - timedelta(days=30)
        abandoned_items = PillItem.objects.filter(status__isnull=True, date_added__lt=threshold)
        count = abandoned_items.count()
        abandoned_items.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} abandoned cart items.'))