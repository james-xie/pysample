cdef extern from "sample.h":
    ctypedef struct SampleCounter

    SampleCounter *SampleCounter_Create(int delta);

    void SampleCounter_Free(SampleCounter *counter);

    int SampleCounter_AddFrame(SampleCounter *counter, object frame);

    object SampleCounter_FlameOutput(SampleCounter *counter, object sys_path);


cdef class PySampleCounter:
    cdef object _sys_path
    cdef SampleCounter *_counter


    
