"""Helpers for telling Qt objects apart behind their Python wrappers.

PyQt may hand out different wrappers for one C++ object (an action asked
for twice, a map tool passed in a signal), so wrappers are compared by the
address of the object they wrap.
"""

from qgis.PyQt import sip


def address(obj):
    """Return the address of the Qt object behind ``obj``.

    Falls back to the wrapper's ``id`` for objects sip cannot unwrap.
    """
    try:
        return sip.unwrapinstance(obj)
    except (TypeError, RuntimeError):
        return id(obj)


def same(a, b):
    """Tell whether two wrappers stand for the same Qt object.

    :returns: ``False`` if either is ``None``.
    """
    if a is None or b is None:
        return False
    return a is b or address(a) == address(b)
