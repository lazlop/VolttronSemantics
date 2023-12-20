# %%
from typing import Protocol
import rdflib
from dflexlibs.hvac.strategies.stra_zone_temp_shift_shed_price import (
    compute_control
)

from dflexlibs.hvac.protocols_zone_temp import (
    DRControlFunctions,
    DRControlStrategy,
    DRInterface
)
from dflexlibs.hvac.functions import (
    ashrae_TSet_adjust,
    new_comfort_range,
    runaway_condition,
    runaway_TsetHeaZon,
    runaway_TsetCooZon,
    shed_price_event,
    shed_TsetCooZon,
    shed_TsetHeaZon,
    shift_occ_price_event,
    shift_TsetCooZon,
    shift_TsetHeaZon
)
# %%
def null_runaway_condition(*args):
    '''Replacement for the runaway function if no runaway condition is used.
       Will return that there is no runaway condition.

        Parameters
        ----------            

        *args
            Accepts runaway condition inputs, though they are not used

        Returns
        -------

        False 

    '''    
    
    return False

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

    '''    

    # Query the identifiers for control points per zone
    return [None]     
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

    for row in qres:
        TZonPoint.append (str(row.TZonPoint))
        TSetZonPoint.append (str(row.TSetZonPoint))
        TSetHeaZonPoint.append (str(row.TSetHeaZonPoint))
        TSetCooZonPoint.append (str(row.TSetCooZonPoint))

    return range_query, TZonPoint, TSetZonPoint, TSetHeaZonPoint, TSetCooZonPoint

class VolttronShiftControlFunctions(DRControlFunctions):
    '''
    The control functions needed to run the shift strategy from the Volttron platform
    Functions are same as those needed for BOPTest, however runaway conditions were not used
    '''
    
    def __init__(self):
        self.runaway_condition = null_runaway_condition
        self.heat_runaway = null_runaway_condition
        self.cool_runaway = null_runaway_condition
        self.shift_occ_price_event = shift_occ_price_event
        self.shed_price_event = shed_price_event
        self.heat_shed = shed_TsetHeaZon
        self.cool_shed = shed_TsetCooZon
        self.cool_shift = shift_TsetCooZon
        self.heat_shift = shift_TsetHeaZon
        self.setpoint_adjustment = ashrae_TSet_adjust
        self.new_comfort_range = new_comfort_range

class VolttronStrategy(DRControlStrategy):
    # Not sure we really need these three separate classes, but it works for now
    
    def __init__(self, control_functions):
        self.control_functions = VolttronShiftControlFunctions
        self.compute_control = compute_control
