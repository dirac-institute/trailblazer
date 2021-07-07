import django_tables2 as tables
from .models import Observation


class ObservationTable(tables.Table):
    class Meta: 
        model = Observation
        template_name = ""
        fields = ("time_start",)
        template_name = "semantic.html"
