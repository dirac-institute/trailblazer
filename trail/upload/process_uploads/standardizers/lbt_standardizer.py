
from datetime import datetime, timedelta, timezone

from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import Metadata


__all__ = ["LbtStandardizer", ]


class LbtStandardizer(HeaderStandardizer):
    """
    Class that facilitates header metadata translation for Large Binocular Telescope Observatory

    Parameters
    ----------
    header: 'astropy.io.fits.header.Header'
        The header file for the FITS image
    """

    name = "large_binocular_telescope_standardizer"
    priority = 1

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        """Determines whether standardizer can standardizer a header file

        Parameters
        ----------
        header: 'astropy.io.fits.header.Header'
            FITS header file for image

        Returns
        -------
        can_standardize: 'bool'
            Whether standardizer can standardize
        """
        origin = header.get("ORIGIN", False)
        if origin and "LBT Observatory" == origin:
            return True
        return False

    def standardizeMetadata(self):
        """Standardizes metadata from header of the FITS file

        Returns
        -------
        metadata: 'upload.models.Metadata'
            The metadata
        """
        DATE_OBS = self.header["DATE_OBS"]
        EXPTIME = self.header["EXPTIME"]
        begin = datetime.strptime(DATE_OBS, "%Y-%m-%dT%H:%M:%S.%f")
        begin = begin.replace(tzinfo=timezone.utc)
        end = begin + timedelta(seconds=EXPTIME)

        meta = Metadata(
            obs_lon=self.header["LBTLONG"],
            obs_lat=self.header["LBTLAT"],
            obs_height=3221,  # height in meters from official website
            datetime_begin=begin.isoformat(),
            datetime_end=end.isoformat(),
            telescope=self.header["TELESCOP"],
            instrument=self.header["INSTRUME"],
            exposure_duration=EXPTIME,
            filter_name=self.header["FILTER"].strip()
        )

        return meta
