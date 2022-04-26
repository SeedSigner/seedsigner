#cython: language_level=3

cimport cython

@cython.boundscheck(False)  # Deactivate bounds checking
@cython.wraparound(False)   # Deactivate negative indexing.
@cython.initializedcheck(False)
def rgbtobgr(const char* arr, fb: cython.char[:], unsigned int l):

    cdef unsigned int i

    with nogil:

        for i in range(0, l, 4):

            fb[i     ] = arr[i +  2]
            fb[i +  1] = arr[i +  1]
            fb[i +  2] = arr[i     ]
