/*

 Copyright (c) 2005 Canonical
 Copyright (c) 2004 Conectiva, Inc.

 Written by Anders F Bjorklund <afb@users.sourceforge.net>

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

static PyObject *
_base_arm_eabi(PyObject *self)
{
    PyObject *ret;
#ifdef __ARM_EABI__
    ret = Py_True;
#else
    ret = Py_False;
#endif
    Py_INCREF(ret);
    return ret;
}

static PyMethodDef _base_methods[] = {
    {"arm_eabi", (PyCFunction)_base_arm_eabi, METH_NOARGS, NULL},
    {NULL, NULL}
};

static struct PyModuleDef _base_module = {
    PyModuleDef_HEAD_INIT,
    "_base",             /* m_name */
    "",                  /* m_doc */
    -1,                  /* m_size */
    _base_methods,       /* m_methods */
    NULL,                /* m_reload */
    NULL,                /* m_traverse */
    NULL,                /* m_clear */
    NULL,                /* m_free */
};

void
init_base(void)
{
    PyObject *m;
    m = PyModule_Create(&_base_module);
}

