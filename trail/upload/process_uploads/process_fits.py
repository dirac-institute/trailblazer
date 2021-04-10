from .tmpfile import TemporaryUploadedFileWrapper
from .processors import UploadProcessor


"""Views invoked when upload gets submitted."""


__all__ = ["process_fits", ]


def process_fits(img):
    """Given a uploaded file, normalizes and inserts header data into the DB,
    creates and stores small and large thumbnails and saves a copy of the
    uploaded file.

    Parameters
    ----------
    img : `django.core.files.uploadedfile.TemporaryUploadedFile`
        Uploaded fits image
    """
    upload = TemporaryUploadedFileWrapper(img)
    uplPrc = UploadProcessor(upload)
    uplPrc.process(upload)
    upload.save()
