//
// Created by 谢建 on 2020-06-03.
//

#include <stdio.h>
#include "sample_traceback.h"

#define PyHASH_MULTIPLIER 1000003UL  /* 0xf4243 */




static inline PyObject *get_unknown_str() {
    static PyObject *unknown_str = NULL;

    if (unknown_str == NULL) {
        unknown_str = PyUnicode_FromString("<unknown>");
        if (unknown_str == NULL) {
            return NULL;
        }
    }
    return unknown_str;
}


static void build_sample_frame(SampleFrame *sframe, PyFrameObject *pyframe, HashMap *filenames) {
    static PyObject *__name__ = NULL;

    PyCodeObject *code;
    PyObject *filename, *ref_filename;
    PyObject *unknown_str = get_unknown_str();

    if (__name__ == NULL) {
        __name__ = PyUnicode_FromString("__name__");
        if (__name__ == NULL) {
            return;
        }
    }

    if (unknown_str == NULL) {
        return;
    }

    assert(filenames);
    code = pyframe->f_code;
    if (code == NULL) {
        return;
    }

    sframe->lineno = PyFrame_GetLineNumber(pyframe);

    if (code->co_filename) {
        filename = code->co_filename;
        ref_filename = HashMap_Get(filenames, filename);
        if (ref_filename == NULL) {
            int res = HashMap_Set(filenames, filename, filename);
            if (res == HASH_MAP_ERR) {
                return;
            }
            Py_INCREF(filename);
        } else {
            filename = ref_filename;
        }
    } else {
        filename = get_unknown_str();
    }
    Py_INCREF(filename);
    sframe->filename = filename;

    if (code->co_name) {
        sframe->co_name = code->co_name;
    } else {
        sframe->co_name = get_unknown_str();
    }
    Py_INCREF(sframe->co_name);

    if (pyframe->f_globals) {
        sframe->name = PyDict_GetItem(pyframe->f_globals, __name__);
    }
    if (sframe->name == NULL) {
        sframe->name = get_unknown_str();
    }
    Py_INCREF(sframe->name);
}


SampleTraceback *SampleTraceback_Create(PyFrameObject *frame, HashMap *filenames) {
    SampleFrame *sframe;
    SampleTraceback *traceback;

    traceback = PyMem_Malloc(sizeof(SampleTraceback));
    if (traceback == NULL)
        return NULL;

    traceback->nframe = 0;
    traceback->hash_value = 0;

    for (;frame != NULL; frame = frame->f_back) {
        if (traceback->nframe >= DEFAULT_MAX_FRAME_NUM) {
            if (traceback->nframe < FINAL_MAX_FRAME_NUM) {
                SampleTraceback *new_tb = realloc(traceback, MAX_TRACEBACK_MEM_SIZE);
                if (new_tb == NULL) {
                    break;
                }
                traceback = new_tb;
            } else {
                break;
            }
        }

        sframe = &traceback->frames[traceback->nframe++];
        sframe->lineno = 0;
        sframe->filename = NULL;
        sframe->name = NULL;
        sframe->co_name = NULL;
        build_sample_frame(sframe, frame, filenames);
        if (sframe->filename == NULL) {
            PyMem_Free(traceback);
            return NULL;
        }
    }

    return traceback;
}


void SampleTraceback_Free(SampleTraceback *traceback) {
    int n = traceback->nframe;
    SampleFrame *sframe;

    while (--n >= 0) {
        sframe = &traceback->frames[n];
        Py_XDECREF(sframe->filename);
        Py_XDECREF(sframe->co_name);
        Py_XDECREF(sframe->name);
    }

    PyMem_Free(traceback);
}


size_t SampleTraceback_Hash(SampleTraceback *traceback) {
    size_t x, y;  /* Unsigned for defined overflow behavior. */
    int len = traceback->nframe;
    size_t mult = PyHASH_MULTIPLIER;
    SampleFrame *frame;

    x = 0x345678UL;
    frame = traceback->frames;
    while (--len >= 0) {
        y = (size_t)frame->filename;
        y ^= (size_t)frame->lineno;
        frame++;

        x = (x ^ y) * mult;
        /* the cast might truncate len; that doesn't change hash stability */
        mult += (size_t)(82520UL + len + len);
    }
    x += 97531UL;
    return x;
}


/**
 * Compare with two SampleTraceback object.
 * Returns 0 if the two are equal, otherwise it returns 1
 *
 * @param tb1
 * @param tb2
 * @return
 */
int SampleTraceback_Compare(SampleTraceback *tb1, SampleTraceback *tb2) {
    int n;
    assert(tb1);
    assert(tb2);

    if (tb1->nframe != tb2->nframe) {
        return 1;
    }

    n = tb1->nframe;
    while (--n >= 0) {
        if (tb1->frames[n].lineno != tb2->frames[n].lineno) {
            return 1;
        }
        if (tb1->frames[n].filename != tb2->frames[n].filename) {
            return 1;
        }
    }
    return 0;
}


PyObject *SampleTraceback_Dump(SampleTraceback *traceback) {
    int res;
    int n = traceback->nframe;
    SampleFrame *frame;
    PyObject *empty_sep = NULL;
    PyObject *item_str = NULL, *str_buffer = NULL, *tb_string = NULL;

    str_buffer = PyList_New(0);
    if (str_buffer == NULL) {
        return NULL;
    }

    while (--n >= 0) {
        frame = &traceback->frames[n];

        item_str = PyUnicode_FromFormat("%U:%d (%U);", frame->co_name, frame->lineno, frame->name);
        if (item_str == NULL) {
            goto error;
        }

        res = PyList_Append(str_buffer, item_str);
        if (res != 0) {
            goto error;
        }
        Py_DECREF(item_str);
        item_str = NULL;
    }

    empty_sep = PyUnicode_FromString("");
    if (empty_sep == NULL) {
        goto error;
    }

    tb_string = PyUnicode_Join(empty_sep, str_buffer);
    Py_DECREF(empty_sep);
    Py_DECREF(str_buffer);
    return tb_string;

error:
    Py_XDECREF(item_str);
    Py_XDECREF(str_buffer);
    return NULL;
}
