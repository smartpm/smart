
#include <Python.h>
#include <structmember.h>

#include <string.h>

#ifndef Py_RETURN_NONE
#define Py_RETURN_NONE do {Py_INCREF(Py_None); return Py_None;} while (0)
#endif

#define CALLMETHOD(obj, ...) \
    do { \
        PyObject *res = \
            PyObject_CallMethod((PyObject *)(obj), __VA_ARGS__); \
        if (!res) return NULL; \
        Py_DECREF(res); \
    } while (0)

#define STR(obj) PyString_AS_STRING(obj)

staticforward PyTypeObject Package_Type;
staticforward PyTypeObject Provides_Type;
staticforward PyTypeObject Depends_Type;
staticforward PyTypeObject Loader_Type;
staticforward PyTypeObject Cache_Type;

typedef struct {
    PyObject_HEAD
    PyObject *name;
    PyObject *version;
    PyObject *provides;
    PyObject *requires;
    PyObject *obsoletes;
    PyObject *conflicts;
    PyObject *installed;
    PyObject *loaderinfo;
} PackageObject;

typedef struct {
    PyObject_HEAD
    PyObject *name;
    PyObject *version;
    PyObject *packages;
    PyObject *requiredby;
    PyObject *obsoletedby;
    PyObject *conflictedby;
} ProvidesObject;

typedef struct {
    PyObject_HEAD
    PyObject *name;
    PyObject *version;
    PyObject *relation;
    PyObject *packages;
    PyObject *providedby;
} DependsObject;

typedef struct {
    PyObject_HEAD
    PyObject *_cache;
    PyObject *_packages;
    PyObject *_installed;
    PyObject *Package;
    PyObject *Provides;
    PyObject *Requires;
    PyObject *Obsoletes;
    PyObject *Conflicts;
} LoaderObject;

typedef struct {
    PyObject_HEAD
    PyObject *_loaders;
    PyObject *_packages;
    PyObject *_provides;
    PyObject *_requires;
    PyObject *_obsoletes;
    PyObject *_conflicts;
    PyObject *_pkgnames;
    PyObject *_prvnames;
    PyObject *_reqnames;
    PyObject *_obsnames;
    PyObject *_cnfnames;
    PyObject *_pkgmap;
    PyObject *_prvmap;
    PyObject *_reqmap;
    PyObject *_obsmap;
    PyObject *_cnfmap;
} CacheObject;

static int
Package_init(PackageObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, "O!O!", &PyString_Type, &self->name,
                          &PyString_Type, &self->version))
        return -1;
    Py_INCREF(self->name);
    Py_INCREF(self->version);
    self->provides = PyList_New(0);
    self->requires = PyList_New(0);
    self->obsoletes = PyList_New(0);
    self->conflicts = PyList_New(0);
    Py_INCREF(Py_False);
    self->installed = Py_False;
    self->loaderinfo = PyDict_New();
    return 0;
}

static void
Package_dealloc(PackageObject *self)
{
    Py_XDECREF(self->name);
    Py_XDECREF(self->version);
    Py_XDECREF(self->provides);
    Py_XDECREF(self->requires);
    Py_XDECREF(self->obsoletes);
    Py_XDECREF(self->conflicts);
    Py_XDECREF(self->installed);
    Py_XDECREF(self->loaderinfo);
    self->ob_type->tp_free((PyObject *)self);
}

static PyObject *
Package_str(PackageObject *self)
{
    if (!PyString_Check(self->name) || !PyString_Check(self->version)) {
        PyErr_SetString(PyExc_TypeError,
                        "package name or version is not string");
        return NULL;
    }
    return PyString_FromFormat("%s-%s", STR(self->name), STR(self->version));
}

static int
Package_compare(PackageObject *self, PackageObject *other)
{
    int rc = -1;
    if (PyObject_IsInstance((PyObject *)other, (PyObject *)&Package_Type)) {
        const char *self_name, *other_name;
        if (!PyString_Check(self->name) || !PyString_Check(other->name)) {
            PyErr_SetString(PyExc_TypeError,
                            "package name is not string");
            return -1;
        }
        self_name = STR(self->name);
        other_name = STR(other->name);
        rc = strcmp(self_name, other_name);
        if (rc == 0) {
            const char *self_version, *other_version;
            if (!PyString_Check(self->version) ||
                !PyString_Check(other->version)) {
                PyErr_SetString(PyExc_TypeError,
                                "package version is not string");
                return -1;
            }
            self_version = STR(self->version);
            other_version = STR(other->version);
            rc = strcmp(self_version, other_version);
        }
    }
    return rc > 0 ? 1 : ( rc < 0 ? -1 : 0);
}

static PyObject *
Package_equals(PackageObject *self, PackageObject *other)
{
    int i, j, ilen, jlen;
    PyObject *ret = Py_True;

    if (!PyObject_IsInstance((PyObject *)other, (PyObject *)&Package_Type)) {
        PyErr_SetString(PyExc_TypeError, "package expected");
        return NULL;
    }

    if (strcmp(STR(self->name), STR(other->name)) != 0 ||
        strcmp(STR(self->version), STR(other->version)) != 0 ||
        PyList_GET_SIZE(self->provides) != PyList_GET_SIZE(other->provides) ||
        PyList_GET_SIZE(self->requires) != PyList_GET_SIZE(other->requires) ||
        PyList_GET_SIZE(self->obsoletes) != PyList_GET_SIZE(other->obsoletes) ||
        PyList_GET_SIZE(self->conflicts) != PyList_GET_SIZE(other->conflicts)) {
        ret = Py_False;
        goto exit;
    }

    ilen = PyList_GET_SIZE(self->provides);
    jlen = PyList_GET_SIZE(other->provides);
    for (i = 0; i != ilen; i++) {
        PyObject *item = PyList_GET_ITEM(self->provides, i);
        for (j = 0; j != jlen; j++)
            if (item == PyList_GET_ITEM(other->provides, j))
                break;
        if (j == jlen) {
            ret = Py_False;
            goto exit;
        }
    }

    ilen = PyList_GET_SIZE(self->requires);
    jlen = PyList_GET_SIZE(other->requires);
    for (i = 0; i != ilen; i++) {
        PyObject *item = PyList_GET_ITEM(self->requires, i);
        for (j = 0; j != jlen; j++)
            if (item == PyList_GET_ITEM(other->requires, j))
                break;
        if (j == jlen) {
            ret = Py_False;
            goto exit;
        }
    }

    ilen = PyList_GET_SIZE(self->obsoletes);
    jlen = PyList_GET_SIZE(other->obsoletes);
    for (i = 0; i != ilen; i++) {
        PyObject *item = PyList_GET_ITEM(self->obsoletes, i);
        for (j = 0; j != jlen; j++)
            if (item == PyList_GET_ITEM(other->obsoletes, j))
                break;
        if (j == jlen) {
            ret = Py_False;
            goto exit;
        }
    }

    ilen = PyList_GET_SIZE(self->conflicts);
    jlen = PyList_GET_SIZE(other->conflicts);
    for (i = 0; i != ilen; i++) {
        PyObject *item = PyList_GET_ITEM(self->conflicts, i);
        for (j = 0; j != jlen; j++)
            if (item == PyList_GET_ITEM(other->conflicts, j))
                break;
        if (j == jlen) {
            ret = Py_False;
            goto exit;
        }
    }

exit:
    Py_INCREF(ret);
    return ret;
}

