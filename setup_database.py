#!/usr/bin/env python3
"""
Script para configurar la base de datos inicial
Ejecutar este script antes de usar la aplicación Streamlit
"""

import mysql.connector
from mysql.connector import Error
from config import DATABASE_CONFIG

def create_database():
    """Crear la base de datos si no existe"""
    try:
        # Conectar sin especificar base de datos
        connection_config = DATABASE_CONFIG.copy()
        db_name = connection_config.pop('database')
        
        connection = mysql.connector.connect(**connection_config)
        cursor = connection.cursor()
        
        # Crear base de datos
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"✅ Base de datos '{db_name}' creada o ya existe")
        
        # Usar la base de datos
        cursor.execute(f"USE {db_name}")
        
        # Crear tabla clientes
        create_table_query = """
        CREATE TABLE IF NOT EXISTS clientes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cliente VARCHAR(255) NOT NULL,
            razon_social VARCHAR(255),
            domicilio TEXT,
            coord_x DECIMAL(10, 8),
            coord_y DECIMAL(11, 8),
            identificador VARCHAR(100),
            anulado BOOLEAN DEFAULT FALSE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_cliente (cliente),
            INDEX idx_identificador (identificador),
            INDEX idx_anulado (anulado)
        )
        """
        
        cursor.execute(create_table_query)
        print("✅ Tabla 'clientes' creada correctamente")
        
        # Insertar algunos datos de ejemplo (opcional)
        sample_data = [
            ("Empresa A", "Empresa A S.A.", "Av. Principal 123", -12.0464, -77.0428, "EMP001", False),
            ("Empresa B", "Empresa B S.R.L.", "Jr. Comercio 456", -12.0544, -77.0344, "EMP002", False),
            ("Empresa C", "Empresa C E.I.R.L.", "Av. Industrial 789", -12.0624, -77.0264, "EMP003", True)
        ]
        
        insert_query = """
        INSERT INTO clientes (cliente, razon_social, domicilio, coord_x, coord_y, identificador, anulado)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(insert_query, sample_data)
        connection.commit()
        print("✅ Datos de ejemplo insertados")
        
        cursor.close()
        connection.close()
        
        print("\n🎉 ¡Base de datos configurada correctamente!")
        print("Ahora puedes ejecutar: streamlit run app.py")
        
    except Error as e:
        print(f"❌ Error configurando base de datos: {e}")
        return False
    
    return True

def test_connection():
    """Probar la conexión a la base de datos"""
    try:
        connection = mysql.connector.connect(**DATABASE_CONFIG)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM clientes")
            count = cursor.fetchone()[0]
            print(f"✅ Conexión exitosa. Registros en tabla clientes: {count}")
            cursor.close()
            connection.close()
            return True
    except Error as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Configurando base de datos para Sistema de Clientes...")
    print("=" * 50)
    
    if create_database():
        print("\n🧪 Probando conexión...")
        test_connection()
    
    print("\n📝 Notas importantes:")
    print("- Asegúrate de que MySQL esté ejecutándose")
    print("- Verifica las credenciales en config.py")
    print("- Instala las dependencias: pip install -r requirements.txt")