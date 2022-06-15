import django_tables2 as tables

from django.apps import apps

Metadata = apps.get_model('upload', 'Metadata')


class QueryTable(tables.Table):
    class Meta:
        model = Metadata
        template_name = "django_tables2/bootstrap.html"
        fields = ("instrument", "telescope", "datetime_begin", "datetime_end",
                  "exposure_duration", "obs_lon", "obs_lat", "obs_height", "filter_name")
