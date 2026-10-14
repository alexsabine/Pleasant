"""Optional derived index example: install h3 separately, no mandatory dependency.

The geometry stays in PostGIS; this index does not encode a child's location or
network travel time. The coordinate below is only an approximate public demo.
"""
try:
    import h3
except ImportError:
    print("Optional: python -m pip install h3  # after reviewing pinned version")
else:
    cell = h3.latlng_to_cell(41.755, -124.20, 8)
    print("Derived res-8 H3 index (not a map license or source of truth):", cell)
    print("Neighbour count:", len(h3.grid_disk(cell,1))-1)