static PyMethodDef Package_methods[] = {
    {"equals", (PyCFunction)Package_equals, METH_O, NULL},
    {NULL, NULL}
};

#define OFF(x) offsetof(PackageObject, x)
static PyMemberDef Package_members[] = {
    {"name", T_OBJECT, OFF(name), 0, 0},
    {"version", T_OBJECT, OFF(version), 0, 0},
    {"provides", T_OBJECT, OFF(provides), 0, 0},
    {"requires", T_OBJECT, OFF(requires), 0, 0},
    {"obsoletes", T_OBJECT, OFF(obsoletes), 0, 0},
    {"conflicts", T_OBJECT, OFF(conflicts), 0, 0},
    {"installed", T_OBJECT, OFF(installed), 0, 0},
    {"loaderinfo", T_OBJECT, OFF(loaderinfo), 0, 0},
    {NULL}
};
#undef OFF

statichere PyTypeObject Package_Type = {
	PyObject_HEAD_INIT(NULL)
	0,			/*ob_size*/
	"ccache.Package",	/*tp_name*/
	sizeof(PackageObject), /*tp_basicsize*/
	0,			/*tp_itemsize*/
	(destructor)Package_dealloc, /*tp_dealloc*/
	0,			/*tp_print*/
	0,			/*tp_getattr*/
	0,			/*tp_setattr*/
	(cmpfunc)Package_compare, /*tp_compare*/
	0,			/*tp_repr*/
	0,			/*tp_as_number*/
	0,			/*tp_as_sequence*/
	0,			/*tp_as_mapping*/
	0,			/*tp_hash*/
    0,                      /*tp_call*/
    (reprfunc)Package_str,  /*tp_str*/
    PyObject_GenericGetAttr,/*tp_getattro*/
    PyObject_GenericSetAttr,/*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE, /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    Package_methods,        /*tp_methods*/
    Package_members,        /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)Package_init, /*tp_init*/
    PyType_GenericAlloc,    /*tp_alloc*/
    PyType_GenericNew,      /*tp_new*/
    _PyObject_Del,          /*tp_free*/
    0,                      /*tp_is_gc*/
};

static int
Provides_init(ProvidesObject *self, PyObject *args)
{
    self->version = Py_None;
    if (!PyArg_ParseTuple(args, "O!|O", &PyString_Type, &self->name,
                          &self->version))
        return -1;
    Py_INCREF(self->name);
    Py_INCREF(self->version);
    self->packages = PyList_New(0);
    self->requiredby = PyList_New(0);
    self->obsoletedby = PyList_New(0);
    self->conflictedby = PyList_New(0);
    return 0;
}

static void
Provides_dealloc(ProvidesObject *self)
{
    Py_XDECREF(self->name);
    Py_XDECREF(self->version);
    Py_XDECREF(self->packages);
    Py_XDECREF(self->requiredby);
    Py_XDECREF(self->obsoletedby);
    Py_XDECREF(self->conflictedby);
    self->ob_type->tp_free((PyObject *)self);
}

static PyObject *
Provides_str(ProvidesObject *self)
{
    if (!PyString_Check(self->name)) {
        PyErr_SetString(PyExc_TypeError, "package name is not string");
        return NULL;
    }
    if (self->version != Py_None) {
        if (!PyString_Check(self->version)) {
            PyErr_SetString(PyExc_TypeError, "package version is not string");
            return NULL;
        }
        return PyString_FromFormat("%s = %s", STR(self->name),
                                              STR(self->version));
    }
    Py_INCREF(self->name);
    return self->name;
}

static int
Provides_compare(ProvidesObject *self, ProvidesObject *other)
{
    int rc = -1;
    if (PyObject_IsInstance((PyObject *)other, (PyObject *)&Provides_Type)) {
        rc = strcmp(STR(self->name), STR(other->name));
        if (rc == 0)
            rc = strcmp(STR(self->version), STR(other->version));
    }
    return rc > 0 ? 1 : ( rc < 0 ? -1 : 0);
}

#define OFF(x) offsetof(ProvidesObject, x)
static PyMemberDef Provides_members[] = {
    {"name", T_OBJECT, OFF(name), 0, 0},
    {"version", T_OBJECT, OFF(version), 0, 0},
    {"packages", T_OBJECT, OFF(packages), 0, 0},
    {"requiredby", T_OBJECT, OFF(requiredby), 0, 0},
    {"obsoletedby", T_OBJECT, OFF(obsoletedby), 0, 0},
    {"conflictedby", T_OBJECT, OFF(conflictedby), 0, 0},
    {NULL}
};
#undef OFF

statichere PyTypeObject Provides_Type = {
	PyObject_HEAD_INIT(NULL)
	0,			/*ob_size*/
	"ccache.Provides",	/*tp_name*/
	sizeof(ProvidesObject), /*tp_basicsize*/
	0,			/*tp_itemsize*/
	(destructor)Provides_dealloc, /*tp_dealloc*/
	0,			/*tp_print*/
	0,			/*tp_getattr*/
	0,			/*tp_setattr*/
	(cmpfunc)Provides_compare, /*tp_compare*/
	0,			/*tp_repr*/
	0,			/*tp_as_number*/
	0,			/*tp_as_sequence*/
	0,			/*tp_as_mapping*/
	0,			/*tp_hash*/
    0,                      /*tp_call*/
    (reprfunc)Provides_str, /*tp_str*/
    PyObject_GenericGetAttr,/*tp_getattro*/
    PyObject_GenericSetAttr,/*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE, /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    0,                      /*tp_methods*/
    Provides_members,       /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)Provides_init, /*tp_init*/
    PyType_GenericAlloc,    /*tp_alloc*/
    PyType_GenericNew,      /*tp_new*/
    _PyObject_Del,          /*tp_free*/
    0,                      /*tp_is_gc*/
};

static int
Depends_init(DependsObject *self, PyObject *args)
{
    self->version = Py_None;
    self->relation = Py_None;
    if (!PyArg_ParseTuple(args, "O!|OO", &PyString_Type, &self->name,
                          &self->version, &self->relation))
        return -1;
    Py_INCREF(self->name);
    Py_INCREF(self->version);
    Py_INCREF(self->relation);
    self->packages = PyList_New(0);
    self->providedby = PyList_New(0);
    return 0;
}

static void
Depends_dealloc(DependsObject *self)
{
    Py_XDECREF(self->name);
    Py_XDECREF(self->version);
    Py_XDECREF(self->relation);
    Py_XDECREF(self->packages);
    Py_XDECREF(self->providedby);
    self->ob_type->tp_free((PyObject *)self);
}

static PyObject *
Depends_matches(DependsObject *self, PyObject *prv)
{
    Py_INCREF(Py_False);
    return Py_False;
}

