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

    run = models.IntegerField()
    camcol = models.IntegerField()
    filter = models.CharField(max_length=1)
    field = models.IntegerField()

    ctype = models.CharField(max_length=20, null=False)
    crpix1 = models.FloatField(null=False)
    crpix2 = models.FloatField(null=False)
    crval1 = models.FloatField(null=False)
    crval2 = models.FloatField(null=False)

    cd11 = models.FloatField(null=False)
    cd12 = models.FloatField(null=False)
    cd21 = models.FloatField(null=False)
    cd22 = models.FloatField(null=False)

    t = models.DateTimeField(verbose_name="UTC time at exposure start.")
