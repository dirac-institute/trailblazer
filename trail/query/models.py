from django.db import models


# class Settings(models.Model):
    # receive_newsletter = models.BooleanField()


class Observation(models.Model):
    time_start = models.CharField(max_length=100, verbose_name="Observation start time")