static PyObject *
Depends_str(DependsObject *self)
{
    if (!PyString_Check(self->name)) {
        PyErr_SetString(PyExc_TypeError,
                        "package name is not string");
        return NULL;
    }
    if (self->version != Py_None) {
        if (!PyString_Check(self->version) ||
            !PyString_Check(self->relation)) {
            PyErr_SetString(PyExc_TypeError,
                            "package version or relation is not string");
            return NULL;
        }
        return PyString_FromFormat("%s %s %s", STR(self->name),
                                               STR(self->relation),
                                               STR(self->version));
    }
    Py_INCREF(self->name);
    return self->name;
}

static int
Depends_compare(DependsObject *self, DependsObject *other)
{
    int rc = -1;
    if (PyObject_IsInstance((PyObject *)other, (PyObject *)&Depends_Type)) {
        const char *self_name, *other_name;
        if (!PyString_Check(self->name) || !PyString_Check(other->name)) {
            PyErr_SetString(PyExc_TypeError,
                            "package name is not string");
            return -1;
        }
        self_name = STR(self->name);
        other_name = STR(other->name);
        rc = strcmp(self_name, other_name);
    }
    return rc > 0 ? 1 : ( rc < 0 ? -1 : 0);
}

static PyMethodDef Depends_methods[] = {
    {"matches", (PyCFunction)Depends_matches, METH_O, NULL},
    {NULL, NULL}
};

#define OFF(x) offsetof(DependsObject, x)
static PyMemberDef Depends_members[] = {
    {"name", T_OBJECT, OFF(name), 0, 0},
    {"version", T_OBJECT, OFF(version), 0, 0},
    {"relation", T_OBJECT, OFF(relation), 0, 0},
    {"packages", T_OBJECT, OFF(packages), 0, 0},
    {"providedby", T_OBJECT, OFF(providedby), 0, 0},
    {NULL}
};
#undef OFF

statichere PyTypeObject Depends_Type = {
	PyObject_HEAD_INIT(NULL)
	0,			/*ob_size*/
	"ccache.Depends",	/*tp_name*/
	sizeof(DependsObject), /*tp_basicsize*/
	0,			/*tp_itemsize*/
	(destructor)Depends_dealloc, /*tp_dealloc*/
	0,			/*tp_print*/
	0,			/*tp_getattr*/
	0,			/*tp_setattr*/
	(cmpfunc)Depends_compare, /*tp_compare*/
	0,			/*tp_repr*/
	0,			/*tp_as_number*/
	0,			/*tp_as_sequence*/
	0,			/*tp_as_mapping*/
	0,			/*tp_hash*/
    0,                      /*tp_call*/
    (reprfunc)Depends_str, /*tp_str*/
    PyObject_GenericGetAttr,/*tp_getattro*/
    PyObject_GenericSetAttr,/*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE, /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    Depends_methods,        /*tp_methods*/
    Depends_members,        /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)Depends_init, /*tp_init*/
    PyType_GenericAlloc,    /*tp_alloc*/
    PyType_GenericNew,      /*tp_new*/
    _PyObject_Del,          /*tp_free*/
    0,                      /*tp_is_gc*/
};

static int
Loader_init(LoaderObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, ""))
        return -1;
    self->_packages = PyList_New(0);
    Py_INCREF(Py_False);
    self->_installed = Py_False;
    return 0;
}

static void
Loader_dealloc(LoaderObject *self)
{
    Py_XDECREF(self->_packages);
    Py_XDECREF(self->_installed);
    Py_XDECREF(self->_cache);
    self->ob_type->tp_free((PyObject *)self);
}

PyObject *
Loader_setCache(LoaderObject *self, PyObject *cache)
{
    Py_XDECREF(self->_cache);
    self->_cache = NULL;

    if (cache == Py_None)
        Py_RETURN_NONE;

    if (!PyObject_IsInstance(cache, (PyObject *)&Cache_Type)) {
        PyErr_SetString(PyExc_TypeError,
                        "cache is not an instance of ccache.Cache");
        return NULL;
    }

    Py_XDECREF(self->Package);
    self->Package = PyObject_GetAttrString((PyObject*)self, "Package");
    if (!self->Package ||
        !PyObject_IsSubclass(self->Package, (PyObject *)&Package_Type)) {
        PyErr_SetString(PyExc_TypeError, "bad loader.Package member");
        return NULL;
    }
    Py_INCREF(self->Package);

    Py_XDECREF(self->Provides);
    self->Provides = PyObject_GetAttrString((PyObject*)self, "Provides");
    if (!self->Provides ||
        !PyObject_IsSubclass(self->Provides, (PyObject *)&Provides_Type)) {
        PyErr_SetString(PyExc_TypeError, "bad loader.Provides member");
        return NULL;
    }
    Py_INCREF(self->Provides);
    Py_XDECREF(self->Requires);
    self->Requires = PyObject_GetAttrString((PyObject*)self, "Requires");
    if (!self->Requires ||
        !PyObject_IsSubclass(self->Requires, (PyObject *)&Depends_Type)) {
        PyErr_SetString(PyExc_TypeError, "bad loader.Requires member");
        return NULL;
    }
    Py_INCREF(self->Requires);
    Py_XDECREF(self->Obsoletes);
    self->Obsoletes = PyObject_GetAttrString((PyObject*)self, "Obsoletes");
    if (!self->Obsoletes ||
        !PyObject_IsSubclass(self->Obsoletes, (PyObject *)&Depends_Type)) {
        PyErr_SetString(PyExc_TypeError, "bad loader.Obsoletes member");
        return NULL;
    }
    Py_INCREF(self->Obsoletes);
    Py_XDECREF(self->Conflicts);
    self->Conflicts = PyObject_GetAttrString((PyObject*)self, "Conflicts");
    if (!self->Conflicts ||
        !PyObject_IsSubclass(self->Conflicts, (PyObject *)&Depends_Type)) {
        PyErr_SetString(PyExc_TypeError, "bad loader.Conflicts member");
        return NULL;
    }
    Py_INCREF(self->Conflicts);

    Py_INCREF(cache);
    self->_cache = cache;
    Py_RETURN_NONE;
}

PyObject *
Loader_setInstalled(LoaderObject *self, PyObject *flag)
{
    Py_DECREF(self->_installed);
    Py_INCREF(flag);
    self->_installed = flag;
    Py_RETURN_NONE;
}

PyObject *
Loader_getInfo(LoaderObject *self, PyObject *pkg)
{
    Py_RETURN_NONE;
}

PyObject *
Loader_reset(LoaderObject *self, PyObject *args)
{
    PyDict_Clear(self->_packages);
    Py_RETURN_NONE;
}

