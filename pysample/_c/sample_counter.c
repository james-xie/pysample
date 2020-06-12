//
// Created by 谢建 on 2020-06-03.
//

#include "sample_counter.h"

#define DEFAULT_PATH_ARRAY_SIZE 10


#ifdef MS_WINDOWS
#define PATH_SEPARATOR '\\'
#else
#define PATH_SEPARATOR '/'
#endif



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


SampleCounter *SampleCounter_Create(int delta, PyObject *sys_path) {
    SampleCounter *counter = NULL;

    counter = PyMem_Malloc(sizeof(SampleCounter));
    if (counter == NULL) {
        return NULL;
    }
    
    counter->delta = delta;
    Py_INCREF(sys_path);
    counter->sys_path = sys_path;

    counter->filenames = HashMap_Create(&filenames_hash_t);
    if (counter->filenames == NULL) {
        PyMem_Free(counter);
        return NULL;
    }

    counter->short_filenames = HashMap_Create(&filenames_hash_t);
    if (counter->short_filenames == NULL) {
        HashMap_Free(counter->filenames);
        PyMem_Free(counter);
        return NULL;
    }

    counter->points = HashMap_Create(&points_hash_t);
    if (counter->points == NULL) {
        HashMap_Free(counter->filenames);
        HashMap_Free(counter->short_filenames);
        PyMem_Free(counter);
        return NULL;
    }
    return counter;
}


void SampleCounter_Free(SampleCounter *counter) {
    HashMapEntry *entry;
    HashMapIterator iterator;

    Py_DECREF(counter->sys_path);

    HASH_MAP_ITERATOR_INIT(&iterator, counter->filenames);

    while ((entry = HashMap_Next(&iterator)) != NULL) {
        assert(PyUnicode_Check(entry->key));
        assert(PyUnicode_Check(entry->val));
        // key equals value, DECREF key or value
        Py_XDECREF(entry->key);
    }
    HashMap_Free(counter->filenames);

    HASH_MAP_ITERATOR_INIT(&iterator, counter->short_filenames);

    while ((entry = HashMap_Next(&iterator)) != NULL) {
        assert(PyUnicode_Check(entry->key));
        assert(PyUnicode_Check(entry->val));
        Py_XDECREF(entry->key);
        Py_XDECREF(entry->val);
    }
    HashMap_Free(counter->short_filenames);

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


PyObject *shorten_filename(PyObject *filename, SampleCounter *counter) {
    int n, res;
    Py_ssize_t len;
    PyObject *item, *short_filename = NULL;
    PyObject *sys_path = counter->sys_path;
    PackagePathArray *path_array = get_path_array();

    if (path_array == NULL) {
        return NULL;
    }

    short_filename = HashMap_Get(counter->short_filenames, filename);
    if (short_filename) {
        Py_INCREF(short_filename);
        return short_filename;
    }

    // The filename starts with the path in the cached path array.
    for (n=0; n<path_array->length; n++) {
        item = path_array->array[n];
        len = PyUnicode_GET_LENGTH(item);
        if (PyUnicode_Find(filename, item, 0, len, 1) >= 0) {
            short_filename = strip_package_path(filename, item);
            res = HashMap_Set(counter->short_filenames, filename, short_filename);
            if (res == 0) {
                // Successfully put short_filename in hashmap
                Py_INCREF(filename);
                Py_INCREF(short_filename);
            }
            return short_filename;
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
            short_filename = strip_package_path(filename, item);
            res = HashMap_Set(counter->short_filenames, filename, short_filename);
            if (res == 0) {
                // Successfully put short_filename in hashmap
                Py_INCREF(filename);
                Py_INCREF(short_filename);
            }

            add_path_to_array(path_array, item);
            return short_filename;
        }
    }

    return NULL;
}


PyObject *dump_traceback(SampleCounter *counter, SampleTraceback *traceback) {
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

        filename = shorten_filename(frame->filename, counter);
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



/**
 * Generate the collected stacks information.
 * The output stack information will be used as the input of the flame graph.
 *
 * See: https://github.com/brendangregg/FlameGraph
 *
 * @param counter
 * @return
 */
PyObject *SampleCounter_FlameOutput(SampleCounter *counter) {
    int i;
    SamplePoint *point;
    HashMapEntry *entry;
    HashMapIterator iterator;
    PyObject *empty_sep = NULL;
    PyObject *item_str = NULL, *tb_str = NULL, *str_buffer = NULL, *output = NULL;

    if (counter->points->used <= 0) {
        return PyUnicode_FromString("");
    }

    str_buffer = PyList_New(counter->points->used);
    if (str_buffer == NULL) {
        goto error;
    }

    HASH_MAP_ITERATOR_INIT(&iterator, counter->points);

    i = 0;
    while ((entry = HashMap_Next(&iterator)) != NULL) {
        point = entry->val;
        tb_str = dump_traceback(counter, point->traceback);
        if (tb_str == NULL) {
            goto error;
        }

        item_str = PyUnicode_FromFormat("%U %d\n", tb_str, point->count);
        Py_DECREF(tb_str);
        if (item_str == NULL) {
            goto error;
        }

        PyList_SET_ITEM(str_buffer, i, item_str);
        item_str = NULL;

        i++;
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
