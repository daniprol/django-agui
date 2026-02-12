"""Contrib module for framework-specific backends.

This module provides integrations with various Django API frameworks:
- Django REST Framework (DRF): django_agui.contrib.drf
- Django Ninja: django_agui.contrib.ninja
- Django Bolt: django_agui.contrib.bolt

Usage:
    # Django REST Framework
    from django_agui.contrib.drf import get_drf_urlpatterns

    # Django Ninja
    from django_agui.contrib.ninja import get_ninja_urlpatterns

    # Django Bolt
    from django_agui.contrib.bolt import get_bolt_urlpatterns

Each framework integration requires the corresponding package to be installed:
    pip install djangorestframework
    pip install django-ninja
    pip install django-bolt
"""
