import numpy as np


def getXYZFromWcs(ra, dec):
    """
    Convert ra and dec into xyz coordinates

    Parameters
    ----------
    ra: float
        The coordinate ra
    dec: float
        The coordinate dec

    Note
    -----
    All parameters need to be in radian
    """
    x = np.cos(dec) * np.cos(ra)
    y = np.cos(dec) * np.sin(ra)
    z = np.sin(dec)

    return {"x": x, "y": y, "z": z}


def getRaDecFromXYZ(x, y, z):
    """
    Convert xyz coordinates into ra and dec.

    Parameters
    ----------
    x: float
        The cartesian coordiante x
    y: float
        The cartesian coordiante y
    z: float
        The cartesian coordiante z

    Note
    ----
    The parameters need to be in float.
    """
    ra = np.arctan2(y, x) % (2 * np.pi)
    dec = np.arcsin(z) % (2 * np.pi)

    return {"ra": ra, "dec": dec}
