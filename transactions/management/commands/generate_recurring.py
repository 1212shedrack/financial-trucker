"""
Management Command: generate_recurring
=======================================
Generates actual Income or Expense transaction records from overdue
RecurringTransaction schedules. Run this command daily via task scheduler
or cron to keep recurring transactions up to date.

Usage:
    python manage.py generate_recurring
    python manage.py generate_recurring --dry-run   # Preview only

Schedule (Windows Task Scheduler example):
    Program: C:\\path\\to\\venv\\Scripts\\python.exe
    Arguments: manage.py generate_recurring
    Start in: C:\\path\\to\\truker\\
"""

import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from transactions.models import RecurringTransaction, Income, Expense

logger = logging.getLogger('pfams')


def _next_date(current, frequency):
    """Compute the next occurrence date from current date + frequency string.
    Pure function — does NOT save anything to the database."""
    if frequency == 'daily':
        return current + timedelta(days=1)
    elif frequency == 'weekly':
        return current + timedelta(weeks=1)
    elif frequency == 'monthly':
        month = current.month + 1
        year = current.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        days_in_month = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                         else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
        day = min(current.day, days_in_month)
        return current.replace(year=year, month=month, day=day)
    elif frequency == 'yearly':
        try:
            return current.replace(year=current.year + 1)
        except ValueError:
            return current.replace(year=current.year + 1, day=28)
    return current + timedelta(days=1)  # fallback


class Command(BaseCommand):
    help = 'Generate Income/Expense records from overdue recurring transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be generated without saving anything',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()

        # Find all active recurring transactions that are due or overdue
        due_schedules = RecurringTransaction.objects.filter(
            active=True,
            next_due_date__lte=today,
        ).select_related('user', 'category')

        if not due_schedules.exists():
            self.stdout.write(self.style.SUCCESS('No recurring transactions are due today.'))
            return

        generated = 0
        skipped = 0

        for schedule in due_schedules:
            current_due = schedule.next_due_date
            iterations = 0
            max_iterations = 365  # Safety cap

            while current_due <= today and iterations < max_iterations:
                iterations += 1

                if dry_run:
                    self.stdout.write(
                        f'  [DRY-RUN] Would create {schedule.transaction_type.upper()}: '
                        f'"{schedule.title}" — TSh {schedule.amount:,.0f} '
                        f'for user "{schedule.user.username}" on {current_due}'
                    )
                    generated += 1
                    current_due = _next_date(current_due, schedule.frequency)
                    continue

                try:
                    with db_transaction.atomic():
                        # Create the actual transaction record
                        if schedule.transaction_type == 'income':
                            Income.objects.create(
                                user=schedule.user,
                                amount=schedule.amount,
                                source=schedule.title,
                                date=current_due,
                                payment_method=schedule.payment_method or 'cash',
                                category=schedule.category,
                                description=f'Auto-generated from recurring: {schedule.title}',
                            )
                        else:
                            Expense.objects.create(
                                user=schedule.user,
                                amount=schedule.amount,
                                description=schedule.title,
                                date=current_due,
                                payment_method=schedule.payment_method or 'cash',
                                category=schedule.category,
                                notes=f'Auto-generated from recurring: {schedule.title}',
                            )

                        # Advance to next due date
                        next_due = _next_date(current_due, schedule.frequency)
                        schedule.next_due_date = next_due
                        schedule.save(update_fields=['next_due_date'])

                    generated += 1
                    logger.info(
                        f'Generated {schedule.transaction_type} "{schedule.title}" '
                        f'for {schedule.user.username} on {current_due}'
                    )
                    self.stdout.write(
                        f'  ✓ Created {schedule.transaction_type}: '
                        f'"{schedule.title}" on {current_due} for {schedule.user.username}'
                    )

                except Exception as e:
                    skipped += 1
                    logger.error(f'Failed to generate recurring pk={schedule.pk}: {e}')
                    self.stderr.write(self.style.ERROR(f'  ✗ Error for "{schedule.title}": {e}'))
                    break  # Stop this schedule's loop on error

                # Move current_due forward for while-loop check
                current_due = _next_date(current_due, schedule.frequency)

                # Deactivate if end_date has been reached
                if not dry_run and schedule.end_date and current_due > schedule.end_date:
                    schedule.active = False
                    schedule.save(update_fields=['active'])
                    self.stdout.write(
                        f'  ℹ "{schedule.title}" reached its end date — deactivated.'
                    )
                    break

        prefix = '[DRY-RUN] ' if dry_run else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{prefix}Done. '
                f'Generated: {generated} transaction(s). '
                f'Skipped (errors): {skipped}.'
            )
        )
