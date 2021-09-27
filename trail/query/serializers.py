from django.apps import apps
from rest_framework import serializers


Metadata = apps.get_model('upload', 'Metadata')


class MetadataSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Metadata
        fields = ('instrument', 'telescope', 'filter_name')


class MetadataSerializer2(serializers.ModelSerializer):
    class Meta:
        model = Metadata
        fields = ('instrument', 'telescope', 'filter_name')
