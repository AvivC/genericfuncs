from setuptools import setup
from os import path

_here = path.dirname(path.abspath(__file__))
_readme = open(path.join(_here, 'README.rst')).read()

setup(
    name='genericfuncs',
    description='Dynamic dispatch over arbitrary predicates',
    long_description=_readme,
    version='0.1.0',
    author='Aviv Cohn',
    author_email='avivcohn123@yahoo.com',
    license='MIT',
    py_modules=['genericfuncs'],
    classifiers=[
        'Development Status :: 3 - Alpha'
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    keywords='generic functions utility programming development'
)
