# Copy of bestest_air/con_shed_TsetHea_CooZon.py

# %%
import rdflib

g = rdflib.Graph()
g.parse("bestest_air.ttl")

query = """
SELECT DISTINCT ?zone ?TZonPoint ?TSetHeaZonPoint ?TSetCooZonPoint
WHERE {
    ?zone a brick:Zone ;
    brick:hasPoint ?TZon, ?TsetZon, ?TSetHeaZon, ?TSetCooZon .
    
    ?TZon a brick:Zone_Air_Temperature_Sensor ;
        ref:hasExternalReference/volttron:topic-name ?TZonPoint  .

    ?TSetHeaZon a brick:Zone_Air_Heating_Temperature_Setpoint ;
        ref:hasExternalReference/volttron:topic-name ?TSetHeaZonPoint  .

    ?TSetCooZon a brick:Zone_Air_Cooling_Temperature_Setpoint ;
        ref:hasExternalReference/volttron:topic-name ?TSetCooZonPoint  .

}"""

# %%
# Get data points to instantiate control points per zone
qres = g.query(query)

zone = []
zone_name = []
TZonPoint = []
TSetHeaZonPoint = []
TSetCooZonPoint = []

for row in qres:
    zone.append (str(row.zone))
    zone_name.append(str(row.zone[14:-5]))
    TZonPoint.append (str(row.TZonPoint))
    TSetHeaZonPoint.append (str(row.TSetHeaZonPoint))
    TSetCooZonPoint.append (str(row.TSetCooZonPoint))

    # Print points from query
    print(f"{row.zone} {row.TZonPoint} {row.TSetHeaZonPoint} {row.TSetCooZonPoint}")

# %%
# Obtain only the name of the zone
print ("zone_names",zone_name)  

# %%
# Print points from query (optional) 
print(TZonPoint)
for x in range(len(qres)):
    #print ("zone",zone[x])
    print ("TZonPoint",TZonPoint[x])
    print ("TSetHeaZonPoint",TSetHeaZonPoint[x])
    print ("TSetCooZonPoint",TSetCooZonPoint[x])
    print ("next zone")





# %% 
# Test control algorithm
class con_shed_TsetHea_CooZon(object):
    
    def __init__(self, price_threshold = 0.045):

        '''Constructor.

        Parameters
        ----------            
            
        Price_threshold : float
            price threshold to enable DR event.


        '''
    
        self.price_threshold = price_threshold
    
    def compute_control(self, y, f, step):
        '''Compute the control input from the measurement.
    
        Parameters
        ----------
        y : dict
            Contains the current values of the measurements.
            {:}

        f : dict
            Contains the current values of the forecasts.
            {:}

        step : int
            Contains the current step value.
            {:}

        Returns
        -------
        u : dict
            Defines the control input to be used for the next step.
            { : }
    
        '''
        # Temperature drift rate allowed under ASHRAE Standard 55 according to time period
        if step <= 900:         # <= 15 min
            TSet_adj = 2#1.11
        elif step <= 1800:      # <= 30 min
            TSet_adj = 1.67
        elif step <= 3600:      # <= 60 min
            TSet_adj = 2.22
        else:                   # > 120 min 
            TSet_adj = 2.77

        # Get Dynamic Electricty Price Forecast [Euro/kWh]
        priceSche = f['PriceElectricPowerDynamic'] 

        # Get comfort range (manually defined in BOPtest, and equal for all zones)
        LowerSetp = f['LowerSetp[1]']       
  
        # Adjust min values of comfort range during a DR event 
        # (as the Baseline TSetHeaZon = LowerSetp, DR logic "TSetHeaZon - TSet_adj > LowerSetp" would not work)
        # Use LowerSetp to follow same schedule (operating modes in the baseline not working based on the occ schedule)
        TSetMin = []
        for t in LowerSetp:
            if t == 12 + 273.15: #285.15
                TSetMin.append(12 + 273.15) # Lower setpoint for non-occupied periods
                # TSet_min 285.15 (same as LowerSetp because it's a hard limit from BOPTest)
            else: # 20 + 273.15 #293.15
                TSetMin.append(15 + 273.15) # Lower setpoint for occupied periods
                # TSet_min 288.15 (lower that LowerSetp to allow DR logic)
  
        u = {}
        # Iterate over each zone
          
        for zone in range(len(qres)):
              
              # Get zone air temperature heating setpoint per zone
              TSetHeaZon = (y[TSetHeaZonPoint[zone]]) 
              TSetHeaZon_name = ' '.join([TSetHeaZonPoint[zone]])

              # Get zone air temperature cooling setpoint per zone
              #TSetCooZon = (y[TSetCooZonPoint[zone]]) 
              #TSetCooZon_name = ' '.join([TSetCooZonPoint[zone]])

              # Get zone operative temperature per zone
              TZon = (y[TZonPoint[zone]])

              for i in range(25):
              
                # Test runaway condition
                if TZon < TSetMin[i] or TSetMin[i] == 12 + 273.15:
                    # Compute baseline control - for heating (release DR shed control)
                    #print(TZon, "<", TSetmin[i], "or", TSetmin[i], "= 285.15" )
                    print("TZon < TSetmin or TSetmin = 285.15" )
                    u [TSetHeaZon_name[:-1] + 'activate'] = 0 
                    

                # Verify DR event
                elif priceSche[i] > self.price_threshold:
                    print("price > threshold")
                    #print(priceSche[i], ">", self.price_threshold)
                    #print("TSetHeaZon",TSetHeaZon) 
                    #print("LowerSetp", LowerSetp[i]) 
                                            
                    # Compute DR shed control (only for heating)
                    if TSetHeaZon - TSet_adj > TSetMin[i]:
                        offset = TSet_adj 
                        
                    else:
                        offset = 0 
                        
                    new_TsetZon =  TSetHeaZon - offset
                    u [TSetHeaZon_name] = new_TsetZon
                    u [TSetHeaZon_name[:-1]+ 'activate'] = 1
                    #print("new_TsetZon",new_TsetZon) 

                    
                else:
                    # Compute baseline control (release DR shed control)
                    print("price < threshold")   
                    #print("TZonHeaSet",TSetHeaZon)          
                    #print("LowerSetp", LowerSetp[i])
                    u [TSetHeaZon_name[:-1] + 'activate'] = 0 

        return u
            

# %%