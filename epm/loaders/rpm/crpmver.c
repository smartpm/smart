
#include <Python.h>
#include <structmember.h>

#include <assert.h>
#include <string.h>
#include <stdlib.h>

void
parseversion(char *buf, char **e, char **v, char **r)
{
    char *s = strrchr(buf, '-');
    if (s) {
        *s++ = '\0';
        *r = s;
    } else {
        *r = NULL;
    }
    s = buf;
    while (isdigit(*s)) s++;
    if (*s == ':') {
        *e = buf;
        *s++ = '\0';
        *v = s;
        if (**e == '\0') *e = "0";
    } else {
        *e = "0";
        *v = buf;
    }
}

int
vercmp(const char *s1, const char *s2)
{
    char *e1, *v1, *r1, *e2, *v2, *r2;
    char b1[64];
    char b2[64];
    int rc;
    strncpy(b1, s1, sizeof(b1)-1);
    strncpy(b2, s2, sizeof(b2)-1);
    b1[sizeof(b1)-1] = '\0';
    b2[sizeof(b1)-1] = '\0';
    parseversion(b1, &e1, &v1, &r1);
    parseversion(b2, &e2, &v2, &r2);
    return vercmpparts(e1, v1, r1, e2, v2, r2);
}

int
vercmpparts(const char *e1, const char *v1, const char *r1,
            const char *e2, const char *v2, const char *r2)
{
    int rc;
    if (e1 && !e2) return 1;
    if (!e1 && e2) return -1;
    if (e1 && e2) {
        int e1i = atoi(e1);
        int e2i = atoi(e2);
        if (e1i < e2i) return -1;
        if (e1i > e2i) return 1;
    }
    rc = vercmppart(v1, v2);
    if (rc)
        return rc;
    else if (!r1 || !r2)
        return 0;
    return vercmppart(r1, r2);
}

/* Ripped from rpm. */
int
vercmppart(const char *a, const char *b)
{
    char oldch1, oldch2;
    char *str1, *str2;
    char *one, *two;
    int rc;
    int isnum;

    if (!strcmp(a, b)) return 0;

    str1 = alloca(strlen(a) + 1);
    str2 = alloca(strlen(b) + 1);

    strcpy(str1, a);
    strcpy(str2, b);

    one = str1;
    two = str2;

    while (*one && *two) {
        while (*one && !isalnum(*one)) one++;
        while (*two && !isalnum(*two)) two++;

        str1 = one;
        str2 = two;

        if (isdigit(*str1)) {
            while (*str1 && isdigit(*str1)) str1++;
            while (*str2 && isdigit(*str2)) str2++;
            isnum = 1;
        } else {
            while (*str1 && isalpha(*str1)) str1++;
            while (*str2 && isalpha(*str2)) str2++;
            isnum = 0;
        }

        oldch1 = *str1;
        *str1 = '\0';
        oldch2 = *str2;
        *str2 = '\0';

        if (one == str1) return -1;
        if (two == str2) return (isnum ? 1 : -1);

        if (isnum) {
            while (*one == '0') one++;
            while (*two == '0') two++;

            if (strlen(one) > strlen(two)) return 1;
            if (strlen(two) > strlen(one)) return -1;
        }

        rc = strcmp(one, two);
        if (rc) return (rc < 1 ? -1 : 1);

        *str1 = oldch1;
        one = str1;
        *str2 = oldch2;
        two = str2;
    }

    if ((!*one) && (!*two)) return 0;

    if (!*one) return -1; else return 1;
}

PyObject *
crpmver_checkdep(PyObject *self, PyObject *args)
{
    const char *v1, *rel, *v2;
    PyObject *ret;
    int rc;
    if (!PyArg_ParseTuple(args, "sss", &v1, &rel, &v2))
        return NULL;
    rc = vercmp(v1, v2);
    if (rc == 0)
        ret = (strchr(rel, '=') != NULL) ? Py_True : Py_False;
    else if (rc < 0)
        ret = (rel[0] == '<') ? Py_True : Py_False;
    else
        ret = (rel[0] == '>') ? Py_True : Py_False;
    Py_INCREF(ret);
    return ret;
}

PyObject *
crpmver_vercmp(PyObject *self, PyObject *args)
{
    const char *v1, *v2;
    if (!PyArg_ParseTuple(args, "ss", &v1, &v2))
        return NULL;
    return PyInt_FromLong(vercmp(v1, v2));
}

PyObject *
crpmver_vercmpparts(PyObject *self, PyObject *args)
{
    const char *e1, *v1, *r1, *e2, *v2, *r2;
    if (!PyArg_ParseTuple(args, "ssssss", &e1, &v1, &r1, &e2, &v2, &r2))
        return NULL;
    return PyInt_FromLong(vercmpparts(e1, v1, r1, e2, v2, r2));
}

PyObject *
crpmver_vercmppart(PyObject *self, PyObject *args)
{
    const char *a, *b;
    if (!PyArg_ParseTuple(args, "ss", &a, &b))
        return NULL;
    return PyInt_FromLong(vercmppart(a, b));
}

static PyMethodDef crpmver_methods[] = {
    {"checkdep", (PyCFunction)crpmver_checkdep, METH_VARARGS, NULL},
    {"vercmp", (PyCFunction)crpmver_vercmp, METH_VARARGS, NULL},
    {"vercmpparts", (PyCFunction)crpmver_vercmpparts, METH_VARARGS, NULL},
    {"vercmppart", (PyCFunction)crpmver_vercmppart, METH_VARARGS, NULL},
    {NULL, NULL}
};

DL_EXPORT(void)
initcrpmver(void)
{
    PyObject *m;
    m = Py_InitModule3("crpmver", crpmver_methods, "");
}

/* vim:ts=4:sw=4:et
*/
