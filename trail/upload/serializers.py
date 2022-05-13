from .models import Metadata
from rest_framework import serializers


class DynamicMetadataSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kawrgs):
        fields = kawrgs.pop("fields", None)

        super().__init__(*args, **kawrgs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class MetadataSerializer(DynamicMetadataSerializer):

    METADATA_COLS = set([
                        "id", "processor_name",
                        "instrument", "telescope",
                        "science_program",
                        "obs_lon", "obs_lat",
                        "obs_height", "datetime_begin",
                        "datetime_end", "exposure_duration",
                        "upload_info", "filter_name",
                        "standardizer_name"
                        ])

    class Meta:
        model = Metadata
        fields = '__all__'

    def create(self, validated_data):

        metadata = Metadata.objects.create(**validated_data)
        return metadata
