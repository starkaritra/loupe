class_name LoupeIR
extends RefCounted

## Typed in-memory representation of a `loupe-ir/v1` document.
## Inner classes are referenced as `LoupeIR.Entity`, `LoupeIR.Document`, etc.
## Parsing/validation lives in `IRLoader`; these are pure typed data holders.

const VERSION := "loupe-ir/v1"

const PAYLOAD_TYPES := [
	"none", "mesh", "text", "signal", "image", "equation", "table", "point_cloud", "graph", "matrix",
	"volume", "attention", "conv"
]


class Provenance:
	extends RefCounted
	var source: String = ""
	var hash: String = ""
	var generated_at: String = ""
	var generator: String = ""

	static func from_dict(d: Dictionary) -> Provenance:
		var p := Provenance.new()
		p.source = String(d.get("source", ""))
		p.hash = String(d.get("hash", ""))
		p.generated_at = String(d.get("generated_at", ""))
		p.generator = String(d.get("generator", ""))
		return p


class Payload:
	extends RefCounted
	var type: String = "none"
	var has_data: bool = false
	var data: Variant = null
	var ref: String = ""

	static func from_dict(d: Dictionary) -> Payload:
		var p := Payload.new()
		p.type = String(d.get("type", "none"))
		if d.has("data"):
			p.has_data = true
			p.data = d["data"]
		p.ref = String(d.get("ref", ""))
		return p


class Placement:
	extends RefCounted
	var pos := Vector3.ZERO
	var rot := Vector3.ZERO          ## euler degrees
	var scale := Vector3.ONE

	static func _vec3(v: Variant, fallback: Vector3) -> Vector3:
		if v is Array and v.size() == 3:
			return Vector3(float(v[0]), float(v[1]), float(v[2]))
		return fallback

	static func from_dict(d: Dictionary) -> Placement:
		var p := Placement.new()
		p.pos = _vec3(d.get("pos"), Vector3.ZERO)
		p.rot = _vec3(d.get("rot"), Vector3.ZERO)
		p.scale = _vec3(d.get("scale"), Vector3.ONE)
		return p


class Entity:
	extends RefCounted
	var id: String = ""
	var label: String = ""
	var kind: String = ""
	var parent: String = ""           ## "" means root / no parent
	var placement: Placement = null   ## null → auto-layout
	var lod_band: int = 0
	var payload: Payload = null
	var content_tiers: Dictionary = {}  ## { overview, detail, deep }
	var provenance: Provenance = null

	func tier(name: String) -> String:
		return String(content_tiers.get(name, ""))

	static func from_dict(d: Dictionary) -> Entity:
		var e := Entity.new()
		e.id = String(d.get("id", ""))
		e.label = String(d.get("label", ""))
		e.kind = String(d.get("kind", ""))
		var par: Variant = d.get("parent")
		e.parent = "" if par == null else String(par)
		var place: Variant = d.get("placement")
		e.placement = LoupeIR.Placement.from_dict(place) if place is Dictionary else null
		e.lod_band = int(d.get("lod_band", 0))
		var pl: Variant = d.get("payload")
		e.payload = LoupeIR.Payload.from_dict(pl) if pl is Dictionary else LoupeIR.Payload.new()
		var ct: Variant = d.get("content_tiers")
		e.content_tiers = ct if ct is Dictionary else {}
		var prov: Variant = d.get("provenance")
		e.provenance = LoupeIR.Provenance.from_dict(prov) if prov is Dictionary else null
		return e


class Relation:
	extends RefCounted
	var from: String = ""
	var to: String = ""
	var kind: String = ""

	static func from_dict(d: Dictionary) -> Relation:
		var r := Relation.new()
		r.from = String(d.get("from", ""))
		r.to = String(d.get("to", ""))
		r.kind = String(d.get("kind", ""))
		return r


class LODPolicy:
	extends RefCounted
	var bands: int = 3
	var distance_thresholds: Array[float] = []

	static func from_dict(d: Dictionary) -> LODPolicy:
		var p := LODPolicy.new()
		p.bands = int(d.get("bands", 3))
		var dt: Variant = d.get("distance_thresholds")
		if dt is Array:
			for v in dt:
				p.distance_thresholds.append(float(v))
		return p


class Document:
	extends RefCounted
	var version: String = ""
	var root: String = ""
	var entities: Array[Entity] = []
	var relations: Array[Relation] = []
	var lod_policy: LODPolicy = null
	var provenance: Provenance = null

	var _by_id: Dictionary = {}        ## id → Entity
	var _children: Dictionary = {}     ## parent id → Array[Entity]

	func index() -> void:
		_by_id.clear()
		_children.clear()
		for e in entities:
			_by_id[e.id] = e
		for e in entities:
			if e.parent != "":
				if not _children.has(e.parent):
					_children[e.parent] = [] as Array
				_children[e.parent].append(e)

	func get_entity(id: String) -> Entity:
		return _by_id.get(id)

	func children_of(id: String) -> Array:
		return _children.get(id, [] as Array)

	func root_entity() -> Entity:
		return get_entity(root)