PyObject *
Loader_load(LoaderObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

PyObject *
Loader_unload(LoaderObject *self, PyObject *args)
{
    return Loader_reset(self, args);
}

PyObject *
Loader_loadFileProvides(LoaderObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

PyObject *
Loader_reload(LoaderObject *self, PyObject *args)
{
    PyErr_SetString(PyExc_RuntimeError, "Loader.reload not yet implemented");
    return NULL;
}

static int
mylist(PyObject *obj, PyObject **ret)
{
    if (obj == Py_None)
        *ret = NULL;
    else if (PyList_Check(obj))
        *ret = obj;
    else
        return 0;
    return 1;
}

PyObject *
Loader_newPackage(LoaderObject *self, PyObject *args)
{
    PyObject *pkgargs;
    PyObject *prvargs;
    PyObject *reqargs;
    PyObject *obsargs;
    PyObject *cnfargs;
    
    PyObject *pkg;
    PackageObject *pkgobj;

    PyObject *relpkgs;
    PyObject *lst;

    CacheObject *cache;

    if (!self->_cache) {
        PyErr_SetString(PyExc_TypeError, "cache not set");
        return NULL;
    }

    cache = (CacheObject *)self->_cache;

    if (!PyArg_ParseTuple(args, "O!O&O&O&O&", &PyTuple_Type, &pkgargs,
                          mylist, &prvargs, mylist, &reqargs,
                          mylist, &obsargs, mylist, &cnfargs))
        return NULL;

    /* pkg = self.Package(*pkgargs) */
    pkg = PyObject_CallObject(self->Package, pkgargs);
    if (!pkg) return NULL;

    pkgobj = (PackageObject *)pkg;

    /* relpkgs = [] */
    relpkgs = PyList_New(0);

    /* if prvargs: */
    if (prvargs) {
        /* for args in prvargs: */
        int i = 0;    
        int len = PyList_Size(prvargs);
        for (; i != len; i++) {
            PyObject *args = PyList_GET_ITEM(prvargs, i);
            ProvidesObject *prvobj;
            PyObject *prv;
            
            if (!PyTuple_Check(args)) {
                PyErr_SetString(PyExc_TypeError,
                                "item in prvargs is not a tuple");
                return NULL;
            }

            /* prv = cache._prvmap.get(args) */
            prv = PyDict_GetItem(cache->_prvmap, args);
            prvobj = (ProvidesObject *)prv;

            /* if not prv: */
            if (!prv) {
                /* prv = self.Provides(*args) */
                prv = PyObject_CallObject(self->Provides, args);
                if (!prv) return NULL;
                prvobj = (ProvidesObject *)prv;

                /* cache._prvmap[args] = prv */
                PyDict_SetItem(cache->_prvmap, args, prv);

                /*
                   lst = cache._prvnames.get(prv.name)
                   if lst is not None:
                       lst.append(prv)
                   else:
                       cache._prvnames[prv.name] = [prv]
                */
                lst = PyDict_GetItem(cache->_prvnames, prvobj->name);
                if (!lst) {
                    lst = PyList_New(0);
                    PyDict_SetItem(cache->_prvnames, prvobj->name, lst);
                }
                PyList_Append(lst, prv);

                /* cache._provides.append(prv) */
                PyList_Append(cache->_provides, prv);
            }

            /* relpkgs.append(prv.packages) */
            PyList_Append(relpkgs, prvobj->packages);

            /* pkg.provides.append(prv) */
            PyList_Append(pkgobj->provides, prv);
        }
    }

    /* if reqargs: */
    if (reqargs) {
        /* for args in reqargs: */
        int i = 0;    
        int len = PyList_Size(reqargs);
        for (; i != len; i++) {
            PyObject *args = PyList_GET_ITEM(reqargs, i);
            DependsObject *reqobj;
            PyObject *req;
            
            if (!PyTuple_Check(args)) {
                PyErr_SetString(PyExc_TypeError,
                                "item in reqargs is not a tuple");
                return NULL;
            }

            /* req = cache._reqmap.get(args) */
            req = PyDict_GetItem(cache->_reqmap, args);
            reqobj = (DependsObject *)req;

            /* if not req: */
            if (!req) {
                /* req = self.Requires(*args) */
                req = PyObject_CallObject(self->Requires, args);
                if (!req) return NULL;
                reqobj = (DependsObject *)req;

                /* cache._reqmap[args] = req */
                PyDict_SetItem(cache->_reqmap, args, req);

                /*
                   lst = cache._reqnames.get(req.name)
                   if lst is not None:
                       lst.append(req)
                   else:
                       cache._reqnames[req.name] = [req]
                */
                lst = PyDict_GetItem(cache->_reqnames, reqobj->name);
                if (!lst) {
                    lst = PyList_New(0);
                    PyDict_SetItem(cache->_reqnames, reqobj->name, lst);
                }
                PyList_Append(lst, req);

                /* cache._requires.append(req) */
                PyList_Append(cache->_requires, req);
            }

            /* relpkgs.append(req.packages) */
            PyList_Append(relpkgs, reqobj->packages);

            /* pkg.requires.append(req) */
            PyList_Append(pkgobj->requires, req);
        }
    }

    /* if obsargs: */
    if (obsargs) {
        /* for args in obsargs: */
        int i = 0;    
        int len = PyList_Size(obsargs);
        for (; i != len; i++) {
            PyObject *args = PyList_GET_ITEM(obsargs, i);
            DependsObject *obsobj;
            PyObject *obs;
            
            if (!PyTuple_Check(args)) {
                PyErr_SetString(PyExc_TypeError,
                                "item in obsargs is not a tuple");
                return NULL;
            }

            /* obs = cache._obsmap.get(args) */
            obs = PyDict_GetItem(cache->_obsmap, args);
            obsobj = (DependsObject *)obs;

            /* if not obs: */
            if (!obs) {
                /* obs = self.Obsoletes(*args) */
                obs = PyObject_CallObject(self->Obsoletes, args);
                if (!obs) return NULL;
                obsobj = (DependsObject *)obs;

                /* cache._obsmap[args] = obs */
                PyDict_SetItem(cache->_obsmap, args, obs);

                /*
                   lst = cache._obsnames.get(obs.name)
                   if lst is not None:
                       lst.append(obs)
                   else:
                       cache._obsnames[obs.name] = [obs]
                */
                lst = PyDict_GetItem(cache->_obsnames, obsobj->name);
                if (!lst) {
                    lst = PyList_New(0);
                    PyDict_SetItem(cache->_obsnames, obsobj->name, lst);
                }
                PyList_Append(lst, obs);

                /* cache._obsoletes.append(obs) */
                PyList_Append(cache->_obsoletes, obs);
            }

            /* relpkgs.append(obs.packages) */
            PyList_Append(relpkgs, obsobj->packages);

            /* pkg.obsoletes.append(obs) */
            PyList_Append(pkgobj->obsoletes, obs);
        }
    }

    /* if cnfargs: */
    if (cnfargs) {
        /* for args in cnfargs: */
        int i = 0;    
        int len = PyList_Size(cnfargs);
        for (; i != len; i++) {
            PyObject *args = PyList_GET_ITEM(cnfargs, i);
            DependsObject *cnfobj;
            PyObject *cnf;
            
            if (!PyTuple_Check(args)) {
                PyErr_SetString(PyExc_TypeError,
                                "item in cnfargs is not a tuple");
                return NULL;
            }

            /* cnf = cache._cnfmap.get(args) */
            cnf = PyDict_GetItem(cache->_cnfmap, args);
            cnfobj = (DependsObject *)cnf;

            /* if not cnf: */
            if (!cnf) {
                /* cnf = self.Conflicts(*args) */
                cnf = PyObject_CallObject(self->Conflicts, args);
                if (!cnf) return NULL;
                cnfobj = (DependsObject *)cnf;

                /* cache._cnfmap[args] = cnf */
                PyDict_SetItem(cache->_cnfmap, args, cnf);

                /*
                   lst = cache._cnfnames.get(cnf.name)
                   if lst is not None:
                       lst.append(cnf)
                   else:
                       cache._cnfnames[cnf.name] = [cnf]
                */
                lst = PyDict_GetItem(cache->_cnfnames, cnfobj->name);
                if (!lst) {
                    lst = PyList_New(0);
                    PyDict_SetItem(cache->_cnfnames, cnfobj->name, lst);
                }
                PyList_Append(lst, cnf);

                /* cache._conflicts.append(cnf) */
                PyList_Append(cache->_conflicts, cnf);
            }

            /* relpkgs.append(cnf.packages) */
            PyList_Append(relpkgs, cnfobj->packages);

            /* pkg.conflicts.append(cnf) */
            PyList_Append(pkgobj->conflicts, cnf);
        }
    }

    /* found = False */
    int found = 0;
    /* lst = cache._pkgmap.get(pkgargs) */
    lst = PyDict_GetItem(cache->_pkgmap, pkgargs);
    /* if lst is not None: */
    if (lst) {
        /* for lstpkg in lst: */
        int i = 0;    
        int len = PyList_Size(lst);
        for (; i != len; i++) {
            PyObject *lstpkg = PyList_GET_ITEM(lst, i);
            /* if pkg.equals(lstpkg): */
            PyObject *ret = Package_equals((PackageObject *)pkg,
                                           (PackageObject *)lstpkg);
            if (!ret) return NULL;
            if (ret == Py_True) {
                /* pkg = lstpkg */
                Py_DECREF(pkg);
                pkg = lstpkg;
                Py_INCREF(pkg);
                /* found = True */
                found = 1;
                /* break */
                break;
            }
            Py_DECREF(ret);
        }
        /* else: */
        if (!found)
            /* lst.append(pkg) */
            PyList_Append(lst, pkg);
    }
    /* else: */
    if (!found) {
        /* cache._pkgmap[pkgargs] = [pkg] */
        lst = PyList_New(1);
        Py_INCREF(pkg);
        PyList_SET_ITEM(lst, 0, pkg);
        PyDict_SetItem(cache->_pkgmap, pkgargs, lst);
        Py_DECREF(lst);
    }

    /* if not found: */
    if (!found) {
        int i, len;

        /* cache._packages.append(pkg) */
        PyList_Append(cache->_packages, pkg);

        /*
           lst = cache._pkgnames.get(pkg.name)
           if lst is not None:
               lst.append(pkg)
           else:
               cache._pkgnames[pkg.name] = [pkg]
        */
        lst = PyDict_GetItem(cache->_pkgnames, pkgobj->name);
        if (!lst) {
            lst = PyList_New(0);
            PyDict_SetItem(cache->_pkgnames, pkgobj->name, lst);
        }
        PyList_Append(lst, pkg);

        /* for pkgs in relpkgs: */
        len = PyList_GET_SIZE(relpkgs);
        for (i = 0; i != len; i++) {
            PyObject *pkgs = PyList_GET_ITEM(relpkgs, i);
            /* pkgs.append(pkg) */
            PyList_Append(pkgs, pkg);
        }
    }

    /* This will leak if it returns earlier, but any early
     * returns are serious bugs, so let's KISS here. */
    Py_DECREF(relpkgs);

    /* pkg.installed |= self._installed */
    if (self->_installed == Py_True) {
        Py_DECREF(pkgobj->installed);
        pkgobj->installed = self->_installed;
        Py_INCREF(pkgobj->installed);
    }

    /* self._packages.append(pkg) */
    PyList_Append(self->_packages, pkg);

    return pkg;
}

PyObject *
Loader_newProvides(LoaderObject *self, PyObject *_args)
{
    PackageObject *pkgobj;
    PyObject *pkg;
    PyObject *name;
    PyObject *version = Py_None;

    ProvidesObject *prvobj;
    PyObject *prv;
    PyObject *args;
    PyObject *lst;

    CacheObject *cache;

    if (!self->_cache) {
        PyErr_SetString(PyExc_TypeError, "cache not set");
        return NULL;
    }
    cache = (CacheObject *)self->_cache;

    if (!PyArg_ParseTuple(_args, "OO!|O!", &pkg,
                          &PyString_Type, &name, &PyString_Type, &version))
        return NULL;

    if (!PyObject_IsInstance(pkg, (PyObject *)&Package_Type)) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be a Package instance");
        return NULL;
    }

    pkgobj = (PackageObject *)pkg;

    /* args = (name, version) */
    args = PyTuple_New(2);
    if (!args) return NULL;
    Py_INCREF(name);
    Py_INCREF(version);
    PyTuple_SetItem(args, 0, name);
    PyTuple_SetItem(args, 1, version);
    
    /* prv = cache._prvmap.get(args) */
    prv = PyDict_GetItem(cache->_prvmap, args);
    prvobj = (ProvidesObject *)prv;

    /* if not prv: */
    if (!prv) {
        /* prv = self.Provides(*args) */
        prv = PyObject_CallObject(self->Provides, args);
        if (!prv) goto error;
        prvobj = (ProvidesObject *)prv;

        /* cache._prvmap[args] = prv */
        PyDict_SetItem(cache->_prvmap, args, prv);

        /*
           lst = cache._prvnames.get(prv.name)
           if lst is not None:
               lst.append(prv)
           else:
               cache._prvnames[prv.name] = [prv]
        */
        lst = PyDict_GetItem(cache->_prvnames, prvobj->name);
        if (!lst) {
            lst = PyList_New(0);
            PyDict_SetItem(cache->_prvnames, prvobj->name, lst);
        }
        PyList_Append(lst, prv);

        /* cache._provides[prv.name] = [prv] */
        PyList_Append(cache->_provides, prv);
    }

    /* prv.packages.append(pkg) */
    PyList_Append(prvobj->packages, pkg);

    /* pkg.provides.append(prv) */
    PyList_Append(pkgobj->provides, prv);

    Py_DECREF(args);

    Py_RETURN_NONE;

error:
    Py_DECREF(args);
    return NULL;
}

static PyMethodDef Loader_methods[] = {
    {"setCache", (PyCFunction)Loader_setCache, METH_O, NULL},
    {"setInstalled", (PyCFunction)Loader_setInstalled, METH_O, NULL},
    {"getInfo", (PyCFunction)Loader_getInfo, METH_O, NULL},
    {"reset", (PyCFunction)Loader_reset, METH_NOARGS, NULL},
    {"load", (PyCFunction)Loader_load, METH_NOARGS, NULL},
    {"unload", (PyCFunction)Loader_unload, METH_NOARGS, NULL},
    {"loadFileProvides", (PyCFunction)Loader_loadFileProvides, METH_O, NULL},
    {"reload", (PyCFunction)Loader_reload, METH_NOARGS, NULL},
    {"newPackage", (PyCFunction)Loader_newPackage, METH_VARARGS, NULL},
    {"newProvides", (PyCFunction)Loader_newProvides, METH_VARARGS, NULL},
    {NULL, NULL}
};

#define OFF(x) offsetof(LoaderObject, x)
static PyMemberDef Loader_members[] = {
    {"_cache", T_OBJECT, OFF(_cache), RO, "Cache object"},
    {"_packages", T_OBJECT, OFF(_packages), RO, "Package list"},
    {"_installed", T_OBJECT, OFF(_installed), RO, "Installed flag"},
    {"Package", T_OBJECT, OFF(Package), 0, "Package class"},
    {"Provides", T_OBJECT, OFF(Provides), 0, "Provides class"},
    {"Requires", T_OBJECT, OFF(Requires), 0, "Requires class"},
    {"Obsoletes", T_OBJECT, OFF(Obsoletes), 0, "Obsoletes class"},
    {"Conflicts", T_OBJECT, OFF(Conflicts), 0, "Conflicts class"},
    {NULL}
};
#undef OFF

statichere PyTypeObject Loader_Type = {
	PyObject_HEAD_INIT(NULL)
	0,			/*ob_size*/
	"ccache.Loader",	/*tp_name*/
	sizeof(LoaderObject), /*tp_basicsize*/
	0,			/*tp_itemsize*/
	(destructor)Loader_dealloc, /*tp_dealloc*/
	0,			/*tp_print*/
	0,			/*tp_getattr*/
	0,			/*tp_setattr*/
	0,			/*tp_compare*/
	0,			/*tp_repr*/
	0,			/*tp_as_number*/
	0,			/*tp_as_sequence*/
	0,			/*tp_as_mapping*/
	0,			/*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    PyObject_GenericGetAttr,/*tp_getattro*/
    PyObject_GenericSetAttr,/*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE, /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    Loader_methods,         /*tp_methods*/
    Loader_members,         /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)Loader_init,  /*tp_init*/
    PyType_GenericAlloc,    /*tp_alloc*/
    PyType_GenericNew,      /*tp_new*/
    _PyObject_Del,          /*tp_free*/
    0,                      /*tp_is_gc*/
};

