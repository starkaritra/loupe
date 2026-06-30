class_name LensRegistry
extends RefCounted

## Maps `payload.type` → a Lens (LP-002, R2 — the reuse engine). The Stage asks the registry which lens
## draws an entity. Registering a new payload type is the *only* thing needed to support a new domain's
## visuals — the shell is untouched. Lenses: `mesh` + `text` + `graph` + `matrix`; a fallback handles
## containers/unknowns.

var _lenses: Dictionary = {}        ## type:String → Lens
var _fallback: Lens = null


func _init() -> void:
	_fallback = DefaultLens.new()
	register(MeshLens.new())
	register(StructureTextLens.new())
	register(GraphLens.new())
	register(MatrixLens.new())
	register(AttentionLens.new())
	register(EquationLens.new())
	register(ConvLens.new())


func register(lens: Lens) -> void:
	_lenses[lens.payload_type()] = lens


func lens_for(type: String) -> Lens:
	return _lenses.get(type, _fallback)


## Fallback for container entities (`none`) and any unregistered payload type: a small glowing marker so
## structure is still visible and explodable even without a specialized renderer.
class DefaultLens:
	extends Lens

	func payload_type() -> String:
		return "none"

	func render(entity: LoupeIR.Entity, ctx: Lens.Context) -> Node3D:
		var root := Node3D.new()
		root.name = "marker_visual"
		var mi := MeshInstance3D.new()
		var s := SphereMesh.new()
		s.radius = 0.12
		s.height = 0.24
		s.radial_segments = 12
		s.rings = 6
		mi.mesh = s
		mi.material_override = ctx.holo_material(Color(0.6, 0.7, 0.9), 1.0)
		root.add_child(mi)
		if entity.label != "":
			var l := ctx.make_label(entity.label, 0.1)
			l.position = Vector3(0, 0.22, 0)
			root.add_child(l)
		return root
