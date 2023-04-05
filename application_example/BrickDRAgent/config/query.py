import rdflib

def sparql_query(graph_path, query_path):

    '''Query identifiers for control points per zone from the selected graph path.

        Parameters
        ----------            

        graph_path : str
            Contains the path to the graph directory.
        
        query_path : str
            Contains the path to the sparql query.

        Returns
        -------

        range_query : int
            Contains the length of the query results, ie the number of zones with sufficient points from the graph. 

        TZonPoint : str
            Contains the identifier for the temperature measurement point per zone. 

        TSetZonPoint : str
            Contains the identifier for the temperature setpoint per zone.

        TSetHeaZonPoint : str
            Contains the identifier for the heating temperature setpoint per zone. 

        TSetCooZonPoint : str
            Contains the identifier for the cooling temperature setpoint per zone. 

        TSetMinPoint : str
            Contains the identifier for the minimum temperature setpoint per zone.

        TSetMaxPoint : str
            Contains the identifier for the maximum temperature setpoint per zone.

    '''    

    # Query the identifiers for control points per zone    
    g = rdflib.Graph()
    g.parse(graph_path)
    with open(query_path) as f:
        query = f.read()
    qres = g.query(query)
    range_query = range(len(qres))

    # Create lists for the identifiers needed to instatiate the control points per zone
    TZonPoint = []
    TSetZonPoint = []
    TSetHeaZonPoint = []
    TSetCooZonPoint = []
    TSetMinPoint = []
    TSetMaxPoint  = []
    
    for row in qres:
        TZonPoint.append (str(row.TZonPoint))
        TSetZonPoint.append (str(row.TSetZonPoint))
        TSetHeaZonPoint.append (str(row.TSetHeaZonPoint))
        TSetCooZonPoint.append (str(row.TSetCooZonPoint))
        TSetMinPoint.append (str(row.TSetMinPoint))
        TSetMaxPoint .append (str(row.TSetMaxPoint ))

    return {
            'TZonPoint': TZonPoint, 
            'TSetZonPoint': TSetZonPoint, 
            'TSetHeaZonPoint': TSetHeaZonPoint, 
            'TSetCooZonPoint':TSetCooZonPoint
            }
 