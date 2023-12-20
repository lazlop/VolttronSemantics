# This application adjusts the maximum and minimum comfort bands to exapand the range during a DR event
# It then runs the shifting logic 

# %%

config = {
    'TSetMax': [
        16, 16, 16, 16, 16, 16,
        21, 21, 21, 21, 21, 21,
        21, 21, 21, 21, 21, 21,
        16, 16, 16, 16, 16, 16,
    ],
    'TSetMin': [
        16, 16, 16, 16, 16, 16,
        21, 21, 21, 21, 21, 21,
        21, 21, 21, 21, 21, 21,
        16, 16, 16, 16, 16, 16,
    ],
    'Event_Schedule': [
        0, 0, 0, 0, 0, 0,
        1, 1, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0,
    ],
    'TSetMax_event': 22,
    'TSetMin_event': 19,
}   

def adjust_schedule(TSetMax, TSetMin, Event_Schedule, TSetMax_event, TSetMin_event):
    """
    Widens comfort band by the event values when there is an event scheduled
    """
    new_TSetMax = []
    new_TSetMin = []
    for i, val in enumerate(Event_Schedule):
        if val == 1:
            new_TSetMax.append(TSetMax_event)
            new_TSetMin.append(TSetMin_event)
        else:
            new_TSetMax.append(TSetMax[i])
            new_TSetMin.append(TSetMin[i])
    
    return new_TSetMax, new_TSetMin

def main(TSetMax, TSetMin, Event_Schedule, TSetMax_event, TSetMin_event):
    """
    Runs application
    Takes parameters for all functions and calls them in sequence
    """
    new_TSetMax, new_TSetMin = adjust_schedule(TSetMax, TSetMin, Event_Schedule, TSetMax_event, TSetMin_event)

    return new_TSetMax, new_TSetMin

# %%

res = main(TSetMax= config['TSetMax'], 
     TSetMin= config['TSetMin'], 
     Event_Schedule= config['Event_Schedule'],
     TSetMax_event= config['TSetMax_event'], 
     TSetMin_event= config['TSetMin_event'])

print(res[0])
print(res[1])

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

res_dict = query_model('test-model.ttl')
display(res_dict)    

