""" Benchmark different hashlib hash functions using timeit """

import timeit
try:
    import hashlib

    digest = {
        "MD5": hashlib.md5,
        "SHA": hashlib.sha1,
        "SHA224": hashlib.sha224,
        "SHA256": hashlib.sha256,
        "SHA384": hashlib.sha384,
        "SHA512": hashlib.sha512
    }
except ImportError:
    from md5 import md5
    from sha import sha as sha1
    from smart.util.sha256 import sha256
    
    digest = {
        "MD5": md5,
        "SHA": sha1,
        "SHA256": sha256,
    }


def hash(type, str):
    return digest[type](str).hexdigest()

checksum = {
    "MD5": '9dd4e461268c8034f5c8564e155c67a6',
    "SHA": '11f6ad8ec52a2984abaafd7c3b516503785c2072',
    "SHA256": '2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881',
}

block = None
repetitions = 100000
for type in ["MD5", "SHA", "SHA256"]:
    for size in [16, 64, 256, 1024, 8192]:
        block = 'x' * size
        assert(hash(type, 'x') == checksum[type])
        timer = timeit.Timer('hash("%s", block)' % type,
                             'from __main__ import block, hash')
        seconds = timer.timeit(repetitions)
        speed = (size * repetitions) / (seconds * 1000.0)
        print("%s\t%d\t%fs\t%fk" % (type, size, seconds, speed))
