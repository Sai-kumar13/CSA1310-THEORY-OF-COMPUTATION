"""Configuration for Adaptive E-Commerce application."""
import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'adaptive-ecommerce-secret-key-2024')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'adaptive_ecommerce_db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    DEFAULT_USER_ID = 1  # Guest/demo user
