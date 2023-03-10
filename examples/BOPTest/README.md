# Simulating BACnet Building

This tests the workflow of generating a brick model from configurations that would be retrieved from a BACnet scan. For this 'simulated' workflow, files were generated from the BACnet proxy interface to BOPTest. 

BOPTest: https://github.com/ibpsa/project1-boptest

BACnet Interface/Simulated Digital Twin: https://github.com/gtfierro/simulated-digital-twin

Paper describing BOPTest, Brick, and BACnet: https://home.gtf.fyi/papers/fierro2022simulated.pdf

# Using OpenRefine

OpenRefine was used to infer brick point types from the bacnet.csv file. OpenRefine is used to reinterpret the names of the data points. At this time, the process is largely manual. Adding new mappings to the reconciliation API or using other tools (like plaster) can take care of this. 

Tutorial: https://www.youtube.com/watch?v=LKcXMvrxXzE&ab_channel=GabeFierro
reconciliation API: https://github.com/BrickSchema/reconciliation-api

# Future Development

Other tools such as scrabble and plaster automatically create brick models from unstructured BIM metadata. This may be used in the future to directly generate a brick model, point tags, and bacnet.csv

Plastering: https://github.com/plastering/plastering