===========
User editor
===========

User editor is Django app for editing user. It uses DynamicForms

Quick start
___________


1. Add "usereditor" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'usereditor',
    ]

2. Run `python manage.py migrate` to create the usereditor models.

3. Use DRF routers to make user editor accessible through browser

