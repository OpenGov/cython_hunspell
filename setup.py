import os
import sys
import platform
from setuptools import setup, find_packages, Extension
from setuptools.command.egg_info import egg_info
from subprocess import check_call
from find_library import pkgconfig

VERSION = '1.1.0'

requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')

try:
    from Cython.Build import cythonize
    from Cython.Distutils import build_ext
except ImportError:
    check_call('pip install -r {}'.format(requirements_file), stdout=sys.stdout, stderr=sys.stderr, shell=True)
    from Cython.Build import cythonize
    from Cython.Distutils import build_ext

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

datatypes = ['*.aff', '*.dic', '*.pxd', '*.pyx', '*.pyd', '*.so', '*.lib', '*hpp']
packages = find_packages(exclude=['*.tests', '*.tests.*', 'tests.*', 'tests'])
packages.append('dictionaries')
required = [req.strip() for req in read('requirements.txt').splitlines() if req.strip()]

build_args = ['-O3', '-g0'] if platform.system() != 'Windows' else ['/EHsc', '/DHUNSPELL_STATIC']
ext_modules = cythonize([
    Extension(
        'hunspell.hunspell',
        [os.path.join('hunspell', 'hunspell.pyx')],
        extra_compile_args=build_args,
        **pkgconfig('hunspell', language='c++')
    )
])

class egg_build(egg_info):
    def run(self):
        # Hack to only build on pip install
        if '--egg-base' in sys.argv:
            # Only build on non-windows machines
            check_call([sys.executable, __file__, 'build_ext', '--inplace'],
                shell=False, stdout=sys.stdout, stderr=sys.stderr)
        egg_info.run(self)

setup(
    name='CyHunspell',
    version=VERSION,
    author='Matthew Seal',
    author_email='mseal@opengov.us',
    description='A wrapper on hunspell for use in Python',
    long_description=readMD('README.md'),
    ext_modules=ext_modules,
    install_requires=required,
    cmdclass={ 'build_ext': build_ext, 'egg_info': egg_build },
    license='New BSD',
    packages=packages,
    scripts=['find_library.py', 'tar_download.py'],
    test_suite='tests',
    zip_safe=False,
    url='https://github.com/OpenGov/cython_hunspell',
    download_url='https://github.com/OpenGov/cython_hunspell/tarball/v' + VERSION,
    package_data={'' : datatypes},
    keywords=['hunspell', 'spelling', 'correction'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2 :: Only'
    ]
)
