from setuptools import setup, find_packages

setup(
    name="taskflow",
    version="2.0.0",
    description="A calm, powerful CLI task management assistant",
    author="Your Name",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'taskflow=task_manager.main:main',
        ],
    },
    install_requires=[
        # No external dependencies - pure Python
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
        "Topic :: Office/Business :: Scheduling",
    ],
)