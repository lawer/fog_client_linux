from distutils.core import setup

setup(
    name='fog_client',
    version='0.4.1',
    author='Carles Gonzalez',
    packages=['components', 'cliapp'],
    py_modules=['fog_lib', 'fog_client'],
    requires=['cuisine',
              'requests (>=0.13)'],
    scripts=['fog_client.py'],
    data_files=[('/etc/init', ['aux/fog_client.conf']),
                ('/etc', ['aux/fog_client.ini'])],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: System :: Systems Administration'])
