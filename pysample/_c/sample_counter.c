//
// Created by 谢建 on 2020-06-03.
//

#include "sample_counter.h"

size_t filenames_hash(const void *key);
int filenames_compare(const void *key1, const void *key2);
size_t traceback_hash(const void *key);
int traceback_compare(const void *key1, const void *key2);

HashMapType filenames_hash_t = {
        .hash_function = &filenames_hash,
        .key_compare = &filenames_compare,
};


HashMapType points_hash_t = {
        .hash_function = &traceback_hash,
        .key_compare = &traceback_compare,
};


size_t filenames_hash(const void *key) {
    return PyObject_Hash((PyObject *)key);
}

int filenames_compare(const void *key1, const void *key2) {
    return PyUnicode_Compare((PyObject *)key1, (PyObject *)key2);
}


size_t traceback_hash(const void *key) {
    size_t hash_value;
    SampleTraceback *tb = (SampleTraceback *)key;
    if (tb->hash_value) {
        return tb->hash_value;
    }

    hash_value = SampleTraceback_Hash(tb);
    tb->hash_value = hash_value;
    return hash_value;
}

int traceback_compare(const void *key1, const void *key2) {
    return SampleTraceback_Compare((SampleTraceback *)key1, (SampleTraceback *)key2);
}


SampleCounter *SampleCounter_Create(int delta) {
    SampleCounter *counter;

    counter = PyMem_Malloc(sizeof(SampleCounter));
    if (counter == NULL) {
        return NULL;
    }
    
    counter->delta = delta;

    counter->filenames = HashMap_Create(&filenames_hash_t);
    if (counter->filenames == NULL) {
        PyMem_Free(counter);
        return NULL;
    }

    counter->points = HashMap_Create(&points_hash_t);
    if (counter->points == NULL) {
        HashMap_Free(counter->filenames);
        PyMem_Free(counter);
        return NULL;
    }
    return counter;
}


void SampleCounter_Free(SampleCounter *counter) {
    HashMapEntry *entry;
    HashMapIterator iterator;
    HASH_MAP_ITERATOR_INIT(&iterator, counter->filenames);

    while ((entry = HashMap_Next(&iterator)) != NULL) {
        assert(PyUnicode_Check(entry->key));
        assert(PyUnicode_Check(entry->val));
        // key equals value, DECREF key or value
        Py_XDECREF(entry->key);
    }
    HashMap_Free(counter->filenames);

    HASH_MAP_ITERATOR_INIT(&iterator, counter->points);

    while ((entry = HashMap_Next(&iterator)) != NULL) {
        SampleTraceback_Free(entry->key);
        // free SamplePoint
        PyMem_Free(entry->val);
    }
    HashMap_Free(counter->points);

    PyMem_Free(counter);
}


int SampleCounter_AddTraceback(SampleCounter *counter, SampleTraceback *traceback) {
    int res;
    SamplePoint *point;

    assert(traceback);

    point = HashMap_Get(counter->points, traceback);
    if (point == NULL) {
        point = PyMem_Malloc(sizeof(SamplePoint));
        if (point == NULL) {
            return -1;
        }

        point->traceback = traceback;
        point->count = 0;
        res = HashMap_Set(counter->points, traceback, point);
        if (res == HASH_MAP_ERR) {
            PyMem_Free(point);
            return -1;
        }
    } else {
        SampleTraceback_Free(traceback);
    }

    point->count += counter->delta;
    return 0;
}


int SampleCounter_AddFrame(SampleCounter *counter, PyObject *frame) {
    PyFrameObject *pyframe;
    SampleTraceback *traceback;

    pyframe = (PyFrameObject *)frame;
    traceback = SampleTraceback_Create(pyframe, counter->filenames);
    if (traceback == NULL) {
        return -1;
    }

    return SampleCounter_AddTraceback(counter, traceback);
}



PyObject *SampleCounter_FlameOutput(SampleCounter *counter) {
    int res;
    SamplePoint *point;
    HashMapEntry *entry;
    HashMapIterator iterator;
    PyObject *empty_sep = NULL;
    PyObject *item_str = NULL, *tb_str = NULL, *str_buffer = NULL, *output = NULL;

    str_buffer = PyList_New(0);
    if (str_buffer == NULL) {
        goto error;
    }

    HASH_MAP_ITERATOR_INIT(&iterator, counter->points);

    while ((entry = HashMap_Next(&iterator)) != NULL) {
        point = entry->val;
        tb_str = SampleTraceback_Dump(point->traceback);
        if (tb_str == NULL) {
            goto error;
        }

        item_str = PyUnicode_FromFormat("%U %d\n", tb_str, point->count);
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

    output = PyUnicode_Join(empty_sep, str_buffer);
    Py_DECREF(empty_sep);
    Py_DECREF(str_buffer);
    return output;

error:
    Py_XDECREF(empty_sep);
    Py_XDECREF(item_str);
    Py_XDECREF(tb_str);
    Py_XDECREF(str_buffer);
    return NULL;
}
