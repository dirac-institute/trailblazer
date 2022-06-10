from copy import copy

from django.test import TestCase
from upload.models import Metadata, Wcs, StandardizedHeader


class TestData:
    metadata1 = {
        'processor_name': 'generic',
        'standardizer_name': 'generic',
        'obs_lon': 1,
        'obs_lat': 2,
        'obs_height': 3,
        'telescope': '5',
        'instrument': '6',
        'science_program': '7',
        'datetime_begin': '8',
        'datetime_end': '9',
        'exposure_duration': 10,
        'filter_name': '11'
    }

    metadata2 = {
        'processor_name': 'generic',
        'standardizer_name': 'generic',
        'obs_lon': 1.1,
        'obs_lat': 2.1,
        'obs_height': 3.1,
        'telescope': '5',
        'instrument': '6',
        'science_program': '7',
        'datetime_begin': '8',
        'datetime_end': '9',
        'exposure_duration': 10,
        'filter_name': '11'
    }

    wcs1 = {
        'radius': 12,
        'center_x': 13,
        'center_y': 14,
        'center_z': 15,
        'corner_x': 16,
        'corner_y': 17,
        'corner_z': 18
    }

    wcs2 = {
        'radius': 12.1,
        'center_x': 13.1,
        'center_y': 14.1,
        'center_z': 15.1,
        'corner_x': 16.1,
        'corner_y': 17.1,
        'corner_z': 18.1
    }

    flat = copy(metadata1)
    flat.update(wcs1)

    nested = {
        "metadata": metadata1,
        "wcs": [wcs1, wcs2]
    }


class WcsTestCase(TestCase):
    def setUp(self):
        self.wcs1 = Wcs(**TestData.wcs1)
        self.wcs2 = copy(self.wcs1)
        self.wcs3 = Wcs(**TestData.wcs2)

    def testToDict(self):
        """Tests Wcs conversion to dictionary"""
        self.assertEqual(self.wcs1.toDict(), TestData.wcs1)

    def testValues(self):
        """Tests Wcs.values behave as expected."""
        self.assertCountEqual(self.wcs1.values(), list(TestData.wcs1.values()))

    def testKeys(self):
        """Tests Wcs.keys behave as expected."""
        self.assertCountEqual(self.wcs1.keys, list(TestData.wcs1.keys()))

    def testRequiredKeys(self):
        """Test Wcs recognizes all required keys."""
        # for Wcs these are all of the keys
        self.assertCountEqual(self.wcs1.required_keys, list(TestData.wcs1.keys()))

    def testIsClose(self):
        """Test Wcs approximate equality."""
        self.assertTrue(self.wcs1.isClose(self.wcs2))
        self.assertFalse(self.wcs1.isClose(self.wcs3))


class MetadataTestCase(TestCase):
    def setUp(self):
        self.metadata1 = Metadata(**TestData.metadata1)
        self.metadata2 = copy(self.metadata1)
        self.metadata3 = Metadata(**TestData.metadata2)

    def testToDict(self):
        """Tests Metadata conversion to dictionary"""
        self.assertEqual(self.metadata1.toDict(), TestData.metadata1)

    def testValues(self):
        """Tests Metadata.values behave as expected."""
        self.assertCountEqual(self.metadata1.values(), list(TestData.metadata1.values()))

    def testKeys(self):
        """Tests Metadata.keys behave as expected."""
        self.assertCountEqual(self.metadata1.keys, list(TestData.metadata1.keys()))

    def testRequiredKeys(self):
        """Test Metadata recognizes all required keys."""
        requiredKeys = ['processor_name', 'standardizer_name',
                        'obs_lon', 'obs_lat', 'obs_height',
                        'datetime_begin', 'datetime_end']
        self.assertCountEqual(self.metadata1.required_keys, requiredKeys)

    def testIsClose(self):
        """Test Metadata approximate equality."""
        self.assertTrue(self.metadata1.isClose(self.metadata2))
        self.assertFalse(self.metadata1.isClose(self.metadata3))


class StandardizedHeaderTestCase(TestCase):
    def setUp(self):
        self.meta1 = Metadata(**TestData.metadata1)
        self.wcs1 = Wcs(**TestData.wcs1)
        self.std1 = StandardizedHeader(metadata=self.meta1, wcs=[self.wcs1])

        self.meta2 = Metadata(**TestData.metadata2)
        self.wcs2 = Wcs(**TestData.wcs2)
        self.std2 = StandardizedHeader(metadata=self.meta2, wcs=[self.wcs2])

        self.std3 = StandardizedHeader(metadata=self.meta1, wcs=[self.wcs1, self.wcs2])

    def testFromDict(self):
        """Tests StandardizedHeader instantiation from dictionary."""
        # Django equality is something really specific, so comparing Metadata
        # and Wcs objects directly compares their PKs by identity. This will of
        # course fail for any non-saved model...
        std = StandardizedHeader.fromDict(TestData.nested)
        self.assertEqual(std.metadata.values(), self.meta1.values())
        self.assertEqual(std.wcs[0].values(), self.wcs1.values())
        self.assertEqual(std.wcs[1].values(), self.wcs2.values())

        std = StandardizedHeader.fromDict(TestData.flat)
        self.assertEqual(std.metadata.values(), self.meta1.values())
        self.assertEqual(std.wcs[0].values(), self.wcs1.values())

    def testIsClose(self):
        """Test StandardizedHeader approximate equality."""
        std = StandardizedHeader.fromDict(TestData.flat)
        msg = (
            "\nStandardized headers differ! Expected values \n "
            f"  {self.std1.toDict()}\n"
            "got \n"
            f"  {std.toDict()}\n"
            "values instead!"
        )
        self.assertEqual(std, self.std1, msg=msg)
        self.assertTrue(self.std1 == std)

    def testUpdateMetadata(self):
        """Test updating metadata works."""
        std = copy(self.std1)
        std.updateMetadata(self.meta2)
        self.assertEqual(std.metadata.values(), self.meta2.values())

        std.updateMetadata(TestData.metadata1)
        self.assertEqual(std, self.std1)

    def testAppendWcs(self):
        """Test we can append a WCS."""
        std = copy(self.std1)
        std.appendWcs(self.wcs2)
        # This should be exactly true
        self.assertEqual(std.wcs[-1].values(), self.wcs2.values())

        # but this might not complete a full circle because of potential casts
        # that could exist in Django ORM
        std.appendWcs(TestData.wcs1)
        self.assertEqual(std.wcs[-1].values(), self.wcs1.values())

    def testExtendWcs(self):
        """Test we can append a list of WCSs"""
        # no need to test from dict because this essentially calls append
        std = copy(self.std1)
        std.extendWcs([self.wcs1, self.wcs2])
        self.assertEqual(std.wcs[-2].values(), self.wcs1.values())
        self.assertEqual(std.wcs[-1].values(), self.wcs2.values())

    def toDict(self):
        """Tests StandardizedHeader conversion to dictionary"""
        self.assertEqual(self.std1.toDict(), TestData.flat)
        self.assertEqual(self.std3.toDict(), TestData.nested)
