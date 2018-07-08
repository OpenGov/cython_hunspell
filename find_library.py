#
# This is a cross-platform shared library search mechanism. Tested on:
# OSX, Ubuntu, Fedora, and Windows XP+
#
import os
import glob
import platform
import re
import sys
import shutil
from subprocess import check_call
from tar_download import download_and_extract
from distutils.sysconfig import get_python_lib
try:
    from subprocess import getstatusoutput
except ImportError:
    from commands import getstatusoutput

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_architecture():
    return 'x64' if sys.maxsize > 2**32 else 'x86'

def get_prefered_msvc():
    if sys.version_info[0] > 3 or sys.version_info[0] < 2:
        raise RuntimeError('Unknown python version')
    # Python 2.6-3.2
    if sys.version_info[0] < 3 or sys.version_info[1] < 3:
        # We should return this, but the 11 build works and we provide it
        #return 'msvc9'
        return 'msvc11'
    # Python 3.3-3.4
    elif sys.version_info[1] < 5:
        # We should return this, but the 11 build works and we provide it
        #return 'msvc10'
        return 'msvc11'
    # Python 3.5+
    else:
        # These versions need msvc14+ compilations
        return 'msvc14'

def form_possible_names(lib, exts, extact=False):
    ret = []
    for ext in exts:
        if not extact:
            ret.append('{}*{}'.format(lib, ext))
        else:
            ret.append('{}{}'.format(lib, ext))
    for ext in exts:
        if not extact:
            ret.append('lib{}*{}'.format(lib, ext))
        else:
            ret.append('lib{}{}'.format(lib, ext))
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
                    return filepath, pn
            elif os.path.exists(filepath):
                return filepath, pn
    return None, None

def is_library(filepath, acceptable_exts):
    # TODO - This is broken for ".dll.a"
    return os.path.isfile(filepath) and (os.path.splitext(filepath)[-1] in acceptable_exts)

def is_header(filepath):
    return os.path.isfile(filepath)

def include_dirs(*packages):
    dirs = []
    if 'hunspell' in packages:
        if platform.system() == 'Linux':
            dirs = [
                os.path.abspath(os.path.join(BASE_DIR, 'hunspell')),
                # Download path if missing
                os.path.abspath(os.path.join(BASE_DIR, 'external', 'hunspell-1.6.2', 'src')),
            ]
        else:
            dirs = [
                os.path.abspath(os.path.join(BASE_DIR, 'hunspell')),
                # Download path if missing
                os.path.abspath(os.path.join(BASE_DIR, 'external', 'hunspell-1.3.3', 'src')),
            ]
    if platform.system() != 'Windows':
        dirs.extend([
            '/usr/local/include',
            '/opt/include',
            '/usr/include'
        ])
    return [path for path in dirs if os.path.isdir(path)]

def library_dirs(check_local=False):
    dirs = [os.path.abspath(BASE_DIR)]
    if platform.system() == 'Windows':
        dirs.extend([
            os.path.dirname(__file__),
            os.path.abspath(BASE_DIR),
            os.path.join(os.environ.get('SystemRoot'), 'system'),
            os.path.join(os.environ.get('SystemRoot'), 'system32'),
            os.environ.get('SystemRoot')
        ])
        if check_local:
            dirs.append(os.path.join(os.path.dirname(__file__), 'libs', 'msvc'))
        dirs.extend(list(set(os.environ.get('PATH').split(os.path.pathsep))))
        dirs = [os.path.abspath(path) for path in dirs]
    else:
        dirs.extend([
            os.path.abspath(os.path.join(get_python_lib(), 'libs', 'unix')),
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

def get_library_path(lib, check_local=False):
    paths = library_dirs(check_local)
    acceptable_exts = [
        '',
        '.so'
    ]

    if platform.system() == 'Windows':
        acceptable_exts = [
            '.lib'
        ]
    elif platform.system() == 'Darwin':
        acceptable_exts.append('.dylib')

    names = form_possible_names(lib, acceptable_exts, check_local)
    found_lib, found_path = do_search(paths, names, lambda filepath: is_library(filepath, acceptable_exts))
    if found_lib and platform.system() == 'Windows':
        found_lib = os.path.splitext(found_lib)[0]
    return found_lib, found_path

def get_library_linker_name(lib):
    found_lib, found_path = get_library_path(lib)
    if not found_lib:
        # Try x86 or x64
        found_lib, found_path = get_library_path(lib + get_architecture(), True)
        if not found_lib:
            found_lib, found_path = get_library_path('-'.join(
                [lib, get_prefered_msvc(), get_architecture()]), True)

    if found_lib:
        found_lib = re.sub(r'.dylib$|.so$|.dll$|.dll.a$|.a$', '', found_lib.split(os.path.sep)[-1])
        if platform.system() != 'Windows':
            found_lib = re.sub(r'^lib|', '', found_lib)

    return found_lib, found_path

def package_found(package, include_dirs):
    for idir in include_dirs:
        package_path = os.path.join(idir, package)
        if os.path.exists(package_path) and os.access(package_path, os.R_OK):
            return True
    return False

def build_hunspell_package(directory, force_build=False):
    tmp_lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'libs', 'tmp'))
    if not os.path.exists(tmp_lib_path):
        os.makedirs(tmp_lib_path)

    olddir = os.getcwd()
    if force_build or not os.path.exists(os.path.join(tmp_lib_path, 'lib', 'libhunspell-1.6.so.0.0.1')):
        try:
            os.chdir(directory)
            check_call(['autoreconf', '-vfi'])
            check_call(['./configure', '--prefix='+tmp_lib_path])
            check_call('make')
            check_call(['make', 'install'])
        finally:
            os.chdir(olddir)

    lib_path = os.path.abspath(os.path.join(get_python_lib(), 'libs', 'unix'))
    if os.path.exists(lib_path):
        shutil.rmtree(lib_path)
    os.makedirs(lib_path)

    shutil.copyfile(
        os.path.join(tmp_lib_path, 'lib', 'libhunspell-1.6.so.0.0.1'),
        os.path.join(lib_path, 'libhunspell-1.6.so.0'))
    os.symlink(
        os.path.join(lib_path, 'libhunspell-1.6.so.0'),
        os.path.join(lib_path, 'libhunspell.so'))
    shutil.rmtree(tmp_lib_path)

    return lib_path

