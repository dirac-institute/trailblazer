from django.test import TestCase
from upload.models import Metadata
from upload.serializers import MetadataSerializer
from rest_framework.test import APIClient
from upload.models import UploadInfo
from rest_framework import status
import io
from rest_framework.parsers import JSONParser
# Create your tests here.


class MetadataQueryTest(TestCase):
    client = APIClient()

    def setUp(self):
        info = UploadInfo()
        info.save()

        meta = Metadata(
            upload_info=info,
            processor_name="MultiExtensionFits",
            standardizer_name="astro_metadaor",
            instrument="HSC",
            telescope="Subaru",
            science_program="asdfasdf",
            obs_lon=-101,
            obs_lat=1.0,
            obs_height=1.0,
            datetime_begin='2009-10-17T01:53:42.1',
            datetime_end='2009-10-18T01:53:42.1',
            exposure_duration=30.0,
            filter_name='i'
        )
        meta2 = Metadata(
            upload_info=info,
            processor_name="SingleExtensionFits",
            standardizer_name="astro_metadaor",
            instrument="HSC",
            telescope="Subaru",
            science_program="asdfasdf",
            obs_lon=-101,
            obs_lat=1.0,
            obs_height=1.0,
            datetime_begin='2009-10-17T01:53:42.1',
            datetime_end='2009-10-18T01:53:42.1',
            exposure_duration=30.0,
            filter_name='i'
        )
        meta.save()
        meta2.save()

    def testBasicQueries(self):
        response = self.client.get("/query/getMetadata?processor_name=fits")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        stream = io.BytesIO(response.content)
        data = JSONParser().parse(stream)

        metadatas = MetadataSerializer(data=data, many=True)

        self.assertTrue(metadatas.is_valid(raise_exception=True))
        result = metadatas.create(metadatas.validated_data)
        self.assertEqual(len(result), 2)
