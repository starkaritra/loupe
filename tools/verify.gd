extends SceneTree

## Dev smoke: loads both sample IR files through IRLoader and asserts structural integrity, so the IR
## pipeline is verifiable headless without rendering. Run:
##   godot --headless --path <project> --script res://tools/verify.gd

const SAMPLES := [
	"res://ir/samples/rocket_engine.loupe.json",
	"res://ir/samples/paper.loupe.json",
	"res://ir/samples/transformer.loupe.json",
	"res://ir/samples/arxiv_paper.loupe.json",
	"res://ir/samples/protein.loupe.json",
	"res://ir/samples/github_repo.loupe.json",
	"res://ir/samples/matrix_demo.loupe.json",
	"res://ir/samples/model_attention.loupe.json",
	"res://ir/samples/alexnet.loupe.json",
	"res://ir/samples/lstm.loupe.json",
	"res://ir/samples/stable_diffusion.loupe.json",
	"res://ir/samples/mamba.loupe.json",
]


func _initialize() -> void:
	var failures := 0
	var paths := SAMPLES.duplicate()
	var cf := FileAccess.open("res://ir/samples/gen/catalog.json", FileAccess.READ)
	if cf != null:
		var d: Variant = JSON.parse_string(cf.get_as_text())
		if d is Array:
			for entry in d:
				if entry is Dictionary and entry.has("path"):
					paths.append(String(entry["path"]))
	for path in paths:
		var r := IRLoader.load_from_file(path)
		if not r.ok:
			printerr("FAIL  %s  ->  %s" % [path, r.error])
			failures += 1
			continue
		var doc := r.doc
		var ok := doc.root_entity() != null and doc.provenance.hash != ""
		var children_root := doc.children_of(doc.root).size()
		var visuals := _render_all(doc)
		print("OK    %s  entities=%d  root_children=%d  visuals=%d  sha=%s…" % [
			path.get_file(), doc.entities.size(), children_root, visuals, doc.provenance.hash.substr(0, 12)
		])
		if not ok or visuals != doc.entities.size():
			failures += 1
	print("RESULT  %s" % ("PASS" if failures == 0 else "FAIL (%d)" % failures))
	quit(failures)


## Render every entity through the lens registry headless — exercises each lens' GDScript so a compile/
## runtime error in a lens (e.g. untyped-array indexing) fails verification instead of only the live app.
func _render_all(doc: LoupeIR.Document) -> int:
	var registry := LensRegistry.new()
	var ctx := Lens.Context.new()
	var built := 0
	for e in doc.entities:
		var lens := registry.lens_for(e.payload.type)
		var visual := lens.render(e, ctx)
		if visual != null:
			built += 1
			visual.free()
	return built
