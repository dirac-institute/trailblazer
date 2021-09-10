from django.test import TestCase
from gallery.views import get_image
from uploads.models import Thumbnails


class GalleryImageTestCase(TestCase):
    def setUp(self):
        objlist = []
        for i in range(100):
            objlist.append(Thumbnails({"wcs-id": i, "small": "", "large": ""}))
        Thumbnails.objects.create(objlist)

    def testImageListSame(self):
        """test that the pages are working"""
        for count in range(20):
            page = 0
            processed = [image.wcs_id for image in get_image(count, page)]
            expected = list(range(page * count, (page + 1) * count))
            self.assertTrue(processed == expected)
