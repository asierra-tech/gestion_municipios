# Gestion municipios

Este proyecto utiliza las capacidades de OpenStreetMap (OSM) para realizar consultas sobre límites administrativos y obtener datos geoespaciales relacionados 
con municipios específicos.

## Descripción

El código proporcionado utiliza un servicio de OpenStreetMap:

1. **[Overpass Turbo](https://overpass-turbo.eu/):**
  - Permite realizar consultas complejas sobre datos geoespaciales de OpenStreetMap mediante su API.
  - En este caso, el código busca límites administrativos de nivel 8 (municipios) en España filtrando por el código `ine:municipio`, que corresponde a municipios específicos en el sistema de codificación español.

## Ejecución

1. Descargar municipios
  Ejecutar, sh download_municipios.sh, ese script descargara en output las geometrias de los municipios especificados, mediante el INE en el archivo municipios_ine.txt
2. Subir los municipios
  Ejecutar el script de pyhton upload_municipios, este actualiza la tabla municipios en la base de datos



### Consulta con Overpass Turbo

El siguiente script realiza una consulta para obtener los límites administrativos de un municipio específico en España:

https://overpass-turbo.eu/# 


[out:json][timeout:300];
area["ISO3166-1"="ES"][admin_level=2]->.espana;
(
  relation[boundary="administrative"]
    [admin_level="8"]
    ["ine:municipio"="28130"]
    (area.espana);
);
out geom;


https://nominatim.openstreetmap.org/reverse?lat=36.1691454&lon=-5.369541&format=json