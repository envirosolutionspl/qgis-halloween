"""Halloween Skin: QGIS plugin entry point."""


def classFactory(iface):  # noqa: N802 (QGIS API name)
    """Create the plugin instance; called by QGIS when the plugin loads.

    :param iface: the QGIS interface (``QgisInterface``).
    :returns: a :class:`~.plugin.HalloweenSkinPlugin`.
    """
    from .plugin import HalloweenSkinPlugin
    return HalloweenSkinPlugin(iface)
