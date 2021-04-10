import os.path
from pathlib import Path

from django.conf import settings


"""
Wrapper to Django's TemporaryUploadedFile that adds additional path
manipulation and file saving functionality.
"""


__all__ = ["TemporaryUploadedFileWrapper", ]


class TemporaryUploadedFileWrapper:
    """Wrapper of TemporaryUploadedFile class.

    Parameters
    ----------
    upload : `django.core.files.uploadedfile.TemporaryUploadedFile`
        Uploaded file object.
    """
    def __init__(self, upload):
        self.tmpfile = upload
        self.filename = upload.name

    @property
    def extension(self):
        """File extension that respects most popularly used archive and
        compressed archive extensions.

        Returns
        -------
        ext : `str`
            File extension of the uploaded file. If the name of the uploaded
            file has no extension, returns an empty string.

        Example
        -------
        If the names of uploaded files are `image.fits.tar.bz2`, `image.fits`
        and `image``returns `.fits.tar.bz2`, `.fits` and ``.
        """
        special = {".gz", ".bz2", ".xz", ".fz"}

        fname = Path(self.filename)
        extensions = fname.suffixes
        if not extensions:
            return ""

        ext = extensions.pop()

        if extensions and ext in special:
            return "".join(extensions)

        return ext

    @property
    def basename(self):
        """Name of the uploaded file without extensions.

        Returns
        -------
        name : `str`
            Name of the uploaded file without extensions.
        """
        return self.filename.split(self.extension)[0]


    def save(self):
        """Saves uploaded file to desired destination.

        Returns
        -------
        tgtPath : `str`
            Path where the file was saved.
        """
        #TODO: fix os.path when transitioning to S3
        # make the destination configurable
        tgtPath = os.path.join(settings.STATIC_ROOT, f"upload/fits/{self.filename}")

        with open(tgtPath, "wb") as f:
            f.write(self.tmpfile.read())

        return tgtPath
