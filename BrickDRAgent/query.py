import rdflib

def query_model(filepath):
    g = rdflib.Graph()
    g.parse(filepath, format = 'ttl')

    equip = []
    TZonPoint = []
    TsetZonPoint = []

    query = """
    SELECT DISTINCT *
    WHERE {
        ?zone a brick:HVAC_Zone .
        ?equip brick:feeds ?zone ;
            a brick:FCU ;
            brick:hasPoint ?TZon, ?TsetZon .

        ?TZon a brick:Air_Temperature_Sensor ;
        ref:hasExternalReference/ref:hasTimeseriesId ?TZonPoint  .

        ?TsetZon a brick:Air_Temperature_Setpoint ;
        ref:hasExternalReference/ref:hasTimeseriesId ?TsetZonPoint  .
        
    }"""

    qres = g.query(query)
    for row in qres:
        equip.append(str(row.equip)) # renamed from zone
        # zone_name.append(str(row.zone[14:-5]))
        TZonPoint.append(str(row.TZonPoint))
        TsetZonPoint.append(str(row.TsetZonPoint))
    return TZonPoint, TsetZonPoint, equip