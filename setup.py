import setuptools

with open('README.rst', 'r') as fh:
    long_description = fh.read()
with open('requirements.txt', 'r') as fh:
    requirements = fh.readlines()

setuptools.setup(
    name="django-usereditor",
    version="0.0.8",
    author="Klemen Pukl",
    author_email="klemen.pukl@velis.si",
    description="Aplication for user overview and editing",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/Brontes/django-usereditor",
    packages=setuptools.find_packages(include=('usereditor',)),
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.4',
    license='BSD-3-Clause',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Framework :: Django",
    ],
)
