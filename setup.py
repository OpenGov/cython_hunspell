import os
import sys
from warnings import warn
from setuptools import setup, find_packages, Extension
from find_library import pkgconfig
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
BUILD_ARGS = defaultdict(lambda: ['-O3', '-g0'])
for compiler, args in [
        ('msvc', ['/EHsc', '/DHUNSPELL_STATIC']),
        ('gcc', ['-O3', '-g0', '-DHUNSPELL_STATIC'])]:
    BUILD_ARGS[compiler] = args

def cleanup_pycs():
    file_tree = os.walk(os.path.join(BASE_DIR, 'cyhunspell'))
    to_delete = []
    for root, directory, file_list in file_tree:
        if len(file_list):
            for file_name in file_list:
                if file_name.endswith(".pyc"):
                    to_delete.append(os.path.join(root, file_name))
    for file_path in to_delete:
        try:
            os.remove(file_path)
        except:
            pass

python_2 = sys.version_info[0] == 2
def read(fname):
    with open(fname, 'rU' if python_2 else 'r') as fhandle:
        return fhandle.read()

def pandoc_read_md(fname):
    if 'PANDOC_PATH' not in os.environ:
        raise ImportError("No pandoc path to use")
    import pandoc
    pandoc.core.PANDOC_PATH = os.environ['PANDOC_PATH']
    doc = pandoc.Document()
    doc.markdown = read(fname)
    return doc.rst

def pypandoc_read_md(fname):
    import pypandoc
    os.environ.setdefault('PYPANDOC_PANDOC', os.environ['PANDOC_PATH'])
    return pypandoc.convert_text(read(fname), 'rst', format='md')

def read_md(fname):
    # Utility function to read the README file.
    full_fname = os.path.join(os.path.dirname(__file__), fname)

    try:
        return pandoc_read_md(full_fname)
    except (ImportError, AttributeError):
        try:
            return pypandoc_read_md(full_fname)
        except (ImportError, AttributeError):
            return read(fname)
    else:
        return read(fname)

profiling = '--profile' in sys.argv or '-p' in sys.argv
linetrace = '--linetrace' in sys.argv or '-l' in sys.argv
building = 'build_ext' in sys.argv
force_rebuild = '--force' in sys.argv or '-f' in sys.argv and building

datatypes = ['*.aff', '*.dic', '*.pxd', '*.pyx', '*.pyd', '*.pxd', '*.so', '*.lib', '*hpp']
packages = find_packages(exclude=['*.tests', '*.tests.*', 'tests.*', 'tests'])
packages.extend(['dictionaries', 'libs.msvc'])
required = [req.strip() for req in read('requirements.txt').splitlines() if req.strip()]
package_data = {'' : datatypes}
hunspell_config = pkgconfig('hunspell', language='c++')

if building:
    if (profiling or linetrace) and not force_rebuild:
        warn("WARNING: profiling or linetracing specified without forced rebuild")
    from Cython.Build import cythonize
    from Cython.Distutils import build_ext

    ext_modules = cythonize([
        Extension(
            'hunspell.hunspell',
            [os.path.join('hunspell', 'hunspell.pyx')],
            **hunspell_config
        )
    ], force=force_rebuild)
else:
    from setuptools.command.build_ext import build_ext
    ext_modules = [
        Extension(
            'hunspell.hunspell',
            [os.path.join('hunspell', 'hunspell.cpp')],
            **hunspell_config
        )
    ]
    package_data["hunspell"] = ["*.pxd"]

class build_ext_compiler_check(build_ext):
    def build_extensions(self):
        compiler = self.compiler.compiler_type
        args = BUILD_ARGS[compiler]
        for ext in self.extensions:
            ext.extra_compile_args = args
        build_ext.build_extensions(self)

    def run(self):
        cleanup_pycs()
        build_ext.run(self)

VERSION = read(os.path.join(BASE_DIR, 'VERSION')).strip()

setup(
    name='CyHunspell',
    version=VERSION,
    author='Matthew Seal',
    author_email='mseal@opengov.us',
    description='A wrapper on hunspell for use in Python',
    long_description=read_md('README.md'),
    ext_modules=ext_modules,
    install_requires=required,
    cmdclass={ 'build_ext': build_ext_compiler_check },
    license='MIT + MPL 1.1/GPL 2.0/LGPL 2.1',
    packages=packages,
    scripts=['find_library.py', 'tar_download.py'],
    test_suite='tests',
    zip_safe=False,
    url='https://github.com/OpenGov/cython_hunspell',
    download_url='https://github.com/OpenGov/cython_hunspell/tarball/v' + VERSION,
    package_data=package_data,
    keywords=['hunspell', 'spelling', 'correction'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3'
    ]
)
