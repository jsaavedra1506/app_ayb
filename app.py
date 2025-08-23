import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import io
import folium
from streamlit_folium import st_folium
from config import DATABASE_CONFIG

# Configurar tu API Key de Google Maps aquí
GOOGLE_MAPS_API_KEY = "AIzaSyAbyMzkvJ1NgEUQVfBq7VbOYpDVKazcTxE"  # Reemplaza con tu API Key real

class ClienteDB:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Conectar a la base de datos MySQL"""
        try:
            self.connection = mysql.connector.connect(**DATABASE_CONFIG)
            if self.connection.is_connected():
                return True
        except Error as e:
            st.error(f"Error conectando a MySQL: {e}")
            return False
        return False
    
    def disconnect(self):
        """Desconectar de la base de datos"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def create_table(self):
        """Crear la tabla de clientes si no existe"""
        if not self.connect():
            return False
        
        try:
            cursor = self.connection.cursor()
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
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
            cursor.close()
            return True
        except Error as e:
            st.error(f"Error creando tabla: {e}")
            return False
        finally:
            self.disconnect()
    
    def clear_table(self):
        """Eliminar todos los registros de la tabla clientes"""
        if not self.connect():
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM clientes")
            self.connection.commit()
            cursor.close()
            return True
        except Error as e:
            st.error(f"Error eliminando datos: {e}")
            return False
        finally:
            self.disconnect()
    
    def insert_clientes(self, df):
        """Insertar múltiples clientes desde DataFrame"""
        if not self.connect():
            return False
        
        try:
            cursor = self.connection.cursor()
            insert_query = """
            INSERT INTO clientes (cliente, razon_social, domicilio, coord_x, coord_y, identificador, anulado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Convertir DataFrame a lista de tuplas
            data_to_insert = []
            for _, row in df.iterrows():
                data_to_insert.append((
                    row.get('Cliente', ''),
                    row.get('Razon social', ''),
                    row.get('Domicilio', ''),
                    row.get('Coord X', None),
                    row.get('Coord Y', None),
                    row.get('Identificador', ''),
                    row.get('Anulado', False)
                ))
            
            cursor.executemany(insert_query, data_to_insert)
            self.connection.commit()
            cursor.close()
            return True
        except Error as e:
            st.error(f"Error insertando datos: {e}")
            return False
        finally:
            self.disconnect()
    
    def get_clientes(self):
        """Obtener todos los clientes"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM clientes ORDER BY cliente")
            result = cursor.fetchall()
            cursor.close()
            return pd.DataFrame(result)
        except Error as e:
            st.error(f"Error obteniendo datos: {e}")
            return None
        finally:
            self.disconnect()
    
    def get_clientes_con_coordenadas(self):
        """Obtener solo clientes que tienen coordenadas válidas"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM clientes 
            WHERE coord_x IS NOT NULL 
            AND coord_y IS NOT NULL 
            AND coord_x != 0 
            AND coord_y != 0
            ORDER BY cliente
            """
            cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return pd.DataFrame(result)
        except Error as e:
            st.error(f"Error obteniendo datos: {e}")
            return None
        finally:
            self.disconnect()
    
    def buscar_cliente(self, termino_busqueda):
        """Buscar cliente por nombre, razón social o identificador"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM clientes 
            WHERE (cliente LIKE %s 
            OR razon_social LIKE %s 
            OR identificador LIKE %s)
            AND coord_x IS NOT NULL 
            AND coord_y IS NOT NULL 
            AND coord_x != 0 
            AND coord_y != 0
            ORDER BY cliente
            """
            search_term = f"%{termino_busqueda}%"
            cursor.execute(query, (search_term, search_term, search_term))
            result = cursor.fetchall()
            cursor.close()
            return pd.DataFrame(result)
        except Error as e:
            st.error(f"Error buscando cliente: {e}")
            return None
        finally:
            self.disconnect()

    def buscar_cliente_google_maps(self, termino_busqueda):
        """Buscar cliente específicamente para Google Maps por cliente y razón social"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM clientes 
            WHERE (cliente LIKE %s 
            OR razon_social LIKE %s)
            AND coord_x IS NOT NULL 
            AND coord_y IS NOT NULL 
            AND coord_x != 0 
            AND coord_y != 0
            ORDER BY 
                CASE 
                    WHEN cliente LIKE %s THEN 1
                    WHEN razon_social LIKE %s THEN 2
                    ELSE 3
                END,
                cliente
            """
            search_term = f"%{termino_busqueda}%"
            exact_search = f"{termino_busqueda}%"
            cursor.execute(query, (search_term, search_term, exact_search, exact_search))
            result = cursor.fetchall()
            cursor.close()
            return pd.DataFrame(result)
        except Error as e:
            st.error(f"Error buscando cliente: {e}")
            return None
        finally:
            self.disconnect()

def process_excel_file(uploaded_file):
    """Procesar archivo Excel y extraer solo los campos necesarios"""
    try:
        # Leer el archivo Excel
        df = pd.read_excel(uploaded_file)
        
        # Campos requeridos
        required_fields = ['Cliente', 'Razon social', 'Domicilio', 'Coord X', 'Coord Y', 'Identificador', 'Anulado']
        
        # Mostrar las columnas disponibles
        st.write("**Columnas disponibles en el archivo:**")
        st.write(list(df.columns))
        
        # Crear DataFrame con solo los campos requeridos
        processed_df = pd.DataFrame()
        
        for field in required_fields:
            if field in df.columns:
                processed_df[field] = df[field]
            else:
                # Si el campo no existe, crear columna vacía o con valor por defecto
                if field == 'Anulado':
                    processed_df[field] = 'NO'  # Valor por defecto
                elif field in ['Coord X', 'Coord Y']:
                    processed_df[field] = None
                else:
                    processed_df[field] = ''
        
        # Convertir campo Anulado de SI/NO a True/False
        if 'Anulado' in processed_df.columns:
            processed_df['Anulado'] = processed_df['Anulado'].fillna('NO')  # Llenar valores vacíos con 'NO'
            processed_df['Anulado'] = processed_df['Anulado'].astype(str).str.upper()  # Convertir a mayúsculas
            processed_df['Anulado_Bool'] = processed_df['Anulado'].map({
                'SI': True,
                'SÍ': True,  # Por si tiene tilde
                'S': True,   # Por si está abreviado
                'YES': True, # Por si está en inglés
                'Y': True,
                '1': True,
                'VERDADERO': True,
                'TRUE': True,
                'NO': False,
                'N': False,
                '0': False,
                'FALSO': False,
                'FALSE': False
            })
            
            # Si hay valores no mapeados, mostrar advertencia y usar False por defecto
            unmapped_values = processed_df[processed_df['Anulado_Bool'].isna()]['Anulado'].unique()
            if len(unmapped_values) > 0:
                st.warning(f"⚠️ Valores no reconocidos en campo 'Anulado': {list(unmapped_values)}. Se asignarán como 'NO' (False).")
                processed_df['Anulado_Bool'] = processed_df['Anulado_Bool'].fillna(False)
            
            # Reemplazar la columna original con la versión booleana
            processed_df['Anulado'] = processed_df['Anulado_Bool']
            processed_df = processed_df.drop('Anulado_Bool', axis=1)
        
        # Limpiar datos
        processed_df = processed_df.fillna('')
        
        # Mostrar información sobre la conversión
        if 'Anulado' in processed_df.columns:
            anulados_count = processed_df['Anulado'].sum()
            st.info(f"📊 Conversión completada: {anulados_count} clientes marcados como anulados (SI), {len(processed_df) - anulados_count} activos (NO)")
        
        return processed_df
        
    except Exception as e:
        st.error(f"Error procesando archivo: {e}")
        return None

def crear_mapa_clientes(df_clientes, cliente_seleccionado=None):
    """Crear mapa interactivo con los clientes"""
    if df_clientes.empty:
        return None
    
    # Coordenadas del centro de Iquitos, Perú
    center_lat = -3.7489894
    center_lon = -73.2570029
    zoom_start = 11
    
    # Si hay un cliente seleccionado, centrarse en él
    if cliente_seleccionado is not None and not df_clientes.empty:
        center_lat = float(cliente_seleccionado['coord_y'])  # coord_y es latitud
        center_lon = float(cliente_seleccionado['coord_x'])  # coord_x es longitud
        zoom_start = 15
    
    # Crear el mapa
    mapa = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles='OpenStreetMap'
    )
    
    # Agregar marcadores para cada cliente
    for idx, cliente in df_clientes.iterrows():
        lat = float(cliente['coord_y'])  # coord_y es latitud
        lon = float(cliente['coord_x'])  # coord_x es longitud
        
        # Determinar color del marcador según estado
        color = 'red' if cliente['anulado'] else 'green'
        icon_symbol = 'remove' if cliente['anulado'] else 'ok'
        
        # Crear popup con información del cliente
        popup_html = f"""
        <div style="width: 220px;">
            <h4>{cliente['identificador']} - {cliente['cliente']}</h4>
            <p><b>Razón Social:</b> {cliente['razon_social']}</p>
            <p><b>Domicilio:</b> {cliente['domicilio']}</p>
            <p><b>Estado:</b> {'🔴 Anulado' if cliente['anulado'] else '🟢 Activo'}</p>
            <p><b>Coordenadas:</b> {lat:.4f}, {lon:.4f}</p>
        </div>
        """
        
        # Determinar si es el cliente seleccionado
        if cliente_seleccionado is not None and cliente['id'] == cliente_seleccionado['id']:
            # Marcador especial para cliente seleccionado
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"⭐ {cliente['identificador']} - {cliente['cliente']} (SELECCIONADO)",
                icon=folium.Icon(color='blue', icon='star', prefix='fa')
            ).add_to(mapa)
        else:
            # Marcador normal
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"📍 {cliente['identificador']} - {cliente['cliente']}",
                icon=folium.Icon(color=color, icon=icon_symbol, prefix='glyphicon')
            ).add_to(mapa)
    
    return mapa

