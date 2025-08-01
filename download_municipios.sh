#!/bin/bash

# Script para descargar geometrías de municipios españoles en GeoJSON
# Requiere: curl, osmtogeojson, y un archivo municipios_ine.txt con códigos INE
#
#
# Verificar dependencias
mkdir output
command -v osmtogeojson >/dev/null 2>&1 || {
    echo "Error: osmtogeojson no está instalado. Instala con:"
    echo "npm install -g osmtogeojson"
    exit 1
}

# Leer archivo con códigos municipales
input_file="municipios_ine_1.txt"

if [[ ! -f "$input_file" ]]; then
    echo "Error: No se encuentra el archivo $input_file"
    exit 1
fi

# Contador para mostrar progreso
total=$(wc -l < "$input_file")
count=0

# Procesar cada municipio
while IFS= read -r ine_code
do
    # Eliminar espacios y saltos de línea
    ine_code=$(echo "$ine_code" | tr -d '[:space:]')
    
    # Saltar líneas vacías
    if [[ -z "$ine_code" ]]; then
        continue
    fi
    
    # Incrementar contador
    ((count++))
    
    # Crear nombre de archivo de salida
    output_file="output/${ine_code}.geojson"
    
    # Mostrar progreso
    echo "Procesando municipio $ine_code ($count/$total)..."
    
    # Ejecutar consulta y conversión
    curl -s -X POST -d @- https://overpass-api.de/api/interpreter <<EOF | osmtogeojson > "$output_file"
[out:json][timeout:300];
area["ISO3166-1"="ES"][admin_level=2]->.espana;
relation[boundary="administrative"][admin_level="8"]["ine:municipio"="${ine_code}"](area.espana);
out geom;
EOF

    # Esperar 1 segundo entre consultas por cortesía a la API
    sleep 1
    
    # Verificar si se creó el archivo
    if [[ ! -s "$output_file" ]]; then
        echo "  ¡Advertencia! No se encontró geometría para $ine_code"
    else
        echo "  Guardado en $output_file"
    fi

done < "$input_file"

echo "Proceso completado. Se procesaron $count municipios."