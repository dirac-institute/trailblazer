from django.db import models


class Observation(models.Model):
    """Placeholder class for django tables 2
    """
    time_start = models.CharField(max_length=100, verbose_name="Observation start time")