static int
Cache_init(CacheObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, ""))
        return -1;
    self->_loaders = PyList_New(0);
    self->_packages = PyList_New(0);
    self->_provides = PyList_New(0);
    self->_requires = PyList_New(0);
    self->_obsoletes = PyList_New(0);
    self->_conflicts = PyList_New(0);
    self->_pkgnames = PyDict_New();
    self->_prvnames = PyDict_New();
    self->_reqnames = PyDict_New();
    self->_obsnames = PyDict_New();
    self->_cnfnames = PyDict_New();
    self->_pkgmap = PyDict_New();
    self->_prvmap = PyDict_New();
    self->_reqmap = PyDict_New();
    self->_obsmap = PyDict_New();
    self->_cnfmap = PyDict_New();
    return 0;
}

static void
Cache_dealloc(CacheObject *self)
{
    Py_XDECREF(self->_loaders);
    Py_XDECREF(self->_packages);
    Py_XDECREF(self->_provides);
    Py_XDECREF(self->_requires);
    Py_XDECREF(self->_obsoletes);
    Py_XDECREF(self->_conflicts);
    Py_XDECREF(self->_pkgnames);
    Py_XDECREF(self->_prvnames);
    Py_XDECREF(self->_reqnames);
    Py_XDECREF(self->_obsnames);
    Py_XDECREF(self->_cnfnames);
    Py_XDECREF(self->_pkgmap);
    Py_XDECREF(self->_prvmap);
    Py_XDECREF(self->_reqmap);
    Py_XDECREF(self->_obsmap);
    Py_XDECREF(self->_cnfmap);
    self->ob_type->tp_free((PyObject *)self);
}

