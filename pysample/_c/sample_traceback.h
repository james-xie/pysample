//
// Created by 谢建 on 2020-06-03.
//

#ifndef PYSAMPLE_SAMPLE_TRACEBACK_H
#define PYSAMPLE_SAMPLE_TRACEBACK_H

#include "Python.h"
#include "frameobject.h"
#include "hash_map.h"

#define DEFAULT_MAX_FRAME_NUM 64
#define FINAL_MAX_FRAME_NUM 256

#define MAX_TRACEBACK_MEM_SIZE (sizeof(SampleTraceback) + (FINAL_MAX_FRAME_NUM - DEFAULT_MAX_FRAME_NUM) * sizeof(SampleFrame))

typedef struct {
    int lineno;
    PyObject *filename;
    PyObject *co_name;
} SampleFrame;


typedef struct {
    int nframe;
    size_t hash_value;
    SampleFrame frames[DEFAULT_MAX_FRAME_NUM];
} SampleTraceback;


SampleTraceback *SampleTraceback_Create(PyFrameObject *frame, HashMap *filenames);

void SampleTraceback_Free(SampleTraceback *traceback);

size_t SampleTraceback_Hash(SampleTraceback *traceback);

int SampleTraceback_Compare(SampleTraceback *tb1, SampleTraceback *tb2);

PyObject *shorten_filename(PyObject *filename);

PyObject *SampleTraceback_Dump(SampleTraceback *traceback);

#endif //PYSAMPLE_SAMPLE_TRACEBACK_H
