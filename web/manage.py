#!/usr/bin/env python
"""Django management entry point for the Pleasant Crescent web platform."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pleasant.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
