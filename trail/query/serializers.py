from upload.models import Metadata, Wcs
from rest_framework import serializers


class DynamicSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class WcsSerializer(DynamicSerializer):
    """
    A MetadataSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """
    class Meta:
        model = Wcs
        fields = '__all__'


class MetadataSerializer(DynamicSerializer):
    """
    A MetadataSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """
    wcs = WcsSerializer(many=True, read_only=True)

    class Meta:
        model = Metadata
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        keepWcs = kwargs.pop("keepWcs", False)

        super().__init__(*args, **kwargs)

        if "wcs" in self.fields and not keepWcs:
            self.fields.pop("wcs")
