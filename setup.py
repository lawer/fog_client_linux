from distutils.core import setup

setup(name='fog_client',
      version='0.0.10',
      author='Carles Gonzalez',
      packages=['components'],
      py_modules=['fog_lib', 'cuisine'],
      requires=['cuisine', 'requests (>=0.13)'],
      scripts=['fog_client.py'],
      data_files=[('/etc/init', ['fog_client.conf']),
                  ('/etc', ['fog_client.ini'])],
      classifiers=[
             'Development Status :: 3 - Alpha',
             'Environment :: Console',
             'Intended Audience :: System Administrators',
             'License :: OSI Approved :: Python Software Foundation License',
             'Operating System :: POSIX',
             'Programming Language :: Python',
             'Topic :: System :: Systems Administration'])
