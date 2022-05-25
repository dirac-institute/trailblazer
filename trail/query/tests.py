from django.test import TestCase
from upload.models import Metadata
from upload.models import UploadInfo, Wcs
from query.views import MetadataDAO
from coordinates import getXYZFromWcs, getRaDecFromXYZ
import numpy as np

# Create your tests here.


class MetadataQueryTest(TestCase):
    metadataDao = MetadataDAO()

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
        wcs1 = {
            'metadata': meta,
            'wcs_radius': 1,
            'wcs_center_x': 0.4,
            'wcs_center_y': 0.3,
            'wcs_center_z': 0.7,
            'wcs_corner_x': 16,
            'wcs_corner_y': 17,
            'wcs_corner_z': 0.7
        }
        meta.save()
        meta2.save()

        self.wcs = Wcs(**wcs1)
        self.wcs.save()

    def testBasicQueries(self):
        """Tests getMetadataByParams in metadataDao is functional"""
        queryParam = {"processor_name__icontains": "fits"}
        response = self.metadataDao.queryByParams(queryParam)

        self.assertEqual(len(response), 2)
        for metadata in response:
            self.assertTrue("fits" in metadata.processor_name.lower())

    def testBasicWcsQuery(self):
        """Tests getMeatadataInSpecifiedSky in metadataDao is functional"""
        queryParam = {"raLow": 0, "raHigh": 1000, "decLow": 0, "decHigh": 1000}
        response = self.metadataDao.queryBySpecifiedSky(queryParam)

        self.assertEqual(len(response), 1)

    def testCoordinateConversion(self):
        ra = 200 * np.pi / 180
        dec = 87 * np.pi / 180

        cartersian = getXYZFromWcs(ra, dec)

        self.assertTrue(abs(cartersian["x"] - (-0.049) < 0.1))
        self.assertTrue(abs(cartersian["y"] - (-0.018) < 0.1))
        self.assertTrue(abs(cartersian["z"] - (0.9986) < 0.1))

        backToPolar = getRaDecFromXYZ(cartersian["x"], cartersian["y"], cartersian["z"])
        self.assertTrue(abs(backToPolar["ra"] - ra < 0.1))
        self.assertTrue(abs(backToPolar["dec"] - dec < 0.1))