def append_links(pkg, kw):
    linker_name, linker_path = get_library_linker_name(pkg)
    if linker_name:
        kw['libraries'].append(linker_name)
    if linker_path:
        kw['library_dirs'].append(linker_path)
    if linker_path and platform.system() != 'Windows':
        kw['runtime_library_dirs'].append(linker_path)
    return linker_name

def pkgconfig(*packages, **kw):
    try:
        flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
        status, response = getstatusoutput("pkg-config --libs --cflags {}".format(' '.join(packages)))
        if status != 0:
            raise RuntimeError(response)
        for token in response.split():
            kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
            if token[:2] in flag_map:
                arg = flag_map.get(token[:2])
                kw.setdefault(arg, []).append(token[2:])
                kw[arg] = list(set(kw[arg]))
            else: # throw others to extra_link_args
                kw.setdefault('extra_link_args', []).append(token)
                kw['extra_link_args'] = list(set(kw['extra_link_args']))
    except RuntimeError:
        kw['include_dirs'] = include_dirs(*packages)
        kw['library_dirs'] = []
        kw['runtime_library_dirs'] = []
        kw['libraries'] = []
        kw['extra_link_args'] = []

        if 'hunspell' in packages and not package_found('hunspell', kw['include_dirs']):
            # Prepare for hunspell if it's missing
            if not os.environ.get('SKIP_DOWNLOAD', False):
                if platform.system() == 'Linux':
                    download_and_extract('https://github.com/hunspell/hunspell/archive/v1.6.2.tar.gz',
                        os.path.join(BASE_DIR, 'external'))
                else:
                    download_and_extract('http://downloads.sourceforge.net/hunspell/hunspell-1.3.3.tar.gz',
                        os.path.join(BASE_DIR, 'external'))
                kw['include_dirs'] = include_dirs(*packages)
            else:
                raise RuntimeError("Could not find hunspell and not allowed to download")

        for pkg in packages:
            if not append_links(pkg, kw):
                if pkg == 'hunspell' and platform.system() == 'Linux':
                    lib_path = build_hunspell_package(os.path.join(BASE_DIR, 'external', 'hunspell-1.6.2'))
                    if not append_links(pkg, kw):
                        raise RuntimeError("Couldn't find lib dependency after building: {}".format(pkg))
                    else:
                        kw['extra_link_args'] += ['-Wl,-rpath,"{}"'.format(lib_path)]
                elif pkg == 'hunspell' and platform.system() != 'Windows':
                    lib_path = build_hunspell_package(os.path.join(BASE_DIR, 'external', 'hunspell-1.3.3'))
                    if not append_links(pkg, kw):
                        raise RuntimeError("Couldn't find lib dependency after building: {}".format(pkg))
                    else:
                        kw['extra_link_args'] += ['-Wl,-rpath,"{}"'.format(lib_path)]
                else:
                    raise RuntimeError("Couldn't find lib dependency: {}".format(pkg))

    return kw
