from glob import glob

from setuptools import find_packages, setup

setup(
    name='course_bringup',
    version='0.0.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/course_bringup']),
        ('share/course_bringup', ['package.xml']),
        ('share/course_bringup/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    extras_require={'test': ['pytest']},
    maintainer='bargomix',
    maintainer_email='beznik0812@gmail.com',
    description='Launch patrol and check delivery of turtlesim poses.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'pose_relay = course_bringup.pose_relay:main',
            'pose_subscriber = course_bringup.pose_subscriber:main',
        ],
    },
)
