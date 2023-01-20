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

# %%
# Print points from query (optional) 
print(TZonPoint)
for x in range(len(qres)):
    print ("TempSensorPoint",TZonPoint[x])
    print ("TempSetPoint",TsetZonPoint[x])

# %%
# Test control algorithm


class con_shed_TsetZon(object):

    def __init__(self, price_threshold = 0.25, step = 900):

        '''Constructor.
        Parameters
        ----------            
            
        price_threshold : float
            price threshold to enable DR event.
        step : float
            receives the current step from the simulation. Default value 900s.
        '''

        self.price_threshold = price_threshold
        self.step = step
    
    def get_adj_size(self):
        # Compute temperature drift rate allowed under ASHRAE Standard 55 
        # according to time period  
        if self.step <= 900:         # <= 15 min
            self.TSet_adj_current = 1.11
        elif self.step <= 1800:      # <= 30 min
            self.TSet_adj_current = 1.67
        elif self.step <= 3600:      # <= 60 min
           self.TSet_adj_current = 2.22
        else:                       # > 120 min 
            self.TSet_adj_current = 2.77

        # Temporary variable to account for ratcheting within the loop  
        return TSet_adj_current

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
               
        # Defines the control input to be used for the next step.
        u = {}

        # Iterate over each zone
        for zone in range(len(qres)):
            
            # Get comfort range 
            # Get zone operative temperature setpoint for heating per zone
            #(Boptest LowerSetp = "reaTSetHea_y")

            TSetMin = 20 #  (y[TSetMinPoint[zone]])
                        
            # Get zone operative temperature setpoint for cooling
            #(Boptest UpperSetp = "reaTSetCoo_y")
            TSetMax = 22 # (y[TSetMaxPoint[zone]]) 

            # Get zone operative temperature setpoint
            TsetZon = self.Tset_prev # (y[TsetZonPoint[zone]]) 
            #TsetZon_name = ' '.join([TsetZonPoint[zone]])

            # Get zone operative temperature
            TZon = self.get_ave_temp() # (y[TZonPoint[zone]]) 

            # Get Dynamic Electricity Price Forecast [Euro/kWh]
            price = self.price_schedule[self.hour] # f['PriceElectricPowerDynamic'] 
            price_next_hour = self.price_schedule[self.hour + 1]
                               
            # Test runaway condition
            if TZon < TSetMin or TZon > TSetMax:
                # Release DR shed control (compute baseline control)
                #u [TsetZon_name[:-1] + 'activate'] = 0 
                        
                # Disable ratcheting (if started)               
                # self.TSet_adj_current = self.TSet_adj_original
                
                self.write_baseline()
                self.dr_flag = False
                # When does this flag reset back to true?
            
            else:
                
                # Verify DR event
                if price > self.price_threshold:
                    
                    # Compute DR shed control (only for heating)                         
                    if TsetZon - self.TSet_adj_current > TSetMin:
                        offset = self.TSet_adj_current
                        
                        # Enable ratcheting
                        self.TSet_adj_current =  0.5                          
                        
                    else:
                        offset = 0 
                                            
                    new_TsetZon =  TsetZon - offset
                    u [TsetZon_name] = new_TsetZon
                    
                    self.write_dr_point()

                    # u [TsetZon_name[:-1]+ 'activate'] = 1
                    self.dr_flag = True  

                    return   

                elif price_next_hour > self.price_threshold: 


                    # Compute DR shed control (only for heating)                         
                    if TsetZon - self.TSet_adj_current > TSetMin:
                        offset = self.TSet_adj_current
                        
                        # Enable ratcheting
                        self.TSet_adj_current =  0.5                          
                        
                    else:
                        offset = 0 
                                            
                    new_TsetZon =  TsetZon - offset
                    u [TsetZon_name] = new_TsetZon
                    
                    self.write_dr_point()

                    # u [TsetZon_name[:-1]+ 'activate'] = 1
                    self.dr_flag = True  


                    
                else:
                    # Release DR shed control (compute baseline control)
                    # u [TsetZon_name[:-1] + 'activate'] = 0
                    # Disable ratcheting (if started)   
                    # self.TSet_adj_current = self.TSet_adj_original
                    self.dr_flag = False
                    self.write_baseline()
                                
        return u