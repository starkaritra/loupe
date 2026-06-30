extends Node3D

## App entry point: builds the holographic world (env/glow/fog, light, camera), wires the desktop input
## adapter → IntentBus → Stage, and loads sample IR files. Switching between two opposite-domain samples
## with the SAME build (keys 1 and 2) is the v0 universality gate (handoff §8).

const SAMPLES := {
	KEY_1: "res://ir/samples/rocket_engine.loupe.json",
	KEY_2: "res://ir/samples/paper.loupe.json",
	KEY_3: "res://ir/samples/transformer.loupe.json",
	KEY_4: "res://ir/samples/arxiv_paper.loupe.json",
	KEY_5: "res://ir/samples/protein.loupe.json",
	KEY_6: "res://ir/samples/github_repo.loupe.json",
	KEY_7: "res://ir/samples/matrix_demo.loupe.json",
	KEY_8: "res://ir/samples/model_attention.loupe.json",
	KEY_9: "res://ir/samples/alexnet.loupe.json",
	KEY_0: "res://ir/samples/lstm.loupe.json",
	KEY_F: "res://ir/samples/stable_diffusion.loupe.json",
	KEY_G: "res://ir/samples/mamba.loupe.json",
	KEY_H: "res://ir/samples/gen/resnet.loupe.json",
	KEY_J: "res://ir/samples/gen/vit.loupe.json",
}

@export var cam_min_distance: float = 1.2
@export var cam_max_distance: float = 16.0

var _stage: Stage = null
var _camera: Camera3D = null
var _hud: Label = null
var _panel: RichTextLabel = null
var _panel_bg: ColorRect = null
var _last_entity: LoupeIR.Entity = null
var _catalog: Array = []
var _catalog_idx: int = -1
var _focus: Vector3 = Vector3(0.0, -0.6, 0.0)
var _cam_dir: Vector3 = Vector3(0.0, 0.22, 1.0).normalized()
var _cam_distance: float = 8.5
var _shoot_path: String = ""
var _shoot_frames: int = 0


func _process(_delta: float) -> void:
	_shoot_tick()


func _shoot_tick() -> void:
	if _shoot_path == "":
		return
	_shoot_frames -= 1
	if _shoot_frames <= 0:
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png(_shoot_path)
		_shoot_path = ""
		get_tree().quit()


func _ready() -> void:
	_build_environment()
	_build_camera()
	_build_stage()
	_build_input()
	_load_catalog()
	_build_hud()
	IntentBus.intent.connect(_on_intent)
	var sample_idx := OS.get_environment("LOUPE_SAMPLE")
	var keymap := {"1": KEY_1, "2": KEY_2, "3": KEY_3, "4": KEY_4, "5": KEY_5, "6": KEY_6, "7": KEY_7, "8": KEY_8, "9": KEY_9, "0": KEY_0, "F": KEY_F, "G": KEY_G, "H": KEY_H, "J": KEY_J}
	var key: int = keymap.get(sample_idx, KEY_1)
	_load_sample(SAMPLES[key])
	var f := OS.get_environment("LOUPE_FOCUS")
	if f != "":
		_stage._set_focus(f)
	var shoot := OS.get_environment("LOUPE_SHOOT")
	if shoot != "":
		_shoot_path = shoot
		_shoot_frames = 40


func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.02, 0.03, 0.05)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.1, 0.16, 0.24)
	env.ambient_light_energy = 0.4
	env.fog_enabled = true
	env.fog_light_color = Color(0.03, 0.06, 0.1)
	env.fog_density = 0.015
	env.glow_enabled = true
	env.glow_intensity = 0.45
	env.glow_bloom = 0.1
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50, -35, 0)
	light.light_energy = 0.6
	add_child(light)


func _build_camera() -> void:
	_camera = Camera3D.new()
	add_child(_camera)
	_update_camera()


func _build_stage() -> void:
	_stage = Stage.new()
	add_child(_stage)
	_stage.set_camera(_camera)
	_stage.inspected.connect(_on_inspected)
	_stage.focus_changed.connect(_on_focus_changed)


