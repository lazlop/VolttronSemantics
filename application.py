# Copy of bestest_air/con_shed_TsetHea_CooZon.py

# %%
import rdflib

g = rdflib.Graph()
g.parse("building_model.ttl")

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

# %%
# Get data points to instantiate control points per zone
qres = g.query(query)

zone = []
zone_name = []
TZonPoint = []
TsetZonPoint = []

for row in qres:
    zone.append (str(row.zone))
    zone_name.append(str(row.zone[14:-5]))
    TZonPoint.append (str(row.TZonPoint))
    TsetZonPoint.append (str(row.TsetZonPoint))

    # Print points from query
    print(f"{row.zone} {row.TZonPoint} {row.TsetZonPoint}")

print(TZonPoint)

# %%
for x in range(len(equip)):
    print ("TempSensorPoint",TZonPoint[x])
    print ("TempSetPoint",TsetZonPoint[x])

# %%
# functions
def query_model(filepath):
    g = rdflib.Graph()
    g.parse(filepath)

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

def get_adj(step):
    if step <= 900:         # <= 15 min
        TSet_adj_original = 1.11
    elif step <= 1800:      # <= 30 min
        TSet_adj_original = 1.67
    elif step <= 3600:      # <= 60 min
        TSet_adj_original = 2.22
    else:                       # > 120 min 
        TSet_adj_original = 2.77
    return TSet_adj_original

def price_event (price_schedule, price_threshold_value):
    if isinstance(price_schedule, (list, tuple)):
        for price in price_schedule:
            if price > price_threshold_value:
                return True
            else: 
                # Release DR shed control (compute baseline control)
                enable_command = 0
                return enable_command
    else:
        if price_schedule > price_threshold_value:
            return True
        else:
            enable_command = 0
            return enable_command


def runaway_condition (TZon, TSetMin, TSetMax):
    if isinstance(TSetMin, (list, tuple)) and isinstance(TSetMax, (list, tuple)):
        for i in range(len(TSetMin)):
            if TZon < TSetMin[i] or TZon > TSetMax[i]:
                # Release DR shed control (compute baseline control)
                enable_command = 0
                return enable_command    
            else:
                return False

    else:
        if TZon < TSetMin or TZon > TSetMax:
            # Release DR shed control (compute baseline control)
            enable_command = 0
            return enable_command    
        else:
            return False

def shed_TsetZon (TsetZon, TSet_adj_current, TSetMin):
    # Compute DR shed control (only for heating) 
    if isinstance(TSetMin, (list, tuple)):   
        for i in range(len(TSetMin)):                      
            if TsetZon - TSet_adj_current > TSetMin [i]:
                offset = TSet_adj_current
                                    
            else:
                offset = 0 
                
            new_TsetZon =  TsetZon - offset
            enable_command = 1
            return new_TsetZon, enable_command
    else:
        if TsetZon - TSet_adj_current > TSetMin:
            offset = TSet_adj_current
                                    
        else:
            # Should this set to min rather than using 0 offset?
            offset = 0 
                
        new_TsetZon =  TsetZon - offset
        enable_command = 1
        return new_TsetZon, enable_command

# LP Addition
def preheat_TsetZon (TsetZon, TSet_adj_current, TSetMax):
    # Compute DR preheat control (only for heating) 
    if isinstance(TSetMax, (list, tuple)):   
        for i in range(len(TSetMin)):                      
            if TsetZon + TSet_adj_current < TSetMax [i]:
                offset = TSet_adj_current
                                    
            else:
                # offset = 0 
                offset = TSetMax - TsetZon
                
            new_TsetZon =  TsetZon + offset
            enable_command = 1
            return new_TsetZon, enable_command
    else:
        if TsetZon + TSet_adj_current < TSetMax:  
            offset = TSet_adj_current
                                    
        else:
            # Shouldln't this just set it to max or min then?
            # offset = 0 
            offset = TSetMax - TsetZon
                
        new_TsetZon =  TsetZon + offset
        enable_command = 1
        return new_TsetZon, enable_command

# %% 
query_model("building_model.ttl")

# %%
     
def get_setpoint(TZon, TsetZon, price, price_next_hour, step):
    """
    returning None if baseline control should be used
    returning shed adjustment if shed controls should be used
    """
    TSetMin = 16
    TSetMax = 21
    price_threshold_value = 0.25
    
    TSet_adj_current = get_adj(step)

    if runaway_condition(TZon, TSetMin, TSetMax):
        # Disable Controls
        return None
    
    if price_event(price, price_threshold_value):
        # Run Shed
        new_TsetZon = shed_TsetZon(TsetZon, TSet_adj_current, TSetMin)

        return new_TsetZon
    
    #testing price event for next hour 
    if price_event(price_next_hour, price_threshold_value):
        # Run Shed
        new_TsetZon = preheat_TsetZon(TsetZon, TSet_adj_current, TSetMax)

        return new_TsetZon

# %%
for i in [0, 900, 1800, 2700, 3600, 4500, 5400, 6300, 7200, 8100, 9000]:
    print(main(19, 21, 0.27, 0.27, i))

# %%
for i in [0, 900, 1800, 2700, 3600, 4500, 5400, 6300, 7200, 8100, 9000]:
    print(main(16, 16, 0.23, 0.27, i))

# %%

print(main(21, 21, 0.23, 0.23, 1800))
print(main(21, 21, 0.27, 0.27, 1800))
print(main(16, 16, 0.27, 0.27, 1800))
# %%
