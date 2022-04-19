from django.test import TestCase
from upload.models import Metadata
from rest_framework.test import APIClient
import json
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

    def test_or_relationship_when_two_query_set(self):
        query1 = {"processor_name": "MultiExtensionFits"}
        query2 = {"processor_name": "DECamCommunityFits"}
        requestReturnCols = ["obs_lon", "processor_name"]
        requestPayload = self.createRequestPayload(returnCols=requestReturnCols, queryParams=[query1, query2])
        reponse = self.client.post("/query/getMetadata", json.dumps(requestPayload), content_type='application/json')
        self.assertEqual(reponse.status_code, 200)
        jsonContents = json.loads(reponse.content)
        for content in jsonContents:
            if (content["processor_name"] != "MultiExtensionFits"
                    and content["processor_name"] != "DECamCommunityFits"):
                self.assertEqual(content["processor_name"], "")

    def test_and_relationship_when_two_param_set(self):
        query1 = {"processor_name": "MultiExtensionFits", "obs_lon__gte": "-100", "obs_lon__lte": "100"}
        requestReturnCols = ["obs_lon", "processor_name"]
        requestPayload = self.createRequestPayload(returnCols=requestReturnCols, queryParams=[query1])
        reponse = self.client.post("/query/getMetadata", json.dumps(requestPayload), content_type='application/json')
        self.assertEqual(reponse.status_code, 200)
        jsonContents = json.loads(reponse.content)
        for content in jsonContents:
            self.assertEqual(content["processor_name"], "MultiExtensionFits")
            self.assertGreaterEqual(content["obs_lon"], -100)
            self.assertLessEqual(content["obs_lon"], 100)

    def createRequestPayload(self, returnAllCols=1, returnCols=[], queryParams=[]):
        request = {
            "returnAllCols": returnAllCols,
            "returnCols": returnCols,
            "queryParams": queryParams
        }
        return request
