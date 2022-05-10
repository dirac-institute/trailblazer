from django.test import TestCase
from upload.models import Metadata
from rest_framework.test import APIClient
from upload.models import UploadInfo
# Create your tests here.


class MetadataQueryTest(TestCase):
    client = APIClient()

    def setUp(self):
        info = UploadInfo()
        info.save()

        meta = Metadata(
            upload_info=info,
            processor_name="MultiExtensionFits",
            standardizer_name="",
            instrument="",
            telescope="",
            science_program="",
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
            processor_name="DECamCommunityFits",
            standardizer_name="",
            instrument="",
            telescope="",
            science_program="",
            obs_lon=10,
            obs_lat=1.0,
            obs_height=1.0,
            datetime_begin='2009-10-17T01:53:42.1',
            datetime_end='2009-10-18T01:53:42.1',
            exposure_duration=30.0,
            filter_name='i'
        )
        meta.save()
        meta2.save()
