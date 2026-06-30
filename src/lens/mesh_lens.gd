class_name MeshLens
extends Lens

## Lens for `mesh` payloads. Three sources, all rendered in the holographic aesthetic (LP-006):
##   1. payload.ref      → a real glTF/scene (res:// PackedScene or external .glb via GLTFDocument),
##                         normalized to a unit size, materials overridden with the holo shader.
##   2. shape revolve/tube → procedural CAD geometry via ProcMesh (bell nozzle, chamber, plumbing).
##   3. shape box|cylinder|… → Godot primitives (placeholders / simple parts).
## Domain math (e.g. a bell profile) lives in the ingestor; this lens only renders what the IR declares.

const _TARGET_SIZE := 2.5    ## referenced models are scaled to fit this longest-axis size


func payload_type() -> String:
	return "mesh"


func render(entity: LoupeIR.Entity, ctx: Lens.Context) -> Node3D:
	var spec: Dictionary = entity.payload.data if entity.payload.data is Dictionary else {}
	var color := _color(spec.get("color"), Color(0.30, 0.75, 1.0))
	var glow := float(spec.get("glow", 1.4))

	if entity.payload.ref != "":
		return _render_ref(entity.payload.ref, ctx, color, glow)

	var root := Node3D.new()
	root.name = "mesh_visual"
	var mi := MeshInstance3D.new()
	mi.mesh = _build_mesh(spec)
	mi.material_override = ctx.holo_material(color, glow)
	root.add_child(mi)
	return root


func _build_mesh(spec: Dictionary) -> Mesh:
	var shape := String(spec.get("shape", "box"))
	match shape:
		"revolve":
			return ProcMesh.revolve(spec.get("profile", []), int(spec.get("segments", 48)))
		"tube":
			return ProcMesh.tube(spec.get("path", []), float(spec.get("radius", 0.08)), int(spec.get("sides", 12)))
		_:
			return _build_primitive(shape, _vec3(spec.get("size"), Vector3.ONE))


func _build_primitive(shape: String, size: Vector3) -> Mesh:
	match shape:
		"sphere":
			var s := SphereMesh.new()
			s.radius = size.x * 0.5
			s.height = size.x
			return s
		"cylinder":
			var c := CylinderMesh.new()
			c.top_radius = size.x * 0.5
			c.bottom_radius = size.x * 0.5
			c.height = size.y
			return c
		"cone":
			var c := CylinderMesh.new()
			c.top_radius = 0.0
			c.bottom_radius = size.x * 0.5
			c.height = size.y
			return c
		"capsule":
			var c := CapsuleMesh.new()
			c.radius = size.x * 0.5
			c.height = max(size.y, size.x)
			return c
		"torus":
			var t := TorusMesh.new()
			t.inner_radius = size.x * 0.35
			t.outer_radius = size.x * 0.5
			return t
		_:
			var b := BoxMesh.new()
			b.size = size
			return b


## Load a real model and bring it into the holographic look. Supports project assets (res://, imported
## as PackedScene) and external glTF files (loaded at runtime via GLTFDocument — the path a real ingestor
## emits). Falls back to a marker if the model can't be loaded so the entity is still present/explodable.
func _render_ref(ref: String, ctx: Lens.Context, color: Color, glow: float) -> Node3D:
	var root := Node3D.new()
	root.name = "mesh_ref"
	var inst := _instantiate_ref(ref)
	if inst == null:
		push_warning("MeshLens: could not load ref '%s'" % ref)
		var mi := MeshInstance3D.new()
		var s := SphereMesh.new()
		s.radius = 0.2
		mi.mesh = s
		mi.material_override = ctx.holo_material(Color(1.0, 0.4, 0.4), 1.5)
		root.add_child(mi)
		return root
	root.add_child(inst)
	_apply_holo_recursive(inst, ctx, color, glow)
	if inst is Node3D:
		_normalize(inst)
	return root


func _instantiate_ref(ref: String) -> Node:
	if ref.begins_with("res://"):
		var res := load(ref)
		if res is PackedScene:
			return (res as PackedScene).instantiate()
		if res is Mesh:
			var mi := MeshInstance3D.new()
			mi.mesh = res
			return mi
		return null
	# External file (absolute or user://): runtime glTF import, no editor reimport needed.
	if ref.ends_with(".glb") or ref.ends_with(".gltf"):
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		if doc.append_from_file(ref, state) == OK:
			return doc.generate_scene(state)
	return null


func _apply_holo_recursive(node: Node, ctx: Lens.Context, color: Color, glow: float) -> void:
	if node is MeshInstance3D:
		(node as MeshInstance3D).material_override = ctx.holo_material(color, glow)
	for child in node.get_children():
		_apply_holo_recursive(child, ctx, color, glow)


## Scale + recenter an arbitrary model so any source (cm/m, off-origin) fits the scene consistently.
func _normalize(node: Node3D) -> void:
	var aabb := _aabb_of(node, Transform3D.IDENTITY)
	if aabb.size == Vector3.ZERO:
		return
	var longest := maxf(aabb.size.x, maxf(aabb.size.y, aabb.size.z))
	if longest <= 0.0001:
		return
	var s := _TARGET_SIZE / longest
	node.scale = Vector3(s, s, s)
	node.position = -aabb.get_center() * s


func _aabb_of(node: Node, xform: Transform3D) -> AABB:
	var result := AABB()
	var has := false
	var local := xform
	if node is Node3D:
		local = xform * (node as Node3D).transform
	if node is MeshInstance3D and (node as MeshInstance3D).mesh != null:
		var box: AABB = (node as MeshInstance3D).mesh.get_aabb()
		result = local * box
		has = true
	for child in node.get_children():
		var child_aabb := _aabb_of(child, local)
		if child_aabb.size != Vector3.ZERO:
			result = result.merge(child_aabb) if has else child_aabb
			has = true
	return result


func _vec3(v: Variant, fallback: Vector3) -> Vector3:
	if v is Array and v.size() == 3:
		return Vector3(float(v[0]), float(v[1]), float(v[2]))
	return fallback


func _color(v: Variant, fallback: Color) -> Color:
	if v is Array and v.size() >= 3:
		return Color(float(v[0]), float(v[1]), float(v[2]))
	return fallback
