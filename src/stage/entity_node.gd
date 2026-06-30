class_name EntityNode
extends Node3D

## One IR entity instantiated in the scene tree. Holds its collapsed "home" position and a radial
## explode offset; the explode controller springs `position` between home and exploded. Children are
## other EntityNodes (the containment hierarchy IS the Godot scene tree — a natural fit, LP-004).

var entity: LoupeIR.Entity = null
var home_pos: Vector3 = Vector3.ZERO
var explode_offset: Vector3 = Vector3.ZERO
var lod_band: int = 0
var visual: Node3D = null


func setup(e: LoupeIR.Entity, home: Vector3, offset: Vector3) -> void:
	entity = e
	home_pos = home
	explode_offset = offset
	lod_band = e.lod_band
	position = home_pos
	name = e.id
	_add_pick_body()


## A click target so the whole part can be picked even when its visual is sparse (lines/labels). The body
## is on layer 2 so the inspect raycast hits parts, not other geometry. Stage maps the body back to id.
func _add_pick_body() -> void:
	var body := StaticBody3D.new()
	body.collision_layer = 2
	body.collision_mask = 0
	body.input_ray_pickable = true
	body.set_meta("entity_id", entity.id)
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(0.9, 0.9, 0.9)
	col.shape = box
	body.add_child(col)
	add_child(body)
	_body = body


var _body: StaticBody3D = null


func set_selected(on: bool) -> void:
	if visual == null:
		return
	for m in _materials(visual):
		m.set_shader_parameter("selected", 1.0 if on else 0.0)


## Flow pulse: a glow level (0..1) passing through the part — the active part brightens and pops in size,
## so attention naturally lands on whatever the data is "in" right now.
func set_flow(level: float) -> void:
	if _base_scale == Vector3.ZERO:
		_base_scale = scale
	scale = _base_scale * (1.0 + 0.25 * level)
	for m in _materials(visual):
		m.set_shader_parameter("selected", level)


var _base_scale: Vector3 = Vector3.ZERO


## Engine-cutaway visibility: 0 = hidden (a casing outside our focus), 1 = ghost (faint context, e.g. the
## parent shell), 2 = solid (the focus + its internals). Dims emission/alpha so externals fade as you dive.
func set_focus_state(state: int, z_offset: float = 0.0) -> void:
	visible = state != 0
	if _body != null:
		_body.collision_layer = 0 if state == 0 else 2
	position = home_pos + Vector3(0, 0, z_offset)   # parents recede along Z; children sit at the front
	if visual != null:
		visual.visible = state == 2          # only the focus's children show; focus+ancestors stay clear
	var glow := 0.5 if state == 1 else 1.4
	var alpha := 0.06 if state == 1 else 0.14
	for m in _materials(visual):
		m.set_shader_parameter("glow", glow)
		m.set_shader_parameter("base_alpha", alpha)


func _materials(n: Node, out: Array = []) -> Array:
	if n is MeshInstance3D and (n as MeshInstance3D).material_override is ShaderMaterial:
		out.append((n as MeshInstance3D).material_override)
	for c in n.get_children():
		_materials(c, out)
	return out


func apply_explode(factor: float) -> void:
	position = home_pos + explode_offset * factor
