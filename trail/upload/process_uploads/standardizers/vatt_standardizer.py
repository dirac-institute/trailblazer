from datetime import datetime, timedelta, timezone

from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import Metadata


__all__ = ["VattStandardizer", ]


class VattStandardizer(HeaderStandardizer):
    """
    Class that facilitates header metadata translation for the Vatican Observatory

    Parameters
    ----------
    header: 'astropy.io.fits.header.Header'
        The header file for the FITS image
    """

    name = "vatt_standardizer"
    priority = 1

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        """Determines whether standardizer can standardize a header file

        Parameters
        ----------
        header: 'astropy.io.fits.header.Header'
            FITS header file for image

        Returns
        -------
        can_standardize: 'bool'
            Whether standardizer can standardize
        """
        dewar = header.get("DEWAR", False)
        if dewar and dewar == 'vatt4k_dewar':
            return True
        return False

    def standardizeMetadata(self):
        """Standardizes metadata from header of the FITS file

        Returns
        -------
        metadata: 'upload.models.Metadata'
            The metadata
        """
        DATE = self.header["DATE-OBS"]
        TIME = self.header["TIME-OBS"]
        DATEOBS = DATE + 'T' + TIME
        EXP = self.header["EXPTIME"]
        begin = datetime.strptime(DATEOBS, "%Y-%m-%dT%H:%M:%S.%f")
        begin = begin.replace(tzinfo=timezone.utc)
        end = begin + timedelta(seconds=EXP)

        meta = Metadata(
            obs_lon=-109.892107,#Longitude from google maps
            obs_lat=32.701328,#Latitude from google maps
            obs_height=self.header["ELEVAT"],
            datetime_begin=begin.isoformat(),
            datetime_end=end.isoformat(),
            telescope=self.header["TELESCOP"][3:-1].strip(),
            instrument=self.header["INSTRUME"][3:-1].strip(),
            exposure_duration=self.header["EXPTIME"],
        )

        return meta
