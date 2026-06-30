class_name LODController
extends RefCounted

## Semantic zoom (R1, v0 slice): camera distance → an "active band". Deeper entities (higher `lod_band`)
## reveal as you zoom in; they hide as you pull back. This is what makes drilling across scales feel
## continuous. v0 controls visibility by band; content-tier swapping (overview→detail→deep) is a v2
## refinement noted in architecture.md.

var _last_band: int = -1


## thresholds: distances (ascending) at which the next-deeper band becomes visible as you get closer.
func active_band(distance: float, policy: LoupeIR.LODPolicy) -> int:
	var band := 0
	for t in policy.distance_thresholds:
		if distance < t:
			band += 1
	return clampi(band, 0, max(policy.bands - 1, 0))


## Returns the active band (so callers can react to changes, e.g. for HUD).
func update(entity_nodes: Array, camera: Camera3D, policy: LoupeIR.LODPolicy, focus: Vector3 = Vector3.ZERO) -> int:
	if camera == null:
		return _last_band
	var distance := camera.global_position.distance_to(focus)
	var band := active_band(distance, policy)
	if band != _last_band:
		for n in entity_nodes:
			if n is EntityNode:
				n.visible = n.lod_band <= band
		_last_band = band
	return band