func _build_input() -> void:
	var adapter := DesktopInputAdapter.new()
	add_child(adapter)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	# Title + metadata (top-left).
	_hud = Label.new()
	_hud.position = Vector2(16, 12)
	_hud.add_theme_color_override("font_color", Color(0.7, 0.9, 1.0))
	layer.add_child(_hud)
	# Per-arm dropdown menus (top-left, below title).
	_build_arm_menus(layer)
	# Legend (bottom-left).
	var legend := Label.new()
	legend.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	legend.offset_left = 16; legend.offset_top = -86
	legend.add_theme_color_override("font_color", Color(0.55, 0.72, 0.86))
	legend.text = "click/E dive in · Q back out · R recenter · C panel · [ ] cycle adapter models\nright-drag move · drag rotate · wheel zoom\nflow = lit part is active; equation below it updates"
	layer.add_child(legend)
	_build_panel(layer)


## A dropdown per "arm": each arm groups related visualizations. The Model Architecture arm is populated
## from the adapter catalog (so new templates appear automatically); other arms list their sample IRs.
func _build_arm_menus(layer: CanvasLayer) -> void:
	var bar := HBoxContainer.new()
	bar.position = Vector2(16, 60)
	bar.add_theme_constant_override("separation", 10)
	layer.add_child(bar)

	var arms := [
		{"name": "Model Architecture", "items": _model_arch_items()},
		{"name": "Mechanical", "items": [["Rocket Engine", "res://ir/samples/rocket_engine.loupe.json"]]},
		{"name": "Documents", "items": [["Paper", "res://ir/samples/paper.loupe.json"],
			["arXiv Paper", "res://ir/samples/arxiv_paper.loupe.json"]]},
		{"name": "Biology", "items": [["Protein (PDB)", "res://ir/samples/protein.loupe.json"]]},
		{"name": "Code", "items": [["GitHub Repo", "res://ir/samples/github_repo.loupe.json"]]},
		{"name": "Data", "items": [["Matrices", "res://ir/samples/matrix_demo.loupe.json"]]},
	]
	for arm in arms:
		var ob := OptionButton.new()
		ob.add_item(String(arm["name"]))                 # header (index 0)
		ob.set_item_disabled(0, true)
		for it in arm["items"]:
			ob.add_item(String(it[0]))
			ob.set_item_metadata(ob.item_count - 1, String(it[1]))
		ob.select(0)
		ob.item_selected.connect(func(idx: int) -> void:
			var p: Variant = ob.get_item_metadata(idx)
			if p is String and p != "":
				_focus = Vector3.ZERO; _cam_distance = 8.5; _update_camera()
				_load_sample(p)
				ob.select(0))
		bar.add_child(ob)


## Model-arm dropdown items, sourced from the adapter-generated catalog + the hand-authored exemplar.
func _model_arch_items() -> Array:
	var items: Array = [["Attention (exemplar)", "res://ir/samples/model_attention.loupe.json"]]
	for entry in _catalog:
		if entry is Dictionary:
			items.append([String(entry.get("label", entry.get("name", "?"))), String(entry.get("path", ""))])
	return items


## Right-side explanation panel: shows the clicked part's name + a description, deepening with zoom
## (overview → detail → deep mirrors the part's content_tiers). Hidden until something is inspected.
func _build_panel(layer: CanvasLayer) -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.03, 0.05, 0.09, 0.82)
	bg.anchor_left = 1.0; bg.anchor_right = 1.0; bg.anchor_bottom = 1.0
	bg.offset_left = -380; bg.offset_right = -16; bg.offset_top = 16; bg.offset_bottom = -16
	layer.add_child(bg)
	_panel_bg = bg
	_panel = RichTextLabel.new()
	_panel.bbcode_enabled = true
	_panel.fit_content = true
	_panel.add_theme_constant_override("margin_left", 16)
	_panel.add_theme_constant_override("margin_top", 14)
	_panel.anchor_left = 1.0; _panel.anchor_right = 1.0; _panel.anchor_bottom = 1.0
	_panel.offset_left = -380; _panel.offset_right = -16; _panel.offset_top = 16; _panel.offset_bottom = -16
	_panel.text = "[color=#8fd]Click a part to inspect.[/color]\nzoom in for deeper detail."
	layer.add_child(_panel)


