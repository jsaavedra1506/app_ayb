# config.py - Configuración de la base de datos

# Configuración de MySQL
DATABASE_CONFIG = {
    'host': '168.181.187.43',          # Cambia por tu host de MySQL
    'database': 'clientes_db',    # Nombre de tu base de datos
    'user': 'root',         # Tu usuario de MySQL
    'password': 'be51beBIde',  # Tu contraseña de MySQL
    'port': 3306,                 # Puerto de MySQL (por defecto 3306)
    'autocommit': True,
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci' 
}

# Configuración alternativa usando variables de entorno (recomendado para producción)
import os

# Descomenta estas líneas si prefieres usar variables de entorno
"""
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'clientes_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 3306)),
    'autocommit': True,
    'charset': 'utf8mb4'
}
"""
