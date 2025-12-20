#cython: language_level=3
"""
Fast RGB to BGR conversion for Raspberry Pi framebuffer.

Based on mutatrum's fast-pillow-fb:
https://github.com/mutatrum/fast-pillow-fb

This converts RGB (3 bytes/pixel) to BGRA (4 bytes/pixel) for 32-bit framebuffers.

Compile with: pip install cython && python -c "import pyximport; pyximport.install()"
Or the module will auto-compile on first import if cython is installed.
"""

cimport cython

@cython.boundscheck(False)  # Deactivate bounds checking
@cython.wraparound(False)   # Deactivate negative indexing
@cython.initializedcheck(False)
def rgbtobgr(const unsigned char* rgb, unsigned char[:] fb, unsigned int num_pixels):
    """
    Convert RGB (3 bytes/pixel) to BGRA (4 bytes/pixel) and write to framebuffer.
    
    Args:
        rgb: Source RGB byte array from PIL image.tobytes() (3 bytes per pixel)
        fb: Destination framebuffer mmap (4 bytes per pixel)
        num_pixels: Number of pixels (width * height)
    """
    cdef unsigned int i
    cdef unsigned int src_idx
    cdef unsigned int dst_idx

    with nogil:
        for i in range(num_pixels):
            src_idx = i * 3
            dst_idx = i * 4
            fb[dst_idx    ] = rgb[src_idx + 2]  # B <- R
            fb[dst_idx + 1] = rgb[src_idx + 1]  # G <- G  
            fb[dst_idx + 2] = rgb[src_idx    ]  # R <- B
            fb[dst_idx + 3] = 255               # A = 255 (opaque)


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.initializedcheck(False)
def rgbx_to_bgrx(const unsigned char* rgbx, unsigned char[:] fb, unsigned int length):
    """
    Convert RGBX (4 bytes/pixel) to BGRX (4 bytes/pixel) - just swap R and B.
    
    Use this if PIL image is converted to RGBX first (faster than RGB to BGRA).
    
    Args:
        rgbx: Source RGBX byte array (4 bytes per pixel)
        fb: Destination framebuffer mmap (4 bytes per pixel)
        length: Length in bytes
    """
    cdef unsigned int i

    with nogil:
        for i in range(0, length, 4):
            fb[i    ] = rgbx[i + 2]  # B <- R
            fb[i + 1] = rgbx[i + 1]  # G <- G
            fb[i + 2] = rgbx[i    ]  # R <- B
            # fb[i + 3] unchanged (alpha/padding)
