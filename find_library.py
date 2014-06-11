#
# This is a cross-platform shared library search mechanism. Tested on:
# OSX, Ubuntu, Fedora, and Windows XP+
#
import os
import glob
import platform
import re
import commands

def form_possible_names(lib, exts):
    ret = []
    for ext in exts:
        ret.append('%s*%s' % (lib, ext))
    for ext in exts:
        ret.append('lib%s*%s' % (lib, ext))
    return ret

def do_search(paths, names=[], test_fn=None):
    for pn in paths:
        globbed = []
        for name in names:
            if '*' in name:
                globbed.extend(glob.glob(os.path.join(pn, name)))
            else:
                globbed.append(os.path.join(pn, name))
        for filepath in globbed:
            if test_fn:
                if test_fn(filepath):
                    return filepath
            elif os.path.exists(filepath):
                return filepath

def is_library(filepath, acceptable_exts):
    # TODO - This is broken for ".dll.a"
    return os.path.isfile(filepath) and (os.path.splitext(filepath)[-1] in acceptable_exts)

def is_header(filepath):
    return os.path.isfile(filepath)

def include_dirs():
    # TODO - Windows?
    dirs = [
        os.path.abspath(os.curdir),
        "/usr/local/include",
        "/opt/include",
        "/usr/include",
    ]
    return [path for path in dirs if os.path.isdir(path)]

def library_dirs():
    dirs = [os.path.abspath(os.curdir)]
    if platform.system() == 'Windows':
        dirs.extend([
            os.path.dirname(__file__),
            os.path.abspath(os.curdir),
            os.path.join(os.environ.get('SystemRoot'), 'system'),
            os.path.join(os.environ.get('SystemRoot'), 'system32'),
            os.environ.get('SystemRoot'),
        ])
        dirs.extend(list(set(os.environ.get('PATH').split(os.path.pathsep))))
        dirs = [os.path.abspath(path) for path in dirs]
    else:
        dirs.extend([
            '/usr/local/lib64',
            '/usr/local/lib',
            '/usr/local/libdata',
            '/opt/local/lib',
            '/usr/lib/x86_64-linux-gnu',
            '/usr/lib64',
            '/usr/lib',
            '/usr/X11/lib',
            '/usr/share',
        ])
    dirs = list(set(dirs))
    try:
        while True:
            dirs.remove(None)
    except ValueError:
        pass
    return [path for path in dirs if os.path.isdir(path)]

def get_library_path(lib):
    paths = library_dirs()
    acceptable_exts = [
        '',
        '.so'
    ]

    if platform.system() == 'Windows':
        acceptable_exts = [
            '',
            '.dll',
            '.dll.a'
        ]
    elif platform.system() == 'Darwin':
        acceptable_exts.append('.dylib')

    names = form_possible_names(lib, acceptable_exts)

    return do_search(paths, names, lambda filepath: is_library(filepath, acceptable_exts))

def get_library_linker_name(lib):
    lib_path = get_library_path('hunspell')
    if lib_path:
        return re.sub(r'^lib|.dylib$|.so$|.dll$|.dll.a$|.a$', '', lib_path.split(os.path.sep)[-1])

def pkgconfig(*packages, **kw):
    try:
        flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
        status, response = commands.getstatusoutput("pkg-config --libs --cflags %s" % ' '.join(packages))
        if status != 0:
            raise Exception(response)
        for token in response.split():
            kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
            if token[:2] in flag_map:
                arg = flag_map.get(token[:2])
                kw.setdefault(arg, []).append(token[2:])
                kw[arg] = list(set(kw[arg]))
            else: # throw others to extra_link_args
                kw.setdefault('extra_link_args', []).append(token)
                kw['extra_link_args'] = list(set(kw['extra_link_args']))
    except:
        kw['include_dirs'] = include_dirs()
        kw['library_dirs'] = library_dirs()
        libraries = [get_library_linker_name(pkg) for pkg in packages]
        try:
            while True:
                libraries.remove(None)
        except ValueError:
            pass

        kw['libraries'] = libraries

    return kw
