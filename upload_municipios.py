import os
import json
import psycopg2
from psycopg2 import sql
from tqdm import tqdm

#Configuración de la base de datos
DB_CONFIG = {
    "dbname": "",
    "user": "",
    "password": "",
    "host": "localhost",
    "port": "5432"
}
# Configuración de la carpeta
INPUT_DIR = "output"  # Carpeta con los archivos GeoJSON

def conectar_postgres():
    """Establece conexión con PostgreSQL y devuelve el objeto de conexión"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"Error de conexión a PostgreSQL: {str(e)}")
        return None

def crear_tabla(conn):
    """Crea la tabla en PostGIS si no existe"""
    try:
        with conn.cursor() as cur:
            # Crear tabla principal de municipios
            cur.execute("""
                CREATE TABLE IF NOT EXISTS municipios (
                    "uuid" uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
                    ine VARCHAR(10) NOT NULL UNIQUE,
                    nombre VARCHAR(255),
                    geometria GEOMETRY(MultiPolygon, 4326)
                );
            """)
            
            # Crear índices
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_municipios_geom 
                ON municipios USING GIST (geometria);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_municipios_ine 
                ON municipios (ine);
            """)
            cur.execute ("""
delete from municipios;
                         """)
            conn.commit()
        return True
    except Exception as e:
        print(f"Error al crear tabla: {str(e)}")
        conn.rollback()
        return False

def extraer_propiedades(properties):
    """Extrae las propiedades relevantes del GeoJSON"""
    return {
        "ine_municipio": properties.get("ine:municipio", ""),
        "nombre": properties.get("name", ""),
        "nombre_es": properties.get("name:es", properties.get("alt_name:es", "")),
        "nombre_eu": properties.get("name:eu", ""),
        "poblacion": int(properties.get("population", 0)) if properties.get("population") else None,
        "wikidata": properties.get("wikidata", ""),
        "wikipedia": properties.get("wikipedia", properties.get("wikipedia:es", ""))
    }

def normalizar_geometria(geometry):
    """Convierte Polygon a MultiPolygon y asegura geometría válida"""
    if not geometry:
        return None
    
    # Si es Polygon, convertirlo a MultiPolygon
    if geometry["type"] == "Polygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [geometry["coordinates"]]
        }
    
    # Si ya es MultiPolygon, devolverlo directamente
    if geometry["type"] == "MultiPolygon":
        return geometry
    
    # Si es otro tipo, devolver None
    return None

def insertar_municipio(conn, ine_code, propiedades, geometry):
    """Inserta un municipio en la base de datos"""
    try:
        with conn.cursor() as cur:
            # Convertir geometría a texto JSON
            geometry_json = json.dumps(geometry)
            
            # Insertar datos
            cur.execute(sql.SQL("""
                INSERT INTO municipios (
                    ine, nombre, geometria
                )
                VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            """), (
                ine_code,
                propiedades["nombre"],
                geometry_json
            ))
        return True
    except Exception as e:
        print(f"Error al insertar municipio {ine_code}: {str(e)}")
        return False

def procesar_archivo_geojson(conn, file_path):
    """Procesa e importa un archivo GeoJSON a PostgreSQL"""
    try:
        # Leer el archivo GeoJSON
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        # Verificar que sea una FeatureCollection con features
        if geojson_data.get("type") != "FeatureCollection" or not geojson_data.get("features"):
            print(f"Archivo no válido: {file_path}")
            return False
        
        # Procesar cada feature (normalmente solo hay uno por archivo)
        for feature in geojson_data["features"]:
            # Extraer propiedades relevantes
            props = extraer_propiedades(feature.get("properties", {}))
            
            # Obtener y normalizar geometría
            geometry = feature.get("geometry")
            normalized_geometry = normalizar_geometria(geometry)
            
            if not normalized_geometry:
                print(f"Geometría no válida o faltante en {file_path}")
                continue
            
            # Extraer código INE del nombre del archivo
            ine_code = os.path.splitext(os.path.basename(file_path))[0]
            
            # Insertar en la base de datos
            if insertar_municipio(conn, ine_code, props, normalized_geometry):
                return True
        
        return False
    
    except Exception as e:
        print(f"Error procesando {file_path}: {str(e)}")
        return False

def importar_geojson_desde_carpeta():
    """Importa todos los archivos GeoJSON de una carpeta"""
    # Conectar a PostgreSQL
    conn = conectar_postgres()
    if not conn:
        return
    
    # Crear tabla si no existe
    if not crear_tabla(conn):
        conn.close()
        return
    
    # Obtener lista de archivos GeoJSON
    archivos = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".geojson")]
    
    if not archivos:
        print("No se encontraron archivos GeoJSON en la carpeta")
        conn.close()
        return
    
    # Contadores para estadísticas
    exitos = 0
    fallos = 0
    
    # Procesar cada archivo
    for archivo in tqdm(archivos, desc="Importando municipios"):
        file_path = os.path.join(INPUT_DIR, archivo)
        
        # Procesar el archivo
        if procesar_archivo_geojson(conn, file_path):
            conn.commit()
            exitos += 1
            print(f"✅ Importado: {archivo}")
        else:
            conn.rollback()
            print(f"❌ Falló: {archivo}")
            fallos += 1
            break
    
    # Optimizar la base de datos después de importar
    try:
        print("Optimizando base de datos...")
        with conn.cursor() as cur:
            cur.execute("VACUUM ANALYZE municipios;")
        conn.commit()
    except Exception as e:
        print(f"Error al optimizar base de datos: {str(e)}")
    
    conn.close()
    print(f"\n✅ Proceso completado. Éxitos: {exitos}, ❌ Fallos: {fallos}")

if __name__ == "__main__":
    importar_geojson_desde_carpeta()