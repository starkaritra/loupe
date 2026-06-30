class_name IRLoader
extends RefCounted

## Parses + validates a `loupe-ir/v1` JSON document into a typed `LoupeIR.Document`.
## Records/derives provenance (reproducibility bar): if the document omits a hash, we compute one over
## the raw bytes so every loaded artifact is traceable.

class Result:
	extends RefCounted
	var ok: bool = false
	var doc: LoupeIR.Document = null
	var error: String = ""

	static func fail(msg: String) -> Result:
		var r := Result.new()
		r.ok = false
		r.error = msg
		return r

	static func success(d: LoupeIR.Document) -> Result:
		var r := Result.new()
		r.ok = true
		r.doc = d
		return r


static func load_from_file(path: String) -> Result:
	if not FileAccess.file_exists(path):
		return Result.fail("IR file not found: %s" % path)
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return Result.fail("Cannot open IR file: %s (err %d)" % [path, FileAccess.get_open_error()])
	var raw := f.get_as_text()
	f.close()
	return parse(raw, path)


static func parse(raw: String, source_path: String = "") -> Result:
	var json := JSON.new()
	var err := json.parse(raw)
	if err != OK:
		return Result.fail("JSON parse error at line %d: %s" % [json.get_error_line(), json.get_error_message()])
	var data: Variant = json.data
	if not (data is Dictionary):
		return Result.fail("IR root must be a JSON object")

	var validation := _validate(data)
	if validation != "":
		return Result.fail(validation)

	var doc := LoupeIR.Document.new()
	doc.version = String(data.get("version", ""))
	doc.root = String(data.get("root", ""))

	for ed in data.get("entities", []):
		if ed is Dictionary:
			doc.entities.append(LoupeIR.Entity.from_dict(ed))

	for rd in data.get("relations", []):
		if rd is Dictionary:
			doc.relations.append(LoupeIR.Relation.from_dict(rd))

	var lp: Variant = data.get("lod_policy")
	doc.lod_policy = LoupeIR.LODPolicy.from_dict(lp) if lp is Dictionary else LoupeIR.LODPolicy.new()

	doc.provenance = _resolve_provenance(data.get("provenance"), raw, source_path)
	doc.index()

	var integrity := _check_integrity(doc)
	if integrity != "":
		return Result.fail(integrity)

	return Result.success(doc)


## Structural (schema-shape) validation. Kept light; the JSON Schema is the full contract.
static func _validate(data: Dictionary) -> String:
	if String(data.get("version", "")) != LoupeIR.VERSION:
		return "Unsupported IR version: expected '%s', got '%s'" % [LoupeIR.VERSION, data.get("version", "")]
	if not data.has("root"):
		return "IR missing required 'root'"
	var entities: Variant = data.get("entities")
	if not (entities is Array) or entities.is_empty():
		return "IR 'entities' must be a non-empty array"
	for e in entities:
		if not (e is Dictionary):
			return "Each entity must be an object"
		if not e.has("id") or String(e["id"]) == "":
			return "Each entity needs a non-empty 'id'"
		if not e.has("label"):
			return "Entity '%s' missing 'label'" % e.get("id", "?")
		var pl: Variant = e.get("payload")
		if pl is Dictionary:
			var t := String(pl.get("type", "none"))
			if not LoupeIR.PAYLOAD_TYPES.has(t):
				return "Entity '%s' has unknown payload type '%s'" % [e["id"], t]
	return ""


## Referential integrity: unique ids, root exists, parents resolve, relation endpoints resolve.
static func _check_integrity(doc: LoupeIR.Document) -> String:
	var seen := {}
	for e in doc.entities:
		if seen.has(e.id):
			return "Duplicate entity id: '%s'" % e.id
		seen[e.id] = true
	if doc.get_entity(doc.root) == null:
		return "Root entity '%s' not found in entities" % doc.root
	for e in doc.entities:
		if e.parent != "" and doc.get_entity(e.parent) == null:
			return "Entity '%s' references missing parent '%s'" % [e.id, e.parent]
	for r in doc.relations:
		if doc.get_entity(r.from) == null or doc.get_entity(r.to) == null:
			return "Relation references missing endpoint: %s -> %s" % [r.from, r.to]
	return ""


static func _resolve_provenance(p: Variant, raw: String, source_path: String) -> LoupeIR.Provenance:
	var prov := LoupeIR.Provenance.from_dict(p) if p is Dictionary else LoupeIR.Provenance.new()
	if prov.hash == "":
		prov.hash = raw.sha256_text()
	if prov.source == "" and source_path != "":
		prov.source = source_path
	if prov.generated_at == "":
		prov.generated_at = Time.get_datetime_string_from_system(true)
	if prov.generator == "":
		prov.generator = "IRLoader@runtime"
	return prov
