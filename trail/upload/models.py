from django.db import models

"""Define the SQL metadata design here."""


class ExampleFrame(models.Model):
    # meta-class mixin ??
    class Meta:
        # Django doesn't do composite primary keys
        constraints = [
            models.UniqueConstraint(fields=['run', 'camcol', 'filter', 'field'],
                                    name="SDSS unique identifiers.")
        ]

    # integer autoincrement primary fields is automatically added by Django

    # verbose_names should be lowercase, Django will capitalize
    # https://docs.djangoproject.com/en/3.1/topics/db/models/#verbose-field-names
    name = models.CharField("name of used translator.", max_length=10, null=False)
    instrument = models.CharField("instrument name", max_length=20)
    telescope = models.CharField("telescope", max_length=20, null=False)
    science_program = models.CharField("science program image is a part of.", max_length=30)

    obs_lon = models.FloatField("observatory longitude (deg)", null=False)
    obs_lat = models.FloatField("observatory latitude (deg)", null=False)
    obs_height = models.FloatField("observatory ASL height (m)", null=False)

    datetime_begin = models.DateTimeField("UTC at exposure start.", null=False)
    datetime_end = models.DateTimeField("UTC at exposure end.", null=False)

    center_x = models.FloatField("unit sphere coordinate of central pixel", null=False)
    center_y = models.FloatField("unit sphere coordinate of central pixel", null=False)
    center_z = models.FloatField("unit sphere coordinate of central pixel", null=False)
    corner_x = models.FloatField("unit sphere coordinate of corner pixel", null=False)
    corner_x = models.FloatField("unit sphere coordinate of corner pixel", null=False)
    corner_x = models.FloatField("unit sphere coordinate of corner pixel", null=False)