def crear_google_map_html(df_clientes, cliente_seleccionado=None, api_key=""):
    """Crear mapa de Google Maps con marcadores de clientes"""
    
    # Centro de Iquitos, Perú
    center_lat = -3.7489894
    center_lon = -73.2570029
    zoom_level = 11
    
    # Si hay cliente seleccionado, centrar en él
    if cliente_seleccionado is not None:
        center_lat = float(cliente_seleccionado['coord_y'])  # coord_y es latitud
        center_lon = float(cliente_seleccionado['coord_x'])  # coord_x es longitud
        zoom_level = 15
    
    # Preparar los datos de marcadores
    markers_js = ""
    for idx, cliente in df_clientes.iterrows():
        lat = float(cliente['coord_y'])  # coord_y es latitud
        lon = float(cliente['coord_x'])  # coord_x es longitud
        
        # Escapar comillas en los textos
        cliente_name = str(cliente['cliente']).replace("'", "\\'").replace('"', '\\"')
        razon_social = str(cliente['razon_social']).replace("'", "\\'").replace('"', '\\"')
        domicilio = str(cliente['domicilio']).replace("'", "\\'").replace('"', '\\"')
        identificador = str(cliente['identificador']).replace("'", "\\'").replace('"', '\\"')
        
        # Color del marcador según estado
        marker_color = '#FF0000' if cliente['anulado'] else '#00FF00'  # Rojo si anulado, verde si activo
        estado_texto = 'Anulado' if cliente['anulado'] else 'Activo'
        estado_icon = '🔴' if cliente['anulado'] else '🟢'
        
        # Determinar si es el cliente seleccionado
        is_selected = cliente_seleccionado is not None and cliente['id'] == cliente_seleccionado['id']
        marker_icon = 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png' if is_selected else f'https://maps.google.com/mapfiles/ms/icons/{"red" if cliente["anulado"] else "green"}-dot.png'
        
        info_content = f"""
        <div style="max-width: 300px; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: #333;">
                {identificador} - {cliente_name}
                {'⭐' if is_selected else ''}
            </h3>
            <p><strong>Razón Social:</strong><br/>{razon_social}</p>
            <p><strong>Domicilio:</strong><br/>{domicilio}</p>
            <p><strong>Estado:</strong> {estado_icon} {estado_texto}</p>
            <p><strong>Coordenadas:</strong> {lat:.4f}, {lon:.4f}</p>
            <div style="margin-top: 15px;">
                <a href="https://www.google.com/maps/dir/?api=1&destination={lat},{lon}" 
                   target="_blank" 
                   style="background: #4285f4; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; font-size: 12px;">
                   📍 Cómo llegar
                </a>
                <a href="https://waze.com/ul?ll={lat},{lon}&navigate=yes" 
                   target="_blank" 
                   style="background: #00d4aa; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; font-size: 12px; margin-left: 5px;">
                   🚗 Waze
                </a>
            </div>
        </div>
        """
        
        markers_js += f"""
        var marker{idx} = new google.maps.Marker({{
            position: {{ lat: {lat}, lng: {lon} }},
            map: map,
            title: '{identificador} - {cliente_name}',
            icon: '{marker_icon}'
        }});
        
        var infoWindow{idx} = new google.maps.InfoWindow({{
            content: `{info_content}`
        }});
        
        marker{idx}.addListener('click', function() {{
            infoWindow{idx}.open(map, marker{idx});
        }});
        """
    
    # HTML completo del mapa
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mapa de Clientes</title>
        <style>
            #map {{
                height: 500px;
                width: 100%;
            }}
            .map-container {{
                padding: 0;
                margin: 0;
            }}
        </style>
    </head>
    <body>
        <div class="map-container">
            <div id="map"></div>
        </div>

        <script>
            function initMap() {{
                var map = new google.maps.Map(document.getElementById('map'), {{
                    zoom: {zoom_level},
                    center: {{ lat: {center_lat}, lng: {center_lon} }},
                    mapTypeId: 'roadmap'
                }});
                
                {markers_js}
            }}
        </script>
        <script async defer 
            src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap">
        </script>
    </body>
    </html>
    """
    
    return html_content

def main():
    st.set_page_config(
        page_title="Gestión de Clientes",
        page_icon="🏢",
        layout="wide"
    )
    
    st.title("🏢 Sistema de Gestión de Clientes")
    st.markdown("---")
    
    # Inicializar la base de datos
    db = ClienteDB()
    
    # Crear tabla si no existe
    if db.create_table():
        st.success("✅ Conexión a base de datos establecida")
    else:
        st.error("❌ Error conectando a la base de datos")
        return
    
    # Sidebar para navegación
    st.sidebar.title("📋 Menú de Opciones")
    option = st.sidebar.selectbox(
        "Selecciona una opción:",
        ["Ver Clientes", "Google Maps", "Importar desde Excel", "Estadísticas"]
    )
    
    if option == "Ver Clientes":
        st.header("👥 Lista de Clientes")
        
        # Botón para actualizar datos
        if st.button("🔄 Actualizar"):
            st.rerun()
        
        # Obtener y mostrar clientes
        df_clientes = db.get_clientes()
        if df_clientes is not None and not df_clientes.empty:
            st.dataframe(
                df_clientes,
                use_container_width=True,
                hide_index=True
            )
            
            # Información adicional
            st.info(f"Total de clientes: {len(df_clientes)}")
            
        else:
            st.warning("No hay clientes registrados en la base de datos.")

    elif option == "Google Maps":
        st.header("🌍 Google Maps - Localización de Clientes")
        
        # Usar la API Key configurada
        google_api_key = GOOGLE_MAPS_API_KEY
        
        if google_api_key == "TU_API_KEY_AQUI":
            st.error("""
            🔑 **API Key no configurada**
            
            Para usar Google Maps, reemplaza la línea:
            ```python
            GOOGLE_MAPS_API_KEY = "TU_API_KEY_AQUI"
            ```
            
            Con tu API Key real:
            ```python
            GOOGLE_MAPS_API_KEY = "AIzaSy..."
            ```
            """)
            return
        
        # Configuración en sidebar
        with st.sidebar:
            st.markdown("---")
            st.subheader("🔍 Buscador Especializado")
            
            # Buscador específico para cliente y razón social
            termino_busqueda_gm = st.text_input(
                "Buscar por Cliente o Razón Social:",
                placeholder="Escribe el nombre del cliente o razón social...",
                help="Busca específicamente en los campos 'Cliente' y 'Razón Social'",
                key="google_maps_search"
            )
            
            # Filtros
            st.markdown("**Filtros:**")
            mostrar_anulados_gm = st.checkbox("Mostrar clientes anulados", value=False, key="mostrar_anulados_gm")
            solo_activos_gm = st.checkbox("Solo clientes activos", value=False, key="solo_activos_gm")
            limite_resultados = st.slider("Máximo de marcadores en mapa:", 1, 100, 50)
        
        # Obtener datos
        df_clientes_gm = db.get_clientes_con_coordenadas()
        
        if df_clientes_gm is not None and not df_clientes_gm.empty:
            # Variables para el cliente seleccionado
            cliente_seleccionado_gm = None
            df_mostrar_gm = df_clientes_gm.copy()
            
            # Aplicar filtros de estado
            if solo_activos_gm:
                df_mostrar_gm = df_mostrar_gm[df_mostrar_gm['anulado'] == False]
            elif not mostrar_anulados_gm:
                df_mostrar_gm = df_mostrar_gm[df_mostrar_gm['anulado'] == False]
            
            # Procesar búsqueda
            if termino_busqueda_gm:
                df_busqueda_gm = db.buscar_cliente_google_maps(termino_busqueda_gm)
                
                if df_busqueda_gm is not None and not df_busqueda_gm.empty:
                    # Aplicar los mismos filtros de estado a los resultados de búsqueda
                    if solo_activos_gm:
                        df_busqueda_gm = df_busqueda_gm[df_busqueda_gm['anulado'] == False]
                    elif not mostrar_anulados_gm:
                        df_busqueda_gm = df_busqueda_gm[df_busqueda_gm['anulado'] == False]
                    
                    if not df_busqueda_gm.empty:
                        st.success(f"🎯 Encontrados {len(df_busqueda_gm)} cliente(s) que coinciden con '{termino_busqueda_gm}'")
                        
                        # Mostrar resultados de la búsqueda
                        with st.expander(f"📋 Resultados de búsqueda ({len(df_busqueda_gm)})", expanded=True):
                            for idx, cliente in df_busqueda_gm.iterrows():
                                col1, col2 = st.columns([3, 1])
                                
                                with col1:
                                    estado_icon = "🔴" if cliente['anulado'] else "🟢"
                                    st.write(f"{estado_icon} **{cliente['cliente']}**")
                                    st.write(f"   📍 *{cliente['razon_social']}*")
                                    st.write(f"   📍 {cliente['domicilio']}")
                                
                                with col2:
                                    if st.button(f"📍 Ver", key=f"ver_gm_{cliente['id']}"):
                                        cliente_seleccionado_gm = cliente.to_dict()
                                        st.success(f"Cliente seleccionado: {cliente['cliente']}")
                        
                        # Seleccionar cliente para centrar mapa
                        if len(df_busqueda_gm) == 1:
                            cliente_seleccionado_gm = df_busqueda_gm.iloc[0].to_dict()
                            st.info(f"🎯 **Cliente seleccionado automáticamente:** {cliente_seleccionado_gm['cliente']}")
                        elif len(df_busqueda_gm) > 1:
                            st.markdown("**Seleccionar cliente para centrar el mapa:**")
                            nombres_clientes_gm = [
                                f"{row['cliente']} - {row['razon_social'][:50]}{'...' if len(row['razon_social']) > 50 else ''}" 
                                for idx, row in df_busqueda_gm.iterrows()
                            ]
                            
                            cliente_idx_gm = st.selectbox(
                                "Cliente:",
                                range(len(nombres_clientes_gm)),
                                format_func=lambda x: nombres_clientes_gm[x],
                                key="cliente_selector_gm"
                            )
                            
                            if cliente_idx_gm is not None:
                                cliente_seleccionado_gm = df_busqueda_gm.iloc[cliente_idx_gm].to_dict()
                        
                        # Usar resultados de búsqueda para el mapa
                        df_mostrar_gm = df_busqueda_gm.head(limite_resultados)
                    else:
                        st.warning("❌ No se encontraron clientes con ese término de búsqueda según los filtros aplicados")
                        df_mostrar_gm = pd.DataFrame()
                else:
                    st.warning("❌ No se encontraron clientes con ese término de búsqueda")
                    df_mostrar_gm = pd.DataFrame()
            else:
                # Si no hay búsqueda, limitar resultados
                df_mostrar_gm = df_mostrar_gm.head(limite_resultados)
            
            # Mostrar información del cliente seleccionado
            if cliente_seleccionado_gm:
                with st.expander("📊 Información del Cliente Seleccionado", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**🏷️ Código:** `{cliente_seleccionado_gm['identificador']}`")
                        st.markdown(f"**👤 Cliente:** `{cliente_seleccionado_gm['cliente']}`")
                        st.markdown(f"**🏢 Razón Social:** `{cliente_seleccionado_gm['razon_social']}`")
                        st.markdown(f"**📍 Domicilio:** `{cliente_seleccionado_gm['domicilio']}`")
                    
                    with col2:
                        estado_texto = "🔴 Anulado" if cliente_seleccionado_gm['anulado'] else "🟢 Activo"
                        st.markdown(f"**📊 Estado:** {estado_texto}")
                        
                        lat_sel = cliente_seleccionado_gm['coord_y']  # coord_y es latitud
                        lon_sel = cliente_seleccionado_gm['coord_x']  # coord_x es longitud
                        st.markdown(f"**🌐 Coordenadas:** `{lat_sel:.6f}, {lon_sel:.6f}`")  # Mostrar lat, lon
                    
                    # Enlaces de navegación
                    st.markdown("### 🚗 Navegación")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat_sel},{lon_sel}"
                        st.markdown(f"[📍 Google Maps]({google_maps_url})")
                    
                    with col2:
                        waze_url = f"https://waze.com/ul?ll={lat_sel},{lon_sel}&navigate=yes"
                        st.markdown(f"[🚗 Waze]({waze_url})")
                    
                    with col3:
                        direcciones_url = f"https://www.google.com/maps/dir/?api=1&destination={lat_sel},{lon_sel}"
                        st.markdown(f"[🧭 Direcciones]({direcciones_url})")
                    
                    with col4:
                        if st.button("📋 Copiar Coords"):
                            st.code(f"{lat_sel},{lon_sel}")
            
            # Mostrar estadísticas del mapa
            if not df_mostrar_gm.empty:
                st.subheader("🗺️ Mapa Interactivo")
                
                # Métricas
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Marcadores en mapa", len(df_mostrar_gm))
                with col2:
                    activos_gm = len(df_mostrar_gm[df_mostrar_gm['anulado'] == False])
                    st.metric("Activos", activos_gm)
                with col3:
                    anulados_gm = len(df_mostrar_gm[df_mostrar_gm['anulado'] == True])
                    st.metric("Anulados", anulados_gm)
                with col4:
                    if cliente_seleccionado_gm:
                        st.metric("Cliente seleccionado", "1")
                    else:
                        st.metric("Cliente seleccionado", "0")
                
                # Crear y mostrar el mapa de Google
                google_map_html = crear_google_map_html(df_mostrar_gm, cliente_seleccionado_gm, google_api_key)
                
                # Mostrar leyenda
                st.markdown("""
                **Leyenda del mapa:**
                - 🟢 Cliente activo  
                - 🔴 Cliente anulado  
                - 🔵 Cliente seleccionado (azul)
                
                💡 **Haz clic en los marcadores** para ver información detallada y enlaces de navegación.
                """)
                
                # Mostrar el mapa HTML
                st.components.v1.html(google_map_html, height=520)
                
                # Información adicional
                if termino_busqueda_gm:
                    st.info(f"🔍 Mostrando resultados para: '{termino_busqueda_gm}'")
                else:
                    st.info(f"📍 Mostrando los primeros {len(df_mostrar_gm)} clientes (de {len(df_clientes_gm)} totales)")
            
            else:
                if termino_busqueda_gm:
                    st.warning("❌ No se encontraron clientes que coincidan con la búsqueda")
                else:
                    st.info("""
                    💡 **Usa el buscador en la barra lateral** para encontrar clientes específicos.
                    
                    Puedes buscar por:
                    - **Nombre del cliente**
                    - **Razón social**
                    
                    El sistema priorizará coincidencias exactas al inicio del texto.
                    """)
        
        else:
            st.warning("""
            ❌ No hay clientes con coordenadas válidas para mostrar en Google Maps.
            
            **Para usar esta función necesitas:**
            - Clientes con coordenadas válidas (Coord X y Coord Y)
            - Las coordenadas no pueden ser 0 o estar vacías
            """)
    
    elif option == "Importar desde Excel":
        st.header("📊 Importar Clientes desde Excel")
        
        st.markdown("""
        **Instrucciones:**
        1. El archivo Excel debe contener las siguientes columnas: `Cliente`, `Razon social`, `Domicilio`, `Coord X`, `Coord Y`, `Identificador`, `Anulado`
        2. Se eliminará toda la información existente y se reemplazará con los nuevos datos
        3. Si alguna columna no existe en el archivo, se llenará con valores por defecto
        """)
        
        uploaded_file = st.file_uploader(
            "Selecciona un archivo Excel",
            type=['xlsx', 'xls'],
            help="Formatos soportados: .xlsx, .xls"
        )
        
        if uploaded_file is not None:
            st.success(f"Archivo cargado: {uploaded_file.name}")
            
            # Procesar archivo
            df_processed = process_excel_file(uploaded_file)
            
            if df_processed is not None:
                st.subheader("👀 Vista previa de los datos")
                st.dataframe(df_processed.head(10), use_container_width=True)
                
                st.info(f"Se procesarán {len(df_processed)} registros")
                
                # Confirmación antes de importar
                st.warning("⚠️ **ATENCIÓN**: Esta acción eliminará todos los clientes existentes y los reemplazará con los nuevos datos.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🗑️ Eliminar datos actuales", type="secondary"):
                        if db.clear_table():
                            st.success("✅ Datos eliminados correctamente")
                        else:
                            st.error("❌ Error eliminando datos")
                
                with col2:
                    if st.button("💾 Importar nuevos datos", type="primary"):
                        with st.spinner("Importando datos..."):
                            if db.insert_clientes(df_processed):
                                st.success(f"✅ Se importaron {len(df_processed)} clientes correctamente")
                                st.balloons()
                            else:
                                st.error("❌ Error importando datos")
    
    elif option == "Estadísticas":
        st.header("📈 Estadísticas de Clientes")
        
        df_clientes = db.get_clientes()
        if df_clientes is not None and not df_clientes.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Clientes", len(df_clientes))
            
            with col2:
                activos = len(df_clientes[df_clientes['anulado'] == False])
                st.metric("Clientes Activos", activos)
            
            with col3:
                anulados = len(df_clientes[df_clientes['anulado'] == True])
                st.metric("Clientes Anulados", anulados)
            
            with col4:
                con_coords = len(df_clientes.dropna(subset=['coord_x', 'coord_y']))
                st.metric("Con Coordenadas", con_coords)
            
            # Mostrar algunos datos adicionales
            st.subheader("📊 Información Detallada")
            
            # Mostrar distribución de estados
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Estado de clientes:**")
                activos = len(df_clientes[df_clientes['anulado'] == False])
                anulados = len(df_clientes[df_clientes['anulado'] == True])
                st.write(f"- Activos: {activos}")
                st.write(f"- Anulados: {anulados}")
            
            with col2:
                if 'fecha_creacion' in df_clientes.columns:
                    df_clientes['fecha_creacion'] = pd.to_datetime(df_clientes['fecha_creacion'])
                    ultimo_registro = df_clientes['fecha_creacion'].max()
                    st.write(f"**Último registro:** {ultimo_registro}")
                
                # Mostrar clientes con coordenadas
                con_coords = len(df_clientes.dropna(subset=['coord_x', 'coord_y']))
                st.write(f"**Con ubicación:** {con_coords} clientes")
        else:
            st.warning("No hay datos para mostrar estadísticas.")

if __name__ == "__main__":
    main()