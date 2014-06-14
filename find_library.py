#
# This is a cross-platform shared library search mechanism. Tested on:
# OSX, Ubuntu, Fedora, and Windows XP+
#
import os
import glob
import platform
import re
import commands
import sys
import shutil
from subprocess import check_call
from tar_download import download_and_extract

if __name__ == '__main__':
    download_and_extract('http://downloads.sourceforge.net/hunspell/hunspell-1.3.3.tar.gz', 'external')

def get_architecture():
    return 'x64' if sys.maxsize > 2**32 else 'x86'

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
                    return filepath, pn
            elif os.path.exists(filepath):
                return filepath, pn
    return None, None

def is_library(filepath, acceptable_exts):
    # TODO - This is broken for ".dll.a"
    return os.path.isfile(filepath) and (os.path.splitext(filepath)[-1] in acceptable_exts)

def is_header(filepath):
    return os.path.isfile(filepath)

def include_dirs():
    dirs = [
        os.path.abspath(os.path.join(os.curdir, 'hunspell')),
        # Download path for windows if missing
        os.path.abspath(os.path.join(os.curdir, 'external', 'hunspell-1.3.3', 'src')),
    ]
    if platform.system() != 'Windows':
        dirs.extend([
            '/usr/local/include',
            '/opt/include',
            '/usr/include'
        ])
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
            # Built binaries home
            os.path.join(os.path.dirname(__file__), 'libs', 'msvc')
        ])
        dirs.extend(list(set(os.environ.get('PATH').split(os.path.pathsep))))
        dirs = [os.path.abspath(path) for path in dirs]
    else:
        dirs.extend([
            os.path.join(os.path.dirname(__file__), 'libs', 'unix'),
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
            '.lib'
        ]
    elif platform.system() == 'Darwin':
        acceptable_exts.append('.dylib')

    names = form_possible_names(lib, acceptable_exts)
    found_lib, found_path = do_search(paths, names, lambda filepath: is_library(filepath, acceptable_exts))
    if found_lib and platform.system() == 'Windows':
        found_lib = os.path.splitext(found_lib)[0]
    return found_lib, found_path

def get_library_linker_name(lib):
    found_lib, found_path = get_library_path(lib)
    if not found_lib:
        # Try x86 or x64
        found_lib, found_path = get_library_path(lib + get_architecture())

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

def build_package(package, directory):
    tmp_lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'libs', 'tmp'))
    if not os.path.exists(tmp_lib_path):
        os.makedirs(tmp_lib_path)

    olddir = os.getcwd()
    try:
        os.chdir(directory)
        check_call(['./configure', '--prefix='+tmp_lib_path])
        check_call('make')
        check_call(['make', 'install'])
    finally:
        os.chdir(olddir)

    lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'libs', 'unix'))
    if not os.path.exists(lib_path):
        os.makedirs(lib_path)

    if package == 'hunspell':
        shutil.copyfile(
            os.path.join(tmp_lib_path, 'lib', 'libhunspell-1.3.so.0.0.0'),
            os.path.join(lib_path, 'libhunspell.so'))
        shutil.rmtree(tmp_lib_path)

def append_links(pkg, kw):
    linker_name, linker_path = get_library_linker_name(pkg)
    if linker_name:
        kw['libraries'].append(linker_name)
    if linker_path:
        kw['library_dirs'].append(linker_path)
    return linker_name

def pkgconfig(*packages, **kw):
    try:
        raise Exception("SKIP!")
        flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
        status, response = commands.getstatusoutput("pkg-config --libs --cflags {}".format(' '.join(packages)))
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
        kw['library_dirs'] = []
        kw['libraries'] = []

        if 'hunspell' in packages and not package_found('hunspell', kw['include_dirs']):
            # Prepare for hunspell if it's missing
            download_and_extract('http://downloads.sourceforge.net/hunspell/hunspell-1.3.3.tar.gz', 'external')

        for pkg in packages:
            if not append_links(pkg, kw):
                if pkg == 'hunspell' and platform.system() != 'Windows':
                    build_package(pkg, os.path.join('external', 'hunspell-1.3.3'))
                    if not append_links(pkg, kw):
                        print "Couldn't find lib dependency after building: {}".format(pkg)
                else:
                    print "Couldn't find lib dependency: {}".format(pkg)

    return kw
