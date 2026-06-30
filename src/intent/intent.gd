class_name Intent
extends RefCounted

## The fixed, device-agnostic vocabulary the Stage reacts to (LP-007). Input adapters translate raw
## device input into these; the Stage never sees a mouse. Adding XR later = a new adapter emitting the
## same kinds — never a rewrite.

enum Kind {
	GRAB,       ## begin direct manipulation
	RELEASE,    ## end direct manipulation
	ROTATE,     ## arcball-style orientation delta (args: delta: Vector2)
	PAN,        ## translate view (args: delta: Vector2)
	ZOOM,       ## semantic zoom across scales (args: amount: float)
	EXPLODE,    ## push explode factor toward 1 (args: amount: float)
	COLLAPSE,   ## pull explode factor toward 0 (args: amount: float)
	INSPECT,    ## focus/drill into an entity (args: entity_id: String)
	SELECT,     ## highlight/pick (args: entity_id: String)
}

static func kind_name(k: int) -> String:
	return Kind.keys()[k] if k >= 0 and k < Kind.size() else "UNKNOWN"
