/*

 Copyright (c) 2005 Conectiva, Inc.

 Written by Gustavo Niemeyer <niemeyer@conectiva.com>

 This file is part of Smart Package Manager.

 Smart Package Manager is free software; you can redistribute it and/or
 modify it under the terms of the GNU General Public License as published
 by the Free Software Foundation; either version 2 of the License, or (at
 your option) any later version.

 Smart Package Manager is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Smart Package Manager; if not, write to the Free Software
 Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

*/

#include <Python.h>
#include <structmember.h>

#include <assert.h>
#include <string.h>
#include <stdlib.h>

#define MAXSIZE 1024

static inline int
min2(int i, int j)        { return i<j?i:j; }
static inline int
min3(int i, int j, int k) { return i<j?(i<k?i:k):(j<k?j:k); };

/*
    Compute Levenhstein distance - http://www.merriampark.com/ld.htm
*/
static int
distance(const char *a, int al, const char *b, int bl,
         int cutoff, float *ratio)
{
    int lst[MAXSIZE];
    const char *t;
    int tl, last, nextlast;
    int ai, bi, minlstai;
    int res;
    if (al > MAXSIZE)
        al = MAXSIZE;
    if (bl > MAXSIZE)
        bl = MAXSIZE;
    if (al == bl && memcmp(a, b, al) == 0) {
        if (ratio)
            *ratio = 1.0;
        return 0;
    }
    if (al < bl) {
        t = a; tl = al;
        a = b; al = bl;
        b = t; bl = tl;
    }
    for (ai = 0; ai != al; ai++)
        lst[ai] = ai+1;
    for (bi = 0; bi != bl; bi++) {
        last = lst[0];
        lst[0] = minlstai = min2(lst[0]+1, bi+(a[0] != b[bi]?1:0));
        for (ai = 1; ai != al; ai++) {
            nextlast = lst[ai];
            lst[ai] = min3(lst[ai-1]+1, lst[ai]+1,
                           last+(a[ai] != b[bi]?1:0));
            last = nextlast;
            if (cutoff != -1 && lst[ai] < minlstai)
                minlstai = lst[ai];
        }
        if (cutoff != -1 && minlstai > cutoff) {
            if (ratio)
                *ratio = 0.0;
            return al;
        }
    }
    res = lst[al-1];
    if (cutoff != -1 && res > cutoff) {
        if (ratio)
            *ratio = 0.0;
        return al;
    }
    if (ratio)
        *ratio = ((float)al-res)/al;
    return res;
}

/*
    Compute Levenhstein distance - http://www.merriampark.com/ld.htm

    Algorithm changed by Gustavo Niemeyer to implement wildcards support.
*/
static int
globdistance(const char *a, int al, const char *b, int bl,
         int cutoff, float *ratio)
{
    int lst[MAXSIZE];
    int last, nextlast;
    int ai, bi, minlstai;
    int maxl;
    int res;
    if (al > MAXSIZE)
        al = MAXSIZE;
    if (bl > MAXSIZE)
        bl = MAXSIZE;
    if (al == bl && memcmp(a, b, al) == 0) {
        if (ratio)
            *ratio = 1.0;
        return 0;
    }
    maxl = al>bl?al:bl;
    for (ai = 0; ai != al; ai++)
        lst[ai] = ai+1;
    for (bi = 0; bi != bl; bi++) {
        if (b[bi] == '*') {
            last = lst[0];
            lst[0] = minlstai = min2(lst[0], bi);
            for (ai = 1; ai != al; ai++) {
                nextlast = lst[ai];
                lst[ai] = min3(lst[ai-1], lst[ai], last);
                last = nextlast;
                if (cutoff != -1 && lst[ai] < minlstai)
                    minlstai = lst[ai];
            }
        } else if (b[bi] == '?') {
            last = lst[0];
            lst[0] = minlstai = min2(lst[0]+1, bi);
            for (ai = 1; ai != al; ai++) {
                nextlast = lst[ai];
                lst[ai] = min3(lst[ai-1]+1, lst[ai]+1, last);
                last = nextlast;
                if (cutoff != -1 && lst[ai] < minlstai)
                    minlstai = lst[ai];
            }
        } else {
            last = lst[0];
            lst[0] = minlstai = min2(lst[0]+1, bi+(a[0] != b[bi]?1:0));
            for (ai = 1; ai != al; ai++) {
                nextlast = lst[ai];
                lst[ai] = min3(lst[ai-1]+1, lst[ai]+1,
                               last+(a[ai] != b[bi]?1:0));
                last = nextlast;
                if (cutoff != -1 && lst[ai] < minlstai)
                    minlstai = lst[ai];
            }
        }
        if (cutoff != -1 && minlstai > cutoff) {
            if (ratio)
                *ratio = 0.0;
            return maxl;
        }
    }
    res = lst[al-1];
    if (cutoff != -1 && res > cutoff) {
        if (ratio)
            *ratio = 0.0;
        return maxl;
    }
    if (ratio)
        *ratio = ((float)maxl-res)/maxl;
    return res;
}

static PyObject *
cdistance_distance(PyObject *self, PyObject *args)
{
    PyObject *ao, *bo, *cutoffo = Py_None;
    PyObject *resulto, *ratioo, *ret;
    const char *a, *b, *t;
    int cutoff = -1;
    int al, bl, tl;
    float ratio;
    if (!PyArg_ParseTuple(args, "SS|O", &ao, &bo, &cutoffo))
        return NULL;
    a = PyString_AS_STRING(ao);
    b = PyString_AS_STRING(bo);
    al = PyString_GET_SIZE(ao);
    bl = PyString_GET_SIZE(bo);
    if (al < bl) {
        t = a; tl = al;
        a = b; al = bl;
        b = t; bl = tl;
    }
    if (cutoffo != Py_None) {
        if (PyInt_Check(cutoffo)) {
            cutoff = (int)PyInt_AsLong(cutoffo);
        } else if (PyFloat_Check(cutoffo)) {
            cutoff = (int)al-PyFloat_AsDouble(cutoffo)*al;
        } else {
            PyErr_SetString(PyExc_TypeError, "cutoff must be int or float");
            return NULL;
        }
    }
    resulto = PyInt_FromLong(distance(a, al, b, bl, cutoff, &ratio));
    if (!resulto) return NULL;
    ratioo = PyFloat_FromDouble((double)ratio);
    if (!ratioo) return NULL;
    ret = PyTuple_New(2);
    if (!ret) return NULL;
    PyTuple_SET_ITEM(ret, 0, resulto);
    PyTuple_SET_ITEM(ret, 1, ratioo);
    return ret;
}

static PyObject *
cdistance_globdistance(PyObject *self, PyObject *args)
{
    PyObject *ao, *bo, *cutoffo = Py_None;
    PyObject *resulto, *ratioo, *ret;
    const char *a, *b;
    int cutoff = -1;
    int al, bl, maxl;
    float ratio;
    if (!PyArg_ParseTuple(args, "SS|O", &ao, &bo, &cutoffo))
        return NULL;
    a = PyString_AS_STRING(ao);
    b = PyString_AS_STRING(bo);
    al = PyString_GET_SIZE(ao);
    bl = PyString_GET_SIZE(bo);
    maxl = al>bl?al:bl;
    if (cutoffo != Py_None) {
        if (PyInt_Check(cutoffo)) {
            cutoff = (int)PyInt_AsLong(cutoffo);
        } else if (PyFloat_Check(cutoffo)) {
            cutoff = maxl-PyFloat_AsDouble(cutoffo)*maxl;
        } else {
            PyErr_SetString(PyExc_TypeError, "cutoff must be int or float");
            return NULL;
        }
    }
    resulto = PyInt_FromLong(globdistance(a, al, b, bl, cutoff, &ratio));
    if (!resulto) return NULL;
    ratioo = PyFloat_FromDouble((double)ratio);
    if (!ratioo) return NULL;
    ret = PyTuple_New(2);
    if (!ret) return NULL;
    PyTuple_SET_ITEM(ret, 0, resulto);
    PyTuple_SET_ITEM(ret, 1, ratioo);
    return ret;
}

static PyMethodDef cdistance_methods[] = {
    {"distance", (PyCFunction)cdistance_distance, METH_VARARGS, NULL},
    {"globdistance", (PyCFunction)cdistance_globdistance, METH_VARARGS, NULL},
    {NULL, NULL}
};

DL_EXPORT(void)
initcdistance(void)
{
    PyObject *m;
    m = Py_InitModule3("cdistance", cdistance_methods, "");
}

/* vim:ts=4:sw=4:et
*/
