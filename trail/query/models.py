from django.db import models


class Observation(models.Model):
    """Placeholder class for django tables 2
    """
    instrument = models.CharField(max_length=100, verbose_name="Instrument")
    telescope = models.CharField(max_length=100, verbose_name="Telescope")
    time_start = models.CharField(max_length=100, verbose_name="Observation start time")
    duration = models.CharField(max_length=100, verbose_name="Duration [s]")
    longitude = models.CharField(max_length=100, verbose_name="Longitude")
    lattitude = models.CharField(max_length=100, verbose_name="Lattitude")
    Height = models.CharField(max_length=100, verbose_name="height")
    processor_name = models.CharField(max_length=100, verbose_name="Processor Name")
    science_program = models.CharField(max_length=100, verbose_name="Science Program")
    standardizer_name = models.CharField(max_length=100, verbose_name="Standardizer Name")
    wcs_radius = models.CharField(max_length=100, verbose_name="WCS Radius")
    filter_name = models.CharField(max_length=100, verbose_name="Filter Name")
