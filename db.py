"""Módulo de base de datos SQLite para ZENIT (delegado a OpenJarvis.zenit)."""
from openjarvis.zenit.db import *
import openjarvis.zenit.db as _impl

DB_PATH = _impl.DB_PATH
CSV_PATH = _impl.CSV_PATH
