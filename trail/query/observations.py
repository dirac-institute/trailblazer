import django_tables2 as tables

from django.apps import apps

Metadata = apps.get_model('upload', 'Metadata')

class ObservationTable(tables.Table):
    class Meta:
        model = Metadata
        template_name = "django_tables2/bootstrap.html"
       # fields = ("instrument", "telescope", "time_start", "duration", "longitude", "lattitude", "obs_height", "science_program", "filter_name")