from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended profile for each registered user."""

    CURRENCY_CHOICES = [
        ('TZS', 'Tanzanian Shilling (TZS)'),
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('KES', 'Kenyan Shilling (KES)'),
    ]

    TIMEZONE_CHOICES = [
        ('Africa/Dar_es_Salaam', 'Africa/Dar_es_Salaam (EAT)'),
        ('Africa/Nairobi', 'Africa/Nairobi (EAT)'),
        ('UTC', 'UTC'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    preferred_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='TZS')
    timezone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='Africa/Dar_es_Salaam')
    monthly_income_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    monthly_savings_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"Profile — {self.user.username}"

    @property
    def display_name(self):
        return self.full_name or self.user.get_full_name() or self.user.username

    @property
    def currency_symbol(self):
        symbols = {'TZS': 'TSh', 'USD': '$', 'EUR': '€', 'KES': 'KSh'}
        return symbols.get(self.preferred_currency, 'TSh')


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Automatically create a UserProfile when a new User is created."""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            UserProfile.objects.create(user=instance)
