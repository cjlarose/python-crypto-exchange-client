from distutils.core import setup
setup(
    name='cryptex',
    version='0.1',
    author='Chris LaRose',
    author_email='cjlarose@gmail.com',
    packages=['cryptex', 'cryptex.soxex'],
    install_requires=[
        'requests>=2.1.0,<3.0',
        'pytz>=2013.8',
        'websocket-client==0.12.0',
        'pusherclient==0.2.0'
    ]
)
