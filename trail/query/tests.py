from django.test import TestCase
from upload.models import Metadata
from django.test import Client
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
            obs_lon=1.0,
            obs_lat=1.0,
            obs_height=1.0,
            datetime_begin='2009-10-17T01:53:42.1',
            datetime_end='2009-10-18T01:53:42.1',
            exposure_duration=30.0,
            filter_name='i'
        )
        meta.save()
    
    def test_and_relationship_when_two_param_set(self):
        query1 = {"obs_lon__gte" : "-90", "obs_lon__lte" : "70", "processor_name" : "MultiExtensionFits"}
        requestReturnCols = ["obs_lon", "processor_name"]
        requestPayload = self.createRequestPayload(returnCols=requestReturnCols, queryParams=[query1])
        reponse = self.client.post("/query/getMetadata", json.dumps(requestPayload), content_type='application/json')
        self.assertEqual(reponse.status_code, 200)
        jsonContents = json.loads(reponse.content)
        for content in jsonContents:
            self.assertEqual(content["processor_name"], "MultiExtensionFits")
            self.assertGreaterEqual(content["obs_lon"], -90)
            self.assertLessEqual(content["obs_lon"], 70)

    
    def createRequestPayload(self, returnAllCols=1, returnCols=[], queryParams=[]):
        request = {
            "returnAllCols" : returnAllCols,
            "returnCols" : returnCols,
            "queryParams" : queryParams
        }
        return request
        
