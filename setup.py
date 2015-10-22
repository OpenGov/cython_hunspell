import os
import sys
from setuptools import setup, find_packages, Extension
from find_library import pkgconfig
from collections import defaultdict

VERSION = '1.1.3'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
BUILD_ARGS = defaultdict(lambda: ['-O3', '-g0'])
for compiler, args in [
        ('msvc', ['/EHsc', '/DHUNSPELL_STATIC']),
        ('gcc', ['-O3', '-g0', '-DHUNSPELL_STATIC'])]:
    BUILD_ARGS[compiler] = args

def cleanup_pycs():
    file_tree = os.walk(os.path.join(BASE_DIR, 'hunspell'))
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

def read(fname):
    # Utility function to read the README file.
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def readMD(fname):
    # Utility function to read the README file.
    full_fname = os.path.join(os.path.dirname(__file__), fname)
    if 'PANDOC_PATH' in os.environ:
        import pandoc
        pandoc.core.PANDOC_PATH = os.environ['PANDOC_PATH']
        doc = pandoc.Document()
        with open(full_fname) as fhandle:
            doc.markdown = fhandle.read()
        return doc.rst
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

if building:
    if (profiling or linetrace) and not force_rebuild:
        print "WARNING: profiling or linetracing specified without forced rebuild"
    from Cython.Build import cythonize
    from Cython.Distutils import build_ext

    ext_modules = cythonize([
        Extension(
            'hunspell.hunspell',
            [os.path.join('hunspell', 'hunspell.pyx')],
            **pkgconfig('hunspell', language='c++')
        )
    ], force=force_rebuild)
else:
    from setuptools.command.build_ext import build_ext
    ext_modules = [
        Extension(
            'hunspell.hunspell',
            [os.path.join('hunspell', 'hunspell.cpp')],
            **pkgconfig('hunspell', language='c++')
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

setup(
    name='CyHunspell',
    version=VERSION,
    author='Matthew Seal',
    author_email='mseal@opengov.us',
    description='A wrapper on hunspell for use in Python',
    long_description=readMD('README.md'),
    ext_modules=ext_modules,
    install_requires=required,
    cmdclass={ 'build_ext': build_ext_compiler_check },
    license='MIT',
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
        'Programming Language :: Python :: 2 :: Only'
    ]
)
