from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from upload.models import Metadata, UploadInfo, Wcs
from query.serializers import MetadataSerializer, WcsSerializer

# Create your tests here.


class RestQueryTest(APITestCase):

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
            filter_name='r'
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
        wcs1 = {
            'metadata': meta,
            'radius': 1,
            'center_x': 0.4,
            'center_y': 0.3,
            'center_z': 0.7,
            'corner_x': 16,
            'corner_y': 17,
            'corner_z': 0.7
        }

        meta.save()
        meta2.save()

        self.wcs = Wcs(**wcs1)
        self.wcs.save()

    def test_metadata_get(self):
        """Test basic Metadata REST queries."""
        url = reverse("metadata")

        # test querying /query/metadata just returns all of the data
        response = self.client.get(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serialized = MetadataSerializer(Metadata.objects.all(), many=True)
        self.assertEqual(serialized.data, response.data)

        # test querying with parameters, i.e. querying:
        # /query/metadata?instrument=HSC&filter_name=r
        response = self.client.get(url,
                                   {"instrument": "HSC", "filter_name": "r"},
                                   format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        queryset = Metadata.objects.filter(instrument="HSC", filter_name="r")
        serialized = MetadataSerializer(queryset, many=True)
        self.assertEqual(serialized.data, response.data)

        # test querying with bad params returns a bad request response
        response = self.client.get(url, {"nonsense": "bad_data"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_metadata_get_fields(self):
        """Test Metadata REST queries with specified return fields."""
        url = reverse("metadata")

        # test querying /query/metadata just returns all of the data
        response = self.client.get(url,
                                   {"instrument": "HSC",
                                    "fields": ["instrument", "telescope"]},
                                   format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        qset = Metadata.objects.filter(instrument__icontains="HSC")
        serialized = MetadataSerializer(qset, many=True, fields=["instrument", "telescope"])
        self.assertEqual(serialized.data, response.data)

    def test_metadata_get_non_exact_match(self):
        """Test Metadata REST queries with exact match being False."""
        url = reverse("metadata")

        # test querying /query/metadata just returns all of the data
        response = self.client.get(url,
                                   {"instrument": "hsc", "exactMatch": False},
                                   format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        qset = Metadata.objects.filter(instrument__icontains="hsc")
        serialized = MetadataSerializer(qset, many=True)
        self.assertEqual(serialized.data, response.data)

    def test_wcs_get(self):
        """Tests basic Wcs REST queries."""
        url = reverse("wcs")

        # because they inherit from same basic view we do not have to be detailed here
        response = self.client.get(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serialized = WcsSerializer(Wcs.objects.all(), many=True)
        self.assertEqual(serialized.data, response.data)

    def test_get_metadata_and_wcs(self):
        """Tests basic Wcs REST queries."""
        url = reverse("metadata")

        # because they inherit from same basic view we do not have to be detailed here
        response = self.client.get(url, {"getWcs": True, }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        qset = Metadata.objects.all().prefetch_related("wcs")
        serialized = MetadataSerializer(qset, many=True, keepWcs=True)
        self.assertEqual(serialized.data, response.data)

    def test_get_metadata_in_sky_region(self):
        """Tests basic Wcs REST queries."""
        url = reverse("metadata")

        # because they inherit from same basic view we do not have to be detailed here
        qparams = {"raLow": 0, "raHigh": 1, "decLow": 0, "decHigh": 1, "getWcs": True}
        response = self.client.get(url, qparams, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        queryset, qparams = Metadata.query_sky_region(qparams)
        serialized = MetadataSerializer(queryset, many=True, keepWcs=True)
        self.assertEqual(serialized.data, response.data)
