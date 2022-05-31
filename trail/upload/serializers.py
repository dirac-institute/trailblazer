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
    """
    A MetadataSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.

    Arguments
    ---------------
    fields : list[str]
        List of keys of metadata objects that will be serialized into a response.
    """
    class Meta:
        model = Metadata
        fields = '__all__'

    def create(self, validated_data):
        metadata = Metadata.objects.create(**validated_data)
        return metadata