#define RESET_LIST(x) \
    PyList_SetSlice((x), 0, PyList_GET_SIZE(x), (PyObject *)NULL);
PyObject *
Cache_reset(CacheObject *self, PyObject *args)
{
    PyObject *deps = NULL;
    if (!PyArg_ParseTuple(args, "|O", &deps))
        return NULL;
    if (deps && PyObject_IsTrue(deps)) {
        int i, len;
        len = PyList_GET_SIZE(self->_provides);
        for (i = 0; i != len; i++) {
            ProvidesObject *prvobj;
            PyObject *prv;
            prv = PyList_GET_ITEM(self->_provides, i);
            prvobj = (ProvidesObject *)prv;
            RESET_LIST(prvobj->packages);
            RESET_LIST(prvobj->requiredby);
            RESET_LIST(prvobj->obsoletedby);
            RESET_LIST(prvobj->conflictedby);
        }
        len = PyList_GET_SIZE(self->_requires);
        for (i = 0; i != len; i++) {
            DependsObject *reqobj;
            PyObject *req;
            req = PyList_GET_ITEM(self->_requires, i);
            reqobj = (DependsObject *)req;
            RESET_LIST(reqobj->packages);
            RESET_LIST(reqobj->providedby);
        }
        len = PyList_GET_SIZE(self->_obsoletes);
        for (i = 0; i != len; i++) {
            DependsObject *obsobj;
            PyObject *obs;
            obs = PyList_GET_ITEM(self->_obsoletes, i);
            obsobj = (DependsObject *)obs;
            RESET_LIST(obsobj->packages);
            RESET_LIST(obsobj->providedby);
        }
        len = PyList_GET_SIZE(self->_conflicts);
        for (i = 0; i != len; i++) {
            DependsObject *cnfobj;
            PyObject *cnf;
            cnf = PyList_GET_ITEM(self->_conflicts, i);
            cnfobj = (DependsObject *)cnf;
            RESET_LIST(cnfobj->packages);
            RESET_LIST(cnfobj->providedby);
        }
    }
    RESET_LIST(self->_packages);
    RESET_LIST(self->_provides);
    RESET_LIST(self->_requires);
    RESET_LIST(self->_obsoletes);
    RESET_LIST(self->_conflicts);
    PyDict_Clear(self->_pkgnames);
    PyDict_Clear(self->_prvnames);
    PyDict_Clear(self->_reqnames);
    PyDict_Clear(self->_obsnames);
    PyDict_Clear(self->_cnfnames);
    PyDict_Clear(self->_prvmap);
    PyDict_Clear(self->_reqmap);
    PyDict_Clear(self->_obsmap);
    PyDict_Clear(self->_cnfmap);
    Py_RETURN_NONE;
}
#undef RESET_LIST

PyObject *
Cache_addLoader(CacheObject *self, PyObject *loader)
{
    if (loader != Py_None) {
        PyList_Append(self->_loaders, loader);
        CALLMETHOD(loader, "setCache", "O", self);
    }
    Py_RETURN_NONE;
}

PyObject *
Cache_removeLoader(CacheObject *self, PyObject *loader)
{
    if (loader != Py_None) {
        int i, len;
        len = PyList_GET_SIZE(self->_loaders);
        for (i = len-1; i >= 0; i--)
            if (PyList_GET_ITEM(self->_loaders, i) == loader)
                PyList_SetSlice(self->_loaders, i, i+1, (PyObject *)NULL);
        CALLMETHOD(loader, "setCache", "O", Py_None);
    }
    Py_RETURN_NONE;
}

