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
    save_root = os.path.join(settings.STATIC_ROOT, "upload/fits/")
    """Root of the location where upload will be permanently saved."""

    special_extensions = {".gz", ".bz2", ".xz", ".fz"}
    """File extensions recognized as processable archives."""

    def __init__(self, upload):
        self.tmpfile = upload
        self.filename = upload.name

    def __repr__(self):
        repr = super().__repr__()
        clsPath = repr.split(self.__class__.__name__)[0]
        return f"{clsPath}{self.__class__.__name__}({self.filename})>"

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
        fname = Path(self.filename)
        extensions = fname.suffixes
        if not extensions:
            return ""

        # if we recognize the special extensions as one of the acceptable
        # special extensions (tars, fz etc.) return all of them
        if extensions[-1] in self.special_extensions:
            return "".join(extensions)

        # otherwise just the last one
        return extensions.pop()

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
        # TODO: fix os.path when transitioning to S3
        # make the destination configurable
        tgtPath = os.path.join(self.save_root, self.filename)
        with open(tgtPath, "wb") as f:
            f.write(self.tmpfile.read())

        return tgtPath
