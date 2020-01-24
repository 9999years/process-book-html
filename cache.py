import os
from os import path
import hashlib

CACHE_DIR = '.cache'


def init_cache():
    if not path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)


def stable_hash(key):
    if isinstance(key, str):
        key = key.encode('utf-8')
    return hashlib.sha512(key).hexdigest()


def fname(key):
    return path.join(CACHE_DIR, stable_hash(key))


def in_cache(key):
    return path.exists(fname(key))


def write(key, data):
    with open(fname(key), 'w') as f:
        f.write(data)

def read(key):
    if in_cache(key):
        with open(fname(key)) as f:
            return f.read()
    return None

def ensure(key, compute_data):
    ret = read(key)
    if ret is None:
        ret = compute_data(key)
        write(key, ret)
    return ret
