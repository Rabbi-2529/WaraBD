"""Refresh courier status for parcels still on the way.

    python manage.py courier_sync            # all shipped orders booked through Steadfast / Pathao
    python manage.py courier_sync --days 30  # only those sent in the last 30 days (default 45)

Run it from Windows Task Scheduler / cron every hour or two; delivered parcels
move the order to "Delivered" (and cash-on-delivery orders to "Paid").
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from web import courier
from web.models import Order


class Command(BaseCommand):
    help = "Ask Steadfast / Pathao for the latest status of parcels that are not delivered yet."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=45)

    def handle(self, *args, **opts):
        since = timezone.now() - timedelta(days=opts["days"])
        orders = (Order.objects.filter(courier__in=[courier.STEADFAST, courier.PATHAO], courier_sent_at__gte=since)
                  .exclude(courier_consignment_id="")
                  .exclude(status__in=[Order.STATUS_DELIVERED, Order.STATUS_CANCELLED]))
        done = failed = 0
        for order in orders:
            try:
                status = courier.refresh(order)
                done += 1
                self.stdout.write(f"{order.order_number}: {status}")
            except courier.CourierError as exc:
                failed += 1
                self.stderr.write(f"{order.order_number}: {exc}")
        self.stdout.write(self.style.SUCCESS(f"Checked {done} parcel(s), {failed} failed."))
