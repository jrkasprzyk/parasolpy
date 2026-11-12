# SOM (MAPS) Example

Script: `examples/08_som_maps_demo.py`

This example runs a MAPS-style workflow on 500 Colorado River Basin states of the world (SOWs), each a 30-year cumulative-supply trace bundled in `examples/data/crb_500_sow/`. It z-scores the traces, fits a 13 × 4 hexagonal SOM, assigns each SOW to a neuron, and layers SOW attributes onto the map. It then sweeps 30 map configurations and prints the non-dominated ones.

```bash
python examples/08_som_maps_demo.py
```

The script prints the map's quantization error, topographic error, and explained variance, followed by the non-dominated rows of the sweep.

Outputs:

- `examples/_output/som_layer_Median.png`: mean of each SOW's median Lees Ferry flow, per neuron
- `examples/_output/som_layer_demand.png`: mean demand per neuron
- `examples/_output/som_layer_InitCombinedStorage.png`: mean initial combined storage per neuron
- `examples/_output/som_layer_hits.png`: number of SOWs per neuron
- `examples/_output/som_node_traces.png`: member traces of each neuron over the full ensemble
- `examples/_output/som_sweep.csv`: all sweep configurations with their scores and the `eps_nd` label

The data are a 500-SOW subsample of the MAPS ensemble (Pernat, Kasprzyk, Zagona 2026). The example is a demo and does not reproduce the paper's figures: a differently trained map has different neurons.

See [Self-Organizing Maps](../user-guide/som.md) for details on the functions and for standalone recipes.
