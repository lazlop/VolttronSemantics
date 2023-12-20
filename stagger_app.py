# Only allow 2 HVAC units to operate at a given time. 
# Widen the deadband of all other units 
# Based on Delta T (primarily) between setpoint and time since unit has been activated, prioritize unit. 
# Do not overwrite 
# %%
#from typing_extensions import Protocol
from typing import Protocol
import rdflib
from collections import OrderedDict

# Class uses functions defined in the 'functions' module
class StaggerFunctions(Protocol):
    '''Contains the set of control functions needed for a Control Strategy.
    May differ by control strategy and interface. 
    Functions are pulled from controls.hvac.sequences.functions'''
        
    def order_units(self):
        ... 
    def get_setpoints(self):
        ...
    
# compute control will probably come from the 'strategies' module
class StaggerStrategy(Protocol):
    '''Class for a particular control strategy.
    control_functions is an instantiated object of type DRControlFunctions.
    compute_control will be pulled from library controls.hvac.sequences.strategies.
    A object of type ControlStrategy may be used by many different DRInterfaces.'''

    control_functions: StaggerFunctions
    
    def __init__(self, control_functions: StaggerFunctions):
        ...
    def main(self):
        ...
    def sparql_query(self):
        ...
       
def organize_units(unit_dict):
    """
    Takes dictionary of units, organizes them first by Deta T and based on inactive period 
    
    params
    --
    unit_dict: dict
    {unit_id: setpoint: val, temp: val, inactive_period: val}, unit_id2: {delta_t: val, inactive_period: val} }

    returns 
    ordered_dict: dict
    ordered dictionary of units from least delta t and time inactive to most delta_t and time inactive (i.e. later units are activated)
    
    """
    sorted_dict = sorted(unit_dict.items(), key=lambda x: (abs(x[1]['setpoint'] - x[1]['temp']), x[1]['inactive_period']), reverse = True)


    return OrderedDict(sorted_dict)

# %%
def deactivate_units(unit_dict, active_unit_count):
    """
    Take the orderd unit dict and return a new dictionary indicating 
    which units should be active and which should not be
    """
    active_units = {}
    i = 0

    for k in unit_dict.keys():
        is_active = i < active_unit_count
        active_units[k] = is_active
        i += 1
    
    return active_units

# %%
def set_setpoints_heat_and_cool(active_units, min_sp, max_sp):
    """
    The set setpoints function is different based on the configuration of the building
    This is especially true of setpoint configurations

    If it has cooling and heating setpoint then we can widen the deadband by writing them independently
    If it has a mode, the mode can be written and the relevant setpoint
    This can be done with different "set setpoints" functions, or with adapter functions that 
    work on its output

    Can be used as on-off controls if desired. However setpoints are a more readily available point

    """    
    setpoint_df = {}
    for k, v, in active_units.items():        
        if v:
            setpoint_df[k]['cooling_setpoint'] = max_sp 
            setpoint_df[k]['heating_setpoint'] = min_sp 
        else:
            setpoint_df[k]['cooling_setpoint'] = None
            setpoint_df[k]['heating_setpoint'] = None

def set_setpoints_setpoint_and_mode(active_units, unit_dict, min_sp, max_sp, mode):
    """
    Adjusts the output of the set_setpoints function for units with a single setpoint and a defined mode
    requires knowledge of the current heating mode (if it's heating or cooling)
    """
    setpoint_df = {}
    for k, v, in active_units.items():        
        if v:
            if mode == 'heat':
                setpoint_df[k]['setpoint'] = min_sp
            if mode == 'cool':
                setpoint_df[k]['setpoint'] = max_sp
            if mode == 'auto':
                print('mode must be writable for this')
                setpoint_df[k]['setpoint'] = min_sp
                setpoint_df[k]['mode'] = 'heat'

            
        else:
            setpoint_df[k]['setpoint'] = None

def main():
    pass
    """
    runs application
    """
    organize_units
    deactivate_units
    set_setpoints_heat_and_cool


# %%
import rdflib
def query_model(filepath):
    """
    runs queries for multiple possible configurations of the model
    if both possible configurations work it'll choose deadband widening 
    it will also let the user know which queries passed. 
    """
    g = rdflib.Graph()
    g.parse(filepath, format = 'ttl')

    queries = {}

    queries['heating_and_cooling_setpoint'] = """
    SELECT DISTINCT *
    WHERE {
        ?zone a s223:DomainSpace ;
            s223:hasProperty ?TZon, ?TsetZonHeat, ?TsetZonCool .

        ?TsetZonCool a app:Heating_Setpoint ;
            ref:hasExternalReference/bacnet:object-name ?TsetZonHeatPoint  .

        ?TsetZonHeat a app:Cooling_Setpoint ;
            ref:hasExternalReference/bacnet:object-name ?TsetZonCoolPoint  .

        ?TZon a app:Zone_Temperature ;
            ref:hasExternalReference/bacnet:object-name  ?TZonPoint  .
        
    }"""

    queries['setpoint_and_mode'] = """
    SELECT DISTINCT *
    WHERE {
        ?zone a s223:DomainSpace ;
            s223:hasProperty ?TZon, ?TsetZon, ?Mode .

        ?TZon a app:Single_Temperature_Setpoint ;
        ref:hasExternalReference/bacnet:object-name ?TsetZonPoint  .

        ?TZon a app:Cooling_Setpoint ;
        ref:hasExternalReference/bacnet:object-name ?TsetZonCoolPoint  .

        ?TsetZon a app:Zone_Temperature ;
        ref:hasExternalReference/bacnet:object-name  ?TZonPoint  .
        
    }"""

    results_dict = {}
    for k, query in queries.items():
        results = g.query(query)
        # only if results have rows add them to the results_dict
        if results:
            results_dict[k] = sparql_to_dict(results)

    return results_dict

def sparql_to_dict(results, key = 'zone'):
    """
    turns results into a dictionary of dictionaries. the key for the containing dictionary can be selected
    turning everything to strings cause it may be easier
    """
    result_dict = {}
    
    for row in results:
        var_names = [var for var in results.vars]
        # Create a dictionary with variable names as keys and corresponding values
        values_dict = {str(var): str(row[var]) for var in var_names[1:]}
        
        result_dict[str(row[key])] = values_dict

    return result_dict

# %%
#Testing 
res_dict = query_model('test-model.ttl')
display(res_dict)    



data = {
    'unit_id1': {'setpoint': 25, 'temp': 20, 'inactive_period': 10},
    'unit_id2': {'setpoint': 25, 'temp': 31, 'inactive_period': 8},
    'unit_id3': {'setpoint': 25, 'temp': 28, 'inactive_period': 5},
    'unit_id4': {'setpoint': 25, 'temp': 23, 'inactive_period': 7},
    'unit_id5': {'setpoint': 25, 'temp': 25, 'inactive_period': 12},
}

a = organize_units(data)
display(a)

print(deactivate_units(a, 2))