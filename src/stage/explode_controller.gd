class_name ExplodeController
extends RefCounted

## Spring-loaded explode (LP-008): a single factor in [0,1] eased toward a target each frame, then
## applied recursively to every EntityNode. Device-agnostic — driven only by EXPLODE/COLLAPSE intents.

var factor: float = 0.0
var target: float = 0.0
@export var stiffness: float = 7.0


func nudge(amount: float) -> void:
	target = clampf(target + amount, 0.0, 1.0)


func set_target(t: float) -> void:
	target = clampf(t, 0.0, 1.0)


## Ease factor toward target and apply to the whole subtree. Returns the current factor.
func step(delta: float, root: Node) -> float:
	factor = lerpf(factor, target, clampf(delta * stiffness, 0.0, 1.0))
	_apply(root)
	return factor


func _apply(node: Node) -> void:
	for child in node.get_children():
		if child is EntityNode:
			child.apply_explode(factor)
		_apply(child)
