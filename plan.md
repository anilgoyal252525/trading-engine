# DESIGN PATTERN

[x] Async Event-Driven Pub/Sub queue based

# SYSTEM DESIGN STRUCTURE 

[X] main
    1. load the whole system 

[x] broker
    1. data provider 
    2. sends to the data manager

[x] data_manager
    1. manage data subscription from strategies
    2. send data to event bus 
    3. use candle builder, to build the candles 

[X] centeral hub 
    1. takes the data from data_manager 
    2. routes to strategies

[X] strategies
    1. consume the data from hub
    2. strategy manager = wires the strategies

[X] order_placement_manager
    1. place orders
    2. modify order

# Error Handling checks

[x] placing order
[x] modifing order
[x] saving csv after trade completion
[x] data laging from broker feeds
[x] data manager not building correct data