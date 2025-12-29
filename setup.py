from setuptools import setup, find_packages

setup(
    name="taskflow-cli",
    version="2.1.0",
    description="A calm, powerful CLI task management assistant with time management features",
    author="K Mohith Kannan",
    author_email="your-email@example.com",
    url="https://github.com/Mohith535/TaskFlow",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'taskflow=task_manager.main:main',  # FIXED THIS LINE
        ],
    },
    install_requires=[],
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
    keywords="cli task manager productivity time-management focus pomodoro",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
)