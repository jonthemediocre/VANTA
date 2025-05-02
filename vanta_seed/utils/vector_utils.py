from typing import List, Tuple

def round_position(position: List[float], resolution: int) -> Tuple[float, ...]:
    """Rounds a position vector components to a given resolution (number of decimal places)."""
    if not isinstance(position, list):
        # Handle potential error or return a default if needed
        # For now, let's assume it should be a list
        return tuple()
    try:
        return tuple(round(coord, resolution) for coord in position)
    except TypeError:
        # Handle cases where position might not contain numbers
        return tuple() 