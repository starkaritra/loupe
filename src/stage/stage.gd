class_name Stage
extends Node3D

## The SHELL core (LP-002): builds the Godot scene tree from an IR document and navigates it like opening
## an engine — you FOCUS one part, its outer casing + siblings fade away, and its internals reveal. Reacts
## ONLY to intents (LP-007), never raw input. Domain-agnostic; payload visuals come from the lens registry.

@export var spin_decay: float = 4.0          ## inertia falloff after release (LP-008)

var doc: LoupeIR.Document = null
var registry: LensRegistry = null
var ctx: Lens.Context = null

var _entity_nodes: Array[EntityNode] = []
var _by_id: Dictionary = {}                   ## id → EntityNode
var _flows: Node3D = null
var _camera: Camera3D = null
var _grabbed: bool = false
var _spin_velocity: Vector2 = Vector2.ZERO
var _selected: EntityNode = null
var _focus_id: String = ""                    ## the part we are currently inside
var _pivot: Vector3 = Vector3.ZERO            ## world point the current level rotates about
var _flow_order: Array[EntityNode] = []       ## focus children ordered input→output for the flow pulse
var _flow_t: float = 0.0
var _flow_i: int = -1
var _eqn: Sprite3D = null
var _eqn_index: Dictionary = {}

signal inspected(entity: LoupeIR.Entity)
signal focus_changed(world_pos: Vector3, radius: float)


func _ready() -> void:
	IntentBus.intent.connect(_on_intent)


func set_camera(cam: Camera3D) -> void:
	_camera = cam


func build(document: LoupeIR.Document) -> void:
	doc = document
	registry = LensRegistry.new()
	ctx = Lens.Context.new()
	_entity_nodes.clear()
	_by_id.clear()
	for c in get_children():
		c.queue_free()
	var root := doc.root_entity()
	if root != null:
		_build_entity(root, self, 0, 1)
	_flows = Node3D.new()
	_flows.name = "flows"
	add_child(_flows)
	_set_focus(doc.root)


func _build_entity(entity: LoupeIR.Entity, parent_node: Node, index: int, sibling_count: int) -> void:
	var node := EntityNode.new()
	var home := Vector3.ZERO
	if entity.placement != null:
		home = entity.placement.pos
		node.scale = entity.placement.scale
		node.rotation = entity.placement.rot * (PI / 180.0)
	else:
		home = _auto_layout(index, sibling_count)
	node.setup(entity, home, Vector3.ZERO)
	var lens := registry.lens_for(entity.payload.type)
	var visual := lens.render(entity, ctx)
	node.visual = visual
	node.add_child(visual)
	parent_node.add_child(node)
	_entity_nodes.append(node)
	_by_id[entity.id] = node
	var children := doc.children_of(entity.id)
	for i in children.size():
		_build_entity(children[i], node, i, children.size())


func _auto_layout(index: int, sibling_count: int) -> Vector3:
	if sibling_count <= 1:
		return Vector3(0, 0, 0)
	var radius := 1.2 + 0.22 * float(sibling_count)
	var angle := (float(index) / float(sibling_count)) * TAU
	return Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)


## Engine-dive: the focused part + its direct children are solid; the focus's parent stays a faint ghost
## (cutaway context), everything else fades right out. Grandchildren hide until you dive again — this kills
## clutter and gives the "you're inside it" feel (cover/transmission gone, valves/crankshaft shown).
func _set_focus(id: String) -> void:
	_focus_id = id
	var focus := doc.get_entity(id)
	var parent_id := focus.parent if focus != null else ""
	var kids := doc.children_of(id)
	var has_kids := kids.size() > 0
	var ancestors := {}
	var p := parent_id
	while p != "":
		ancestors[p] = true
		var pe := doc.get_entity(p)
		p = pe.parent if pe != null else ""
	for n in _entity_nodes:
		var e := n.entity
		var state := 0
		var z := 0.0
		if e.parent == id:
			state = 2
		elif e.id == id:
			state = 3; z = 8.0                       # focus card hidden; its children + flow take the front
		elif e.id == parent_id:
			state = 1; z = -8.0                      # parent recedes far behind; seen when you rotate
		elif ancestors.has(e.id):
			state = 1; z = -16.0
		n.set_focus_state(state, z)
		if focus != null:
			inspected.emit(focus)
		_rebuild_flows()
	position = Vector3.ZERO
	if has_kids:
		_frame_children(kids)
	else:
		var fn: EntityNode = _by_id.get(id)
		if fn != null:
			focus_changed.emit(fn.global_position, 2.6)


## Frame the camera on the bounding sphere of the focus's actual children, so whatever we dive into is
## always centered and filling the view (kills the "empty level" — the layout never has to be guessed).
func _frame_children(kids: Array) -> void:
	var c := Vector3.ZERO
	for k in kids:
		c += k.placement.pos if k.placement != null else Vector3.ZERO
	c /= kids.size()
	var r := 2.0
	for k in kids:
		var p: Vector3 = k.placement.pos if k.placement != null else Vector3.ZERO
		r = maxf(r, c.distance_to(p) + 1.6)
	var fn: EntityNode = _by_id.get(_focus_id)
	var base: Vector3 = fn.global_position if fn != null else Vector3.ZERO
	_pivot = base + c
	focus_changed.emit(_pivot, r)


## Flow without clutter: light the focus's children one-by-one in relation order, so a glow travels
## through the actual parts (input→output) instead of drawing connector lines.
func _rebuild_flows() -> void:
	_flow_order.clear()
	var seq := _order_by_flow(_focus_id)
	for e in seq:
		var n: EntityNode = _by_id.get(e.id)
		if n != null:
			_flow_order.append(n)
	_flow_t = 0.0
	_flow_i = -1
	if _eqn == null:
		_eqn = Sprite3D.new(); _eqn.billboard = BaseMaterial3D.BILLBOARD_ENABLED; _eqn.shaded = false; _eqn.pixel_size = 0.0016
		add_child(_eqn)
	_eqn.visible = _flow_order.size() >= 2


## Topologically order the focus's children along their flow relations (falls back to placement order).
func _order_by_flow(id: String) -> Array:
	var kids := doc.children_of(id)
	if kids.size() <= 1:
		return kids
	var ids := {}
	for k in kids: ids[k.id] = true
	var nxt := {}; var indeg := {}
	for k in kids: indeg[k.id] = 0
	for r in doc.relations:
		if ids.has(r.from) and ids.has(r.to):
			nxt[r.from] = r.to; indeg[r.to] = int(indeg.get(r.to, 0)) + 1
	var start := ""
	for k in kids:
		if int(indeg[k.id]) == 0: start = k.id; break
	var out: Array = []; var seen := {}; var cur := start
	while cur != "" and not seen.has(cur):
		seen[cur] = true; out.append(doc.get_entity(cur)); cur = String(nxt.get(cur, ""))
	if out.size() == kids.size(): return out
	return kids


func _on_intent(kind: int, args: Dictionary) -> void:
	match kind:
		Intent.Kind.ROTATE:
			_apply_rotation(args.get("delta", Vector2.ZERO))
		Intent.Kind.PAN:
			var d: Vector2 = args.get("delta", Vector2.ZERO)
			position += Vector3(d.x, -d.y, 0.0)
		Intent.Kind.INSPECT:
			_pick_at(args.get("screen", Vector2.ZERO))
		Intent.Kind.COLLAPSE:
			_ascend()
		Intent.Kind.EXPLODE:
			_descend()
		Intent.Kind.GRAB:
			_grabbed = true
			_spin_velocity = Vector2.ZERO
		Intent.Kind.RELEASE:
			_grabbed = false


## Dive: click a part → inspect it; if it has internals, descend into it. Click a leaf → just inspect.
func _pick_at(screen: Vector2) -> void:
	if _camera == null:
		return
	var origin := _camera.project_ray_origin(screen)
	var dir := _camera.project_ray_normal(screen)
	var q := PhysicsRayQueryParameters3D.create(origin, origin + dir * 100.0, 2)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return
	var body: Object = hit.get("collider")
	if body == null or not body.has_meta("entity_id"):
		return
	var eid := String(body.get_meta("entity_id"))
	var node: EntityNode = _by_id.get(eid)
	if node == null:
		return
	if _selected != null:
		_selected.set_selected(false)
	_selected = node
	node.set_selected(true)
	inspected.emit(node.entity)
	if doc.children_of(eid).size() > 0:
		if eid == _focus_id:
			_descend()
		else:
			_set_focus(eid)


func _ascend() -> void:
	var focus := doc.get_entity(_focus_id)
	if focus != null and focus.parent != "":
		_set_focus(focus.parent)


## Reset orientation/pan and re-frame the current level — a clean "recenter" the user can rebind to.
func recenter() -> void:
	global_transform = Transform3D.IDENTITY
	_spin_velocity = Vector2.ZERO
	if _focus_id != "":
		_set_focus(_focus_id)


## E dives into the selected part (or the first child of the current focus) so keyboard alone navigates.
func _descend() -> void:
	if _selected != null and _selected.entity.id != _focus_id and doc.children_of(_selected.entity.id).size() > 0:
		_set_focus(_selected.entity.id)
		return
	for k in doc.children_of(_focus_id):
		if doc.children_of(k.id).size() > 0:
			_set_focus(k.id)
			return


func _apply_rotation(delta: Vector2) -> void:
	_rotate_about(Vector3.UP, delta.x)
	_rotate_about(Vector3.RIGHT, delta.y)
	_spin_velocity = delta


## Rotate the whole model about the focus centroid (not the stage origin) so every level spins centered.
func _rotate_about(axis: Vector3, ang: float) -> void:
	var t := Transform3D.IDENTITY.rotated(axis, ang)
	global_transform = Transform3D(t.basis, _pivot - t.basis * _pivot) * global_transform


func _process(delta: float) -> void:
	if not _grabbed and _spin_velocity.length() > 0.0001:
		_rotate_about(Vector3.UP, _spin_velocity.x)
		_rotate_about(Vector3.RIGHT, _spin_velocity.y)
		_spin_velocity = _spin_velocity.lerp(Vector2.ZERO, clampf(delta * spin_decay, 0.0, 1.0))
	_drive_flow(delta)


## Step a spotlight through the parts: the active component comes into focus (bright + larger) while the
## equation below swaps to its formula — data "arriving" at each part, no moving ball. L1 and L2 alike.
func _drive_flow(delta: float) -> void:
	var n := _flow_order.size()
	if n < 2:
		return
	_flow_t = fmod(_flow_t + delta * 0.35, float(n))         # ~3s dwell per part
	var i := int(_flow_t)
	for j in n:
		_flow_order[j].set_flow(1.0 if j == i else 0.0)


func _eqn_tex(e: LoupeIR.Entity) -> Texture2D:
	var spec: Dictionary = e.payload.data if e.payload.data is Dictionary else {}
	var key := String(spec.get("eqn", ""))
	if key == "": return null
	if _eqn_index.is_empty():
		var f := FileAccess.open("res://assets/eqn/index.json", FileAccess.READ)
		if f != null:
			var d: Variant = JSON.parse_string(f.get_as_text())
			if d is Dictionary: _eqn_index = d
	var file := String(_eqn_index.get(key, ""))
	return load("res://assets/eqn/" + file) as Texture2D if file != "" else null
