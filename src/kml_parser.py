import geopandas as gpd
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, MultiPolygon


def parse_custom_kml(kml_path: str) -> gpd.GeoDataFrame:
    """
    Legge il file KML dei quartieri e restituisce un GeoDataFrame con ID_QUART, DENOM e geometry.
    """
    tree = ET.parse(kml_path)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    records = []
    for placemark in root.findall('.//kml:Placemark', ns):
        # Estrae ID_QUART e DENOM dai metadati KML[cite: 1]
        id_quart, denom = None, None
        for data in placemark.findall('.//kml:ExtendedData/kml:Data', ns):
            if data.attrib.get('name') == 'ID_QUART':
                val = data.find('kml:value', ns)
                id_quart = val.text if val is not None else None
            elif data.attrib.get('name') == 'DENOM':
                val = data.find('kml:value', ns)
                denom = val.text if val is not None else None

        # Estrae le coordinate dei poligoni geometrici
        polygons = []
        for poly in placemark.findall('.//kml:Polygon', ns):
            coords_elem = poly.find('.//kml:outerBoundaryIs//kml:coordinates', ns)
            if coords_elem is not None and coords_elem.text:
                coords_text = coords_elem.text.strip()
                coords = [tuple(map(float, c.split(',')[:2])) for c in coords_text.split()]
                if len(coords) >= 3:
                    polygons.append(Polygon(coords))

        if polygons:
            geom = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
            records.append({
                'ID_QUART': str(id_quart),
                'DENOM': denom,
                'geometry': geom
            })

    return gpd.GeoDataFrame(records, crs="EPSG:4326")