//
// Created by 谢建 on 2020-06-03.
//

#include <stdio.h>
#include <string.h>
#include "sample_traceback.h"

#define PyHASH_MULTIPLIER 1000003UL  /* 0xf4243 */

#define DEFAULT_PATH_ARRAY_SIZE 10

#ifdef MS_WINDOWS
#define PATH_SEPARATOR '\\'
#else
#define PATH_SEPARATOR '/'
#endif


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




typedef struct {
    int length;
    int max_length;
    PyObject *array[DEFAULT_PATH_ARRAY_SIZE];
} PackagePathArray;


static PackagePathArray *get_path_array() {
    static PackagePathArray *path_array = NULL;

    if (path_array == NULL) {
        path_array = PyMem_Malloc(sizeof(PackagePathArray));
        if (path_array == NULL) {
            return NULL;
        }

        path_array->length = 0;
        path_array->max_length = DEFAULT_PATH_ARRAY_SIZE;
    }

    if (path_array->length >= path_array->max_length) {
        int max_length = path_array->max_length;
        PackagePathArray *tmp = PyMem_Realloc(path_array, max_length * 2);
        if (tmp == NULL) {
            return NULL;
        }
        path_array = tmp;
        path_array->length = max_length;
        path_array->max_length = max_length * 2;
    }

    return path_array;
}


static void add_path_to_array(PackagePathArray *path_array, PyObject *path) {
    int i;
    PyObject *item;
    Py_ssize_t path_len = PyUnicode_GET_LENGTH(path);

    for (i=0; i<path_array->length; i++) {
        item = path_array->array[i];
        if (path_len >= PyUnicode_GET_LENGTH(item)) {
            void* src = (char *)path_array->array + i * sizeof(PyObject *);
            void* dest = (char *)src + sizeof(PyObject *);
            size_t size = (path_array->length - i) * sizeof(PyObject *);
            memmove(dest, src, size);

            Py_INCREF(path);
            path_array->array[i] = path;
            path_array->length++;
            return;
        }
    }

    Py_INCREF(path);
    path_array->array[path_array->length++] = path;
}


static inline PyObject *strip_package_path(PyObject *filename, PyObject *package_path) {
    int len = PyUnicode_GET_LENGTH(package_path);
    int name_len = PyUnicode_GET_LENGTH(filename);

    if (name_len > len) {
        if (PyUnicode_READ_CHAR(filename, len) == PATH_SEPARATOR) {
            len += 1;
        }
    }
    return PyUnicode_Substring(filename, len, name_len);
}


PyObject *shorten_filename(PyObject *filename, PyObject *sys_path) {
    int n;
    Py_ssize_t len;
    PyObject *item;
    PackagePathArray *path_array = get_path_array();

    if (path_array == NULL) {
        return NULL;
    }

    // The filename starts with the path in the cached path array.
    for (n=0; n<path_array->length; n++) {
        item = path_array->array[n];
        len = PyUnicode_GET_LENGTH(item);
        if (PyUnicode_Find(filename, item, 0, len, 1) >= 0) {
            return strip_package_path(filename, item);
        }
    }

    // The cached path array cannot be used to shorten the file name, so we
    // try to strip the prefix path that starts with the path in sys.path.
    if (sys_path == NULL || sys_path == Py_None) {
        return filename;
    }

    assert(PyList_Check(sys_path));

    for (n=0; n<PyList_GET_SIZE(sys_path); n++) {
        item = PyList_GET_ITEM(sys_path, n);
        len = PyUnicode_GET_LENGTH(item);
        if (len <= 0) {
            continue;
        }

        if (PyUnicode_Find(filename, item, 0, len, 1) >= 0) {
            PyObject *substring = strip_package_path(filename, item);
            add_path_to_array(path_array, item);
            return substring;
        }
    }

    return NULL;
}


PyObject *SampleTraceback_Dump(SampleTraceback *traceback, PyObject *sys_path) {
    int i, n = traceback->nframe;
    SampleFrame *frame;
    PyObject *empty_sep = NULL, *filename;
    PyObject *item_str = NULL, *str_buffer = NULL, *tb_string = NULL;

    str_buffer = PyList_New(n);
    if (str_buffer == NULL) {
        return NULL;
    }

    for (i=0; i<n; i++) {
        frame = &traceback->frames[n-i-1];

        filename = shorten_filename(frame->filename, sys_path);
        if (filename == NULL) {
            filename = frame->filename;
        }

        item_str = PyUnicode_FromFormat("%U (%U:%d);", frame->co_name, filename, frame->lineno);
        if (filename != frame->filename) {
            Py_DECREF(filename);
        }
        if (item_str == NULL) {
            goto error;
        }

        PyList_SET_ITEM(str_buffer, i, item_str);
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
