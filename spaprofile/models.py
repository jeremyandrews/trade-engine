from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django_countries.fields import CountryField

from spauser.models import SpaUser


class SpaProfile(models.Model):
    user = models.OneToOneField(SpaUser, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=128, null=True, blank=True)
    last_name = models.CharField(max_length=128, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. 9 to 15 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    country = CountryField(null=True, blank=True)

    def __unicode__(self):
        return u'Profile of user: %s' % self.user.email

@receiver(post_save, sender=SpaUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        SpaProfile.objects.create(user=instance)

@receiver(post_save, sender=SpaUser)
def save_user_profile(sender, instance, **kwargs):
    instance.spaprofile.save()

