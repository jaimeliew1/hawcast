# https://python-packaging.readthedocs.io
from setuptools import setup

setup(name='hawcast',
      version='0.1',
      description='a CLI tool for HAWC2 simulation workflows.',
      url='https://github.com/jaimeliew1/hawcast.git',
      author='Jaime Liew',
      author_email='jaimeliew1@gmail.com',
      license='MIT',
      packages=['hawcast'],
      install_requires=[],
      zip_safe=False,
      entry_points = {
        'console_scripts': ['hawcast=hawcast.hawcast:Hawcast_parser']})