PyObject *
Cache_load(CacheObject *self, PyObject *args)
{
    int i, len;
    CALLMETHOD(self, "reset", NULL);
    len = PyList_GET_SIZE(self->_loaders);
    for (i = 0; i != len; i++) {
        PyObject *loader = PyList_GET_ITEM(self->_loaders, i);
        CALLMETHOD(loader, "reset", NULL);
        CALLMETHOD(loader, "load", NULL);
    }
    CALLMETHOD(self, "loadFileProvides", NULL);
    CALLMETHOD(self, "linkDeps", NULL);
    Py_RETURN_NONE;
}

PyObject *
Cache_unload(CacheObject *self, PyObject *args)
{
    int i, len;
    CALLMETHOD(self, "reset", NULL);
    len = PyList_GET_SIZE(self->_loaders);
    for (i = 0; i != len; i++) {
        PyObject *loader = PyList_GET_ITEM(self->_loaders, i);
        CALLMETHOD(loader, "unload", NULL);
    }
    Py_RETURN_NONE;
}

PyObject *
Cache_reload(CacheObject *self, PyObject *args)
{
    int i, len;
    CALLMETHOD(self, "reset", "O", Py_True);
    len = PyList_GET_SIZE(self->_loaders);
    for (i = 0; i != len; i++) {
        PyObject *loader = PyList_GET_ITEM(self->_loaders, i);
        CALLMETHOD(loader, "reload", NULL);
    }
    CALLMETHOD(self, "loadFileProvides", NULL);
    CALLMETHOD(self, "linkDeps", NULL);
    Py_RETURN_NONE;
}

PyObject *
Cache_loadFileProvides(CacheObject *self, PyObject *args)
{
    PyObject *fndict = PyDict_New();
    int i, len;
    len = PyList_GET_SIZE(self->_requires);
    for (i = 0; i != len; i++) {
        DependsObject *req =
            (DependsObject *)PyList_GET_ITEM(self->_requires, i);
        if (STR(req->name)[0] == '/') {
            Py_INCREF(req->name);
            Py_INCREF(Py_True);
            PyDict_SetItem(fndict, req->name, Py_True);
        }
    }
    len = PyList_GET_SIZE(self->_loaders);
    for (i = 0; i != len; i++) {
        PyObject *loader = PyList_GET_ITEM(self->_loaders, i);
        CALLMETHOD(loader, "loadFileProvides", "O", fndict);
    }
    Py_RETURN_NONE;
}

PyObject *
Cache_linkDeps(CacheObject *self, PyObject *args)
{
    int i, j, len;
    /* for prv in self._provides: */
    len = PyList_GET_SIZE(self->_provides);
    for (i = 0; i != len; i++) {
        ProvidesObject *prv;
        PyObject *lst;

        prv = (ProvidesObject *)PyList_GET_ITEM(self->_provides, i);

        /* lst = self._reqnames.get(prv.name) */
        lst = PyDict_GetItem(self->_reqnames, prv->name);

        /* if lst: */
        if (lst) {
            /* for req in lst: */
            int reqlen = PyList_GET_SIZE(lst);
            for (j = 0; j != reqlen; j++) {
                DependsObject *req = (DependsObject *)PyList_GET_ITEM(lst, j);
                /* if .......: */
                if (req->relation == Py_None ||
                    (PyString_Check(prv->version) &&
                     strcmp(STR(req->relation), "=") == 0 &&
                     strcmp(STR(req->version), STR(prv->version)) == 0)) {
                    /* req.providedby.append(prv) */
                    PyList_Append(req->providedby, (PyObject *)prv);
                    /* prv.requiredby.append(req) */
                    PyList_Append(prv->requiredby, (PyObject *)req);
                } else {
                    PyObject *ret = 
                        PyObject_CallMethod((PyObject *)req, "matches",
                                            "O", (PyObject *)prv);
                    if (!ret) return NULL;
                    if (PyObject_IsTrue(ret)) {
                        /* req.providedby.append(prv) */
                        PyList_Append(req->providedby, (PyObject *)prv);
                        /* prv.requiredby.append(req) */
                        PyList_Append(prv->requiredby, (PyObject *)req);
                    }
                    Py_DECREF(ret);
                }
            }
        }

        /* lst = self._obsnames.get(prv.name) */
        lst = PyDict_GetItem(self->_obsnames, prv->name);

        /* if lst: */
        if (lst) {

            /* for obs in lst: */
            int obslen = PyList_GET_SIZE(lst);
            for (j = 0; j != obslen; j++) {
                DependsObject *obs = (DependsObject *)PyList_GET_ITEM(lst, j);
                /* if .......: */
                if (obs->relation == Py_None ||
                    (PyString_Check(prv->version) &&
                     strcmp(STR(obs->relation), "=") == 0 &&
                     strcmp(STR(obs->version), STR(prv->version)) == 0)) {
                    /* obs.providedby.append(prv) */
                    PyList_Append(obs->providedby, (PyObject *)prv);
                    /* prv.obsoletedby.append(obs) */
                    PyList_Append(prv->obsoletedby, (PyObject *)obs);
                } else {
                    PyObject *ret = 
                        PyObject_CallMethod((PyObject *)obs, "matches",
                                            "O", (PyObject *)prv);
                    if (!ret) return NULL;
                    if (PyObject_IsTrue(ret)) {
                        /* obs.providedby.append(prv) */
                        PyList_Append(obs->providedby, (PyObject *)prv);
                        /* prv.obsoletedby.append(obs) */
                        PyList_Append(prv->obsoletedby, (PyObject *)obs);
                    }
                    Py_DECREF(ret);
                }
            }
        }

        /* lst = self._cnfnames.get(prv.name) */
        lst = PyDict_GetItem(self->_cnfnames, prv->name);

        /* if lst: */
        if (lst) {

            /* for cnf in lst: */
            int cnflen = PyList_GET_SIZE(lst);
            for (j = 0; j != cnflen; j++) {
                DependsObject *cnf = (DependsObject *)PyList_GET_ITEM(lst, j);
                /* if .......: */
                if (cnf->relation == Py_None ||
                    (PyString_Check(prv->version) &&
                     strcmp(STR(cnf->relation), "=") == 0 &&
                     strcmp(STR(cnf->version), STR(prv->version)) == 0)) {
                    /* cnf.providedby.append(prv) */
                    PyList_Append(cnf->providedby, (PyObject *)prv);
                    /* prv.conflictedby.append(cnf) */
                    PyList_Append(prv->conflictedby, (PyObject *)cnf);
                } else {
                    PyObject *ret = 
                        PyObject_CallMethod((PyObject *)cnf, "matches",
                                            "O", (PyObject *)prv);
                    if (!ret) return NULL;
                    if (PyObject_IsTrue(ret)) {
                        /* cnf.providedby.append(prv) */
                        PyList_Append(cnf->providedby, (PyObject *)prv);
                        /* prv.conflictedby.append(cnf) */
                        PyList_Append(prv->conflictedby, (PyObject *)cnf);
                    }
                    Py_DECREF(ret);
                }
            }
        }
    }

    Py_RETURN_NONE;
}

PyObject *
Cache_getPackages(CacheObject *self, PyObject *args)
{
    PyObject *name = NULL;
    PyObject *lst;
    if (!PyArg_ParseTuple(args, "|O!", &PyString_Type, &name))
        return NULL;
    if (!name) {
        Py_INCREF(self->_packages);
        return self->_packages;
    }
    lst = PyDict_GetItem(self->_pkgnames, name);
    if (!lst)
        lst = PyList_New(0);
    else
        Py_INCREF(lst);
    return lst;
}

