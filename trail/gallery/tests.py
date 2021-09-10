# Not sure how to get this working, may look at a seperate time
#
# from django.test import TestCase
# from gallery.views import get_images
# from uploads.models import Thumbnails
#
#
# class GalleryImageTestCase(TestCase):
#     def setUp(self):
#         objlist = []
#         for i in range(100):
#             objlist.append(Thumbnails({"wcs-id": i, "small": "", "large": ""}))
#         Thumbnails.objects.create(objlist)
#
#     def testImageListSame(self):
#         """test that the pages are working"""
#         for count in range(20):
#             page = 0
#             processed = [image.wcs_id for image in get_images(count, page)]
#             expected = list(range(page * count, (page + 1) * count))
#             self.assertEqual(processed, expected)


from django.test import TestCase
from gallery.views import get_images

from django.apps import apps

UploadInfo = apps.get_model('upload', 'UploadInfo')
Metadata = apps.get_model('upload', 'Metadata')
Thumbnails = apps.get_model('upload', 'Thumbnails')
Wcs = apps.get_model('upload', 'Wcs')


class GalleryImageTestCase(TestCase):
    def setUp(self):
        info = UploadInfo()
        info.save()

        meta = Metadata(
            upload_info=info,
            processor_name="",
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

        thumbs = []
        for i in range(100):
            wcs = Wcs(
                metadata=meta,
                wcs_radius=1.0,
                wcs_center_x=1.0,
                wcs_center_y=1.0,
                wcs_center_z=1.0,
                wcs_corner_x=1.0,
                wcs_corner_y=1.0,
                wcs_corner_z=1.0
            )
            wcs.save()
            thumbs.append(Thumbnails(wcs=wcs, small="", large=""))

        Thumbnails.objects.bulk_create(thumbs)

    def testImageListSame(self):
        """test that the pages are working"""
        for count in range(100):
            for page in range(2):
                self.assertEqual(list(get_images(count, page).values("wcs")),
                                 list(Thumbnails.objects.all()[count * page:count * (page + 1)].values("wcs")))
