from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GdkPixbuf


def new_with_paused_emblem(icon_pixbuf):
    """Returns a new pixbuf with a pause emblem in the right bottom corner

    (success, new pixbuf)
    """

    padding = 1.0 / 15.0
    size = 5.0 / 8.0

    base = icon_pixbuf.copy()
    width, height = base.get_width(), base.get_height()
    hpad = int(height * padding)
    wpad = int(width * padding)

    # get the sqare area where we can place the icon
    height_new = int((width - wpad) * size)
    width_new = int((height - hpad) * size)
    if height_new <= 0 or width_new <= 0:
        return False, base

    # get a pixbuf with roughly the size we want
    overlay = get_paused_pixbuf((height_new, width_new), min(height_new, width_new) / 5)
    if not overlay:
        return False, base

    width_overlay, height_overlay = overlay.get_width(), overlay.get_height()
    # we expect below that the icon fits into the icon including padding
    width_overlay = min(width - wpad, width_overlay)
    height_overlay = min(height - hpad, height_overlay)
    overlay.composite(
        base,
        width - width_overlay - wpad,
        height - height_overlay - hpad,
        width_overlay,
        height_overlay,
        width - width_overlay - wpad,
        height - height_overlay - hpad,
        1.0, 1.0,
        GdkPixbuf.InterpType.BILINEAR,
        255
    )

    return True, base


def get_paused_pixbuf(boundary, diff):
    """Returns a pixbuf for a paused icon from the current theme.
    The returned pixbuf can have a size of size->size+diff
    size needs to be > 0
    """

    size = min(boundary)

    if size <= 0:
        raise ValueError("size has to be > 0")

    if diff < 0:
        raise ValueError("diff has to be >= 0")

    names = ('media-playback-pause', Gtk.STOCK_MEDIA_PAUSE)
    theme = Gtk.IconTheme.get_default()

    # Get the suggested icon
    info = theme.choose_icon(names, size, Gtk.IconLookupFlags.USE_BUILTIN)
    if not info:
        return

    try:
        pixbuf = info.load_icon()
    except GLib.GError:
        pass
    else:
        # In case it is too big, rescale
        pb_size = min(pixbuf.get_height(), pixbuf.get_width())
        if abs(pb_size - size) > diff:
            return scale(pixbuf, boundary)
        return pixbuf


def scale(pixbuf, boundary, scale_up=True, force_copy=False):
    """Scale a pixbuf so it fits into the boundary.
    (preserves image aspect ratio)
    If `scale_up` is True, the resulting pixbuf can be larger than
    the original one.
    If `force_copy` is False the resulting pixbuf might be the passed one.
    Can not fail.
    """

    size = pixbuf.get_width(), pixbuf.get_height()

    scale_w, scale_h = calc_scale_size(boundary, size, scale_up)

    if (scale_w, scale_h) == size:
        if force_copy:
            return pixbuf.copy()
        return pixbuf

    return pixbuf.scale_simple(scale_w, scale_h, GdkPixbuf.InterpType.BILINEAR)


def calc_scale_size(boundary, size, scale_up=True):
    """Returns the biggest possible size to fit into the boundary,
    respecting the aspect ratio.
    If `scale_up` is True the result can be larger than size.
    All sizes have to be > 0.
    """

    bwidth, bheight = boundary
    iwidth, iheight = size

    if bwidth <= 0 or bheight <= 0 or iwidth <= 0 or iheight <= 0:
        raise ValueError

    scale_w, scale_h = iwidth, iheight

    if iwidth > bwidth or iheight > bheight or scale_up:
        bratio = float(bwidth) / bheight
        iratio = float(iwidth) / iheight

        if iratio > bratio:
            scale_w = bwidth
            scale_h = int(bwidth / iratio)
        else:
            scale_w = int(bheight * iratio)
            scale_h = bheight

    return scale_w, scale_h