PyObject *
Cache_getProvides(CacheObject *self, PyObject *args)
{
    PyObject *name = NULL;
    PyObject *lst;
    if (!PyArg_ParseTuple(args, "|O!", &PyString_Type, &name))
        return NULL;
    if (!name) {
        Py_INCREF(self->_provides);
        return self->_provides;
    }
    lst = PyDict_GetItem(self->_prvnames, name);
    if (!lst)
        lst = PyList_New(0);
    else
        Py_INCREF(lst);
    return lst;
}

PyObject *
Cache_getRequires(CacheObject *self, PyObject *args)
{
    PyObject *name = NULL;
    PyObject *lst;
    if (!PyArg_ParseTuple(args, "|O!", &PyString_Type, &name))
        return NULL;
    if (!name) {
        Py_INCREF(self->_requires);
        return self->_requires;
    }
    lst = PyDict_GetItem(self->_reqnames, name);
    if (!lst)
        lst = PyList_New(0);
    else
        Py_INCREF(lst);
    return lst;
}

PyObject *
Cache_getObsoletes(CacheObject *self, PyObject *args)
{
    PyObject *name = NULL;
    PyObject *lst;
    if (!PyArg_ParseTuple(args, "|O!", &PyString_Type, &name))
        return NULL;
    if (!name) {
        Py_INCREF(self->_obsoletes);
        return self->_obsoletes;
    }
    lst = PyDict_GetItem(self->_obsnames, name);
    if (!lst)
        lst = PyList_New(0);
    else
        Py_INCREF(lst);
    return lst;
}

PyObject *
Cache_getConflicts(CacheObject *self, PyObject *args)
{
    PyObject *name = NULL;
    PyObject *lst;
    if (!PyArg_ParseTuple(args, "|O!", &PyString_Type, &name))
        return NULL;
    if (!name) {
        Py_INCREF(self->_conflicts);
        return self->_conflicts;
    }
    lst = PyDict_GetItem(self->_cnfnames, name);
    if (!lst)
        lst = PyList_New(0);
    else
        Py_INCREF(lst);
    return lst;
}

static PyMethodDef Cache_methods[] = {
    {"reset", (PyCFunction)Cache_reset, METH_VARARGS, NULL},
    {"addLoader", (PyCFunction)Cache_addLoader, METH_O, NULL},
    {"removeLoader", (PyCFunction)Cache_removeLoader, METH_O, NULL},
    {"load", (PyCFunction)Cache_load, METH_NOARGS, NULL},
    {"unload", (PyCFunction)Cache_unload, METH_NOARGS, NULL},
    {"reload", (PyCFunction)Cache_reload, METH_NOARGS, NULL},
    {"loadFileProvides", (PyCFunction)Cache_loadFileProvides, METH_NOARGS, NULL},
    {"linkDeps", (PyCFunction)Cache_linkDeps, METH_VARARGS, NULL},
    {"getPackages", (PyCFunction)Cache_getPackages, METH_VARARGS, NULL},
    {"getProvides", (PyCFunction)Cache_getProvides, METH_VARARGS, NULL},
    {"getRequires", (PyCFunction)Cache_getRequires, METH_VARARGS, NULL},
    {"getObsoletes", (PyCFunction)Cache_getObsoletes, METH_VARARGS, NULL},
    {"getConflicts", (PyCFunction)Cache_getConflicts, METH_VARARGS, NULL},
    {NULL, NULL}
};

#define OFF(x) offsetof(CacheObject, x)
static PyMemberDef Cache_members[] = {
    {"_loaders", T_OBJECT, OFF(_loaders), RO, 0},
    {"_packages", T_OBJECT, OFF(_packages), RO, 0},
    {"_provides", T_OBJECT, OFF(_provides), RO, 0},
    {"_requires", T_OBJECT, OFF(_requires), RO, 0},
    {"_obsoletes", T_OBJECT, OFF(_obsoletes), RO, 0},
    {"_conflicts", T_OBJECT, OFF(_conflicts), RO, 0},
    {"_pkgnames", T_OBJECT, OFF(_pkgnames), RO, 0},
    {"_prvnames", T_OBJECT, OFF(_prvnames), RO, 0},
    {"_reqnames", T_OBJECT, OFF(_reqnames), RO, 0},
    {"_obsnames", T_OBJECT, OFF(_obsnames), RO, 0},
    {"_cnfnames", T_OBJECT, OFF(_cnfnames), RO, 0},
    {"_prvmap", T_OBJECT, OFF(_prvmap), RO, 0},
    {"_reqmap", T_OBJECT, OFF(_reqmap), RO, 0},
    {"_obsmap", T_OBJECT, OFF(_obsmap), RO, 0},
    {"_cnfmap", T_OBJECT, OFF(_cnfmap), RO, 0},
    {NULL}
};
#undef OFF

statichere PyTypeObject Cache_Type = {
	PyObject_HEAD_INIT(NULL)
	0,			/*ob_size*/
	"ccache.Cache",	/*tp_name*/
	sizeof(CacheObject), /*tp_basicsize*/
	0,			/*tp_itemsize*/
	(destructor)Cache_dealloc, /*tp_dealloc*/
	0,			/*tp_print*/
	0,			/*tp_getattr*/
	0,			/*tp_setattr*/
	0,			/*tp_compare*/
	0,			/*tp_repr*/
	0,			/*tp_as_number*/
	0,			/*tp_as_sequence*/
	0,			/*tp_as_mapping*/
	0,			/*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    PyObject_GenericGetAttr,/*tp_getattro*/
    PyObject_GenericSetAttr,/*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE, /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    Cache_methods,         /*tp_methods*/
    Cache_members,         /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)Cache_init,  /*tp_init*/
    PyType_GenericAlloc,    /*tp_alloc*/
    PyType_GenericNew,      /*tp_new*/
    _PyObject_Del,          /*tp_free*/
    0,                      /*tp_is_gc*/
};


static PyMethodDef ccache_methods[] = {
    {NULL, NULL}
};

DL_EXPORT(void)
initccache(void)
{
    PyObject *m;
    Package_Type.ob_type = &PyType_Type;
    Provides_Type.ob_type = &PyType_Type;
    Depends_Type.ob_type = &PyType_Type;
    Loader_Type.ob_type = &PyType_Type;
    Cache_Type.ob_type = &PyType_Type;
    m = Py_InitModule3("ccache", ccache_methods, "");
    Py_INCREF(&Package_Type);
    PyModule_AddObject(m, "Package", (PyObject*)&Package_Type);
    Py_INCREF(&Provides_Type);
    PyModule_AddObject(m, "Provides", (PyObject*)&Provides_Type);
    Py_INCREF(&Depends_Type);
    PyModule_AddObject(m, "Depends", (PyObject*)&Depends_Type);
    Py_INCREF(&Loader_Type);
    PyModule_AddObject(m, "Loader", (PyObject*)&Loader_Type);
    Py_INCREF(&Cache_Type);
    PyModule_AddObject(m, "Cache", (PyObject*)&Cache_Type);
}

/* vim:ts=4:sw=4:et
*/