func _on_focus_changed(world_pos: Vector3, radius: float) -> void:
	_focus = world_pos
	_cam_distance = clampf(radius * 1.35, cam_min_distance, cam_max_distance)
	_update_camera()


func _on_inspected(entity: LoupeIR.Entity) -> void:
	if _panel == null:
		return
	_last_entity = entity
	_render_panel()


## Build the panel as organized bullet points (overview · detail · deep), each clause its own line.
func _render_panel() -> void:
	if _last_entity == null:
		return
	var e := _last_entity
	var s := "[b][color=#bdf]%s[/color][/b]   [color=#6ab]%s[/color]\n" % [e.label, e.kind]
	for tier in ["overview", "detail", "deep"]:
		var t := e.tier(tier)
		if t == "":
			continue
		s += "\n[color=#7aa]%s[/color]\n" % tier
		for clause in t.split(";", false):
			var c := clause.strip_edges().trim_suffix(".")
			if c != "":
				s += "  • %s\n" % c
	_panel.text = s
	_panel_bg.visible = true
	_panel.visible = true


func _toggle_panel() -> void:
	var open := not _panel.visible
	_panel.visible = open
	_panel_bg.visible = open


func _load_sample(path: String) -> void:
	var result := IRLoader.load_from_file(path)
	if not result.ok:
		push_error("Loupe IR load failed: %s" % result.error)
		if _hud != null:
			_hud.text = "IR load failed:\n%s" % result.error
		return
	_stage.build(result.doc)
	_update_hud(path, result.doc)


func _update_hud(path: String, doc: LoupeIR.Document) -> void:
	if _hud == null:
		return
	var prov := doc.provenance
	_hud.text = "LOUPE — model architecture\n%s · %d entities · sha %s" % [path.get_file(), doc.entities.size(), prov.hash.substr(0, 8)]


func _on_intent(kind: int, args: Dictionary) -> void:
	if kind == Intent.Kind.ZOOM:
		_cam_distance = clampf(_cam_distance - float(args.get("amount", 0.0)), cam_min_distance, cam_max_distance)
		_update_camera()


func _update_camera() -> void:
	_camera.global_position = _focus + _cam_dir * _cam_distance
	_camera.look_at(_focus, Vector3.UP)


## The adapter-generated model catalog (tools/gen_models.py). [ and ] cycle through every model the
## universal adapter can emit, so new templates appear here with no engine changes.
func _load_catalog() -> void:
	var f := FileAccess.open("res://ir/samples/gen/catalog.json", FileAccess.READ)
	if f == null:
		return
	var d: Variant = JSON.parse_string(f.get_as_text())
	if d is Array:
		_catalog = d


func _cycle_catalog(step: int) -> void:
	if _catalog.is_empty():
		return
	_catalog_idx = wrapi(_catalog_idx + step, 0, _catalog.size())
	var entry: Dictionary = _catalog[_catalog_idx]
	_focus = Vector3.ZERO; _cam_distance = 8.5; _update_camera()
	_load_sample(String(entry.get("path", "")))


func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_C:
			_toggle_panel()
			return
		if event.keycode == KEY_R:
			_focus = Vector3.ZERO; _cam_distance = 8.5; _update_camera()
			_stage.recenter()
			return
		if event.keycode == KEY_BRACKETRIGHT:
			_cycle_catalog(1)
			return
		if event.keycode == KEY_BRACKETLEFT:
			_cycle_catalog(-1)
			return
		if SAMPLES.has(event.keycode):
			_load_sample(SAMPLES[event.keycode])
