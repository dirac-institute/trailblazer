import django_tables2 as tables

from django.apps import apps


__all__ = ["QueryTable", ]


Metadata = apps.get_model('upload', 'Metadata')


class QueryTable(tables.Table):
    obs_lon = tables.Column(verbose_name="Observatory Location")
    datetime_begin = tables.Column(verbose_name="Date taken on")

    class Meta:
        model = Metadata
        fields = ("instrument", "telescope", "datetime_begin", "obs_lon", "exposure_duration", "filter_name")

    def render_datetime_begin(self, value, record, **kwargs):
        return value.strftime("%m/%d/%Y")

    def render_obs_lon(self, value, record, **kwargs):
        return f"({record.obs_lat:.3}, {record.obs_lon:.4})"

    def render_exposure_duration(self, value, record, **kwargs):
        return f"{value:.4}"
