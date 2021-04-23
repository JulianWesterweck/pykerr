import os
import pkg_resources
import numpy
import h5py
from scipy.interpolate import CubicSpline
from scipy.interpolate import InterpolatedUnivariateSpline

# the maximum spin we'll allow; this is based on what is in the data files
MAX_SPIN = 0.9997

# solar masses in seconds
MTSUN = 4.925491025543576e-06


# we'll cache the splines
_reomega_splines = {}
_imomega_splines = {}


def _create_spline(name, reim, l, m, n):
    """Creates a cubic spline for the specified mode data."""
    # load the data
    lmn = '{}{}{}'.format(l, abs(m), n)
    try:
        dfile = pkg_resources.resource_stream(__name__,
                                              'data/l{}.hdf'.format(l))
    except OSError:
        raise ValueError("unsupported lmn {}{}{}".format(l, m, n))
    with h5py.File(dfile, 'r') as fp:
        x = fp[lmn]['spin'][()].astype(float)
        y = fp[lmn][name][()]
        if reim == 're':
            y = y.real.astype(float)
        elif reim == 'im':
            y = y.imag.astype(float)
        else:
            raise ValueError("reim must be eiter 're' or 'im'")
    #return CubicSpline(x, y, axis=0, bc_type='natural', extrapolate=False)
    return InterpolatedUnivariateSpline(x, y)


def _getspline(name, reim, l, m, n, cache):
    """Gets a spline."""
    try:
        spline = cache[l, abs(m), n]
    except KeyError:
        spline = _create_spline(name, reim, l, m, n)
        cache[l, abs(m), n] = spline
    return spline


def _checkspin(spin):
    """Checks that the spin is in bounds."""
    if abs(spin) > MAX_SPIN:
        raise ValueError("|spin| must be < {}".format(MAX_SPIN))
    return


def kerr_omega(spin, l, m, n):
    """Returns the dimensionless complex angular frequency of a Kerr BH.

    Parmeters
    ---------
    spin : float
        The dimensionless spin. Must be in [-0.9999, 0.9999].
    l : int
        The l index.
    m : int
        The m index.
    n : int
        The overtone number (where n=0 is the fundamental mode).

    Returns
    -------
    complex :
        The complex angular frequency.
    """
    _checkspin(spin)
    respline = _getspline('omega', 're', l, m, n, _reomega_splines)
    imspline = _getspline('omega', 'im', l, m, n, _imomega_splines)
    # if m is 0, use the absolute value of the spin
    if m == 0:
        spin = abs(spin)
    # negate the frequency if m < 0
    sign = (-1)**int(m < 0)
    return sign*respline(spin) + 1j*imspline(spin)


def kerr_freq(mass, spin, l, m, n):
    """Returns the QNM frequency for a Kerr black hole.

    Parameters
    ----------
    mass : float
        Mass of the object (in solar masses).
    spin : float
        Dimensionless spin. Must be in [-0.9999, 0.9999].
    l : int
        The l index.
    m : int
        The m index.
    n : int
        The overtone number (where n=0 is the fundamental mode).

    Returns
    -------
    float :
        The frequency (in Hz) of the requested mode.
    """
    _checkspin(spin)
    spline = _getspline('omega', 're', l, m, n, _reomega_splines)
    # if m is 0, use the absolute value of the spin
    if m == 0:
        spin = abs(spin)
    # negate the frequency if m < 0
    sign = (-1)**int(m < 0)
    return sign * spline(spin) / (2*numpy.pi*mass*MTSUN)


def kerr_tau(mass, spin, l, m, n):
    """"Returns the QNM damping time for a Kerr black hole.

    Parameters
    ----------
    mass : float
        Mass of the object (in solar masses).
    spin : float
        Dimensionless spin. Must be in [-0.9999, 0.9999].
    l : int
        The l index.
    m : int
        The m index.
    n : int
        The overtone number (where n=0 is the fundamental mode).

    Returns
    -------
    float :
        The frequency (in Hz) of the requested mode.
    """
    _checkspin(spin)
    spline = _getspline('omega', 'im', l, m, n, _imomega_splines)
    # if m is 0, use the absolute value of the spin
    if m == 0:
        spin = abs(spin)
    # Note: Berti et al. [arXiv:0512160] used the convention
    # h+ + ihx ~ e^{iwt}, (see Eq. 2.4) so we
    # need to negate the spline for tau to have the right sign.
    return -mass*MTSUN / spline(spin)
