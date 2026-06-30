# Loupe — Data Contract (living spec)

> **Purpose.** The menu of inputs Loupe can visualize. For each domain: what data is required, its
> formats, whether it's scrapable from open sources, and which Loupe **payload type / lens** it renders
> as. Ingestors in `ingest/loupe_ingest/ingestors/` are built against this table. This is a *living*
> document — extend it as new domains/sources are added.

## How to read it
- **Acquisition tier** — how the data reaches the IR:
  - **D** = deterministic parse of a structured file/API ($0, 0 tokens).
  - **API / Scrape** = fetched from an open web source (often still deterministic to parse).
  - **L** = LLM frontier (only when structure can't be derived; grounded + cached).
  - **Gen** = synthesized by Loupe when the source lacks renderable data (the "generate more data" arm).
- **→ payload** — the IR `payload.type` (and thus the lens) the data maps to. Universal structure
  (hierarchy + relations) is always present; the payload is what a lens draws.

## Payload types (the lens set)
`mesh · matrix · graph · signal · text · image · equation · table · point_cloud · volume`

Coverage insight: **`graph` + `mesh`** alone cover the majority of domains below; add `matrix`,
`signal`, `point_cloud`, `volume` and the catalog is essentially complete.

---

## 1. Engineering — Mechanical (engine, rocket, car, transmission, turbine, robot arm, spaceship)
| Need | Formats | Online source (scrapable?) | → payload |
|---|---|---|---|
| Part geometry | glTF/GLB, STEP/IGES, STL, OBJ, USD | GrabCAD, NASA 3D, Sketchfab (CC), Thingiverse — scrape (license-gated) | `mesh` (ref) |
| Assembly tree / BOM | STEP structure, JSON, CSV | derived from CAD — D | hierarchy + `table` |
| Part metadata (function, specs) | text | Wikipedia, manuals — API/Scrape/L | `content_tiers` |
| Kinematics (motion) | joint/DOF JSON, URDF | ROS repos — D/Scrape | relations (+ future motion) |
| Schematic (no CAD) | blueprint JSON | hand / LLM — L/Gen | `mesh` (parametric) |

## 2. Engineering — Electronics / Hardware (PCB, chip, circuit)
| Need | Formats | Source | → |
|---|---|---|---|
| Schematic / netlist | KiCad, SPICE, EDIF, Verilog/RTL | GitHub, OpenCores — D/Scrape | `graph` |
| Board / chip layout | Gerber, GDSII, DEF/LEF | foundry/PCB repos — D | `mesh` / `image` |
| Component datasheet | PDF / text | Octopart, mfr sites — Scrape/L | `content_tiers` |

## 3. Architecture / Civil (building, bridge, city, BIM)
| Need | Formats | Source | → |
|---|---|---|---|
| 3D model / BIM | IFC, Revit, glTF, CityGML | BIMobject, OSM-3D — D/Scrape | `mesh` |
| Floor / system hierarchy | IFC tree, JSON | from IFC — D | hierarchy |
| GIS / terrain | GeoJSON, DEM, LAS/LAZ | OpenStreetMap, USGS — API | `point_cloud` / `mesh` |

## 4. Software / Systems (codebase, microservices, cloud infra, network)
| Need | Formats | Source | → |
|---|---|---|---|
| Code structure (call/dep graph) | source tree, AST, import graph | GitHub repo — D ($0) | `graph` + hierarchy |
| Service topology | OpenAPI, k8s YAML, Terraform, C4 DSL | repos — D | `graph` |
| Runtime traces / metrics | OpenTelemetry, Prometheus | live/API — API | `signal` / `graph` |
| Network | PCAP, topology JSON | — D | `graph` |

## 5. AI / ML (model architecture, training, embeddings)
| Need | Formats | Source | → |
|---|---|---|---|
| Architecture | HF `config.json`, ONNX, live `nn.Module` | HF Hub — D ($0) | hierarchy + `matrix` |
| Weights / attention | safetensors, attention arrays | HF — D/Gen | `matrix` (heatmap) |
| Training dynamics | TensorBoard logs, CSV | — D | `signal` |
| Embedding space | .npy vectors + labels | — D | `point_cloud` |
| Data / compute flow | ONNX graph | — D | `graph` |

## 6. Education / Research (papers, concept/knowledge graph, curriculum)
| Need | Formats | Source | → |
|---|---|---|---|
| Paper structure | PDF, LaTeX, JATS XML, GROBID | arXiv, PubMed, Semantic Scholar API — D/API | hierarchy + `text` |
| Citation / concept graph | RDF, GraphML, JSON | Semantic Scholar / OpenAlex API | `graph` |
| Knowledge graph | RDF/OWL, Wikidata triples | Wikidata / DBpedia SPARQL — API | `graph` |
| Equations | LaTeX / MathML | from paper — D | `equation` |
| Curriculum / syllabus | text / outline | scrape — Scrape/L | hierarchy |

## 7. Biology — Neuro (brain map, neuron firing, connectome)
| Need | Formats | Source | → |
|---|---|---|---|
| Brain atlas / regions | NIfTI, GIFTI, mesh | Allen Brain Atlas, BrainNet — API | `mesh` / `volume` |
| Connectome | connectivity matrix, GraphML | Human Connectome Project — API | `graph` / `matrix` |
| Neuron firing | spike trains (NWB), EEG/MEG (EDF) | DANDI, OpenNeuro — API | `signal` |
| Single-neuron morphology | SWC | NeuroMorpho.org — API | `graph` / `mesh` |

## 8. Biology — Molecular / Cell / Anatomy
| Need | Formats | Source | → |
|---|---|---|---|
| Protein / DNA structure | PDB, mmCIF, mol2 | RCSB PDB, AlphaFold DB — API | `mesh` / `graph` |
| Pathway / gene network | SBML, BioPAX, KEGG | KEGG / Reactome — API | `graph` |
| Anatomy | glTF, OBJ | BodyParts3D, Z-Anatomy — Scrape | `mesh` |
| Sequence | FASTA | NCBI — API | `signal` / `text` |

## 9. Chemistry / Materials (molecule, crystal, reaction)
| Need | Formats | Source | → |
|---|---|---|---|
| Molecule | SMILES, MOL/SDF, XYZ, CIF | PubChem, Materials Project — API | `graph` / `mesh` |
| Crystal lattice | CIF | COD, Materials Project — API | `point_cloud` / `mesh` |
| Reaction network | RXN, JSON | — D/L | `graph` |

## 10. Physics / Astronomy (solar system, particle, fields, spacetime)
| Need | Formats | Source | → |
|---|---|---|---|
| Orbital / ephemeris | SPICE kernels, JSON | NASA JPL Horizons — API | `mesh` + motion |
| Particle / event | HepMC, ROOT | CERN Open Data — D | `graph` / `point_cloud` |
| Fields / simulation | VTK, HDF5, NetCDF | sim output — D | `point_cloud` / `volume` |

## 11. Earth / Climate / Geo
| Need | Formats | Source | → |
|---|---|---|---|
| Terrain / elevation | DEM, GeoTIFF, LAS | USGS, Copernicus — API | `point_cloud` / `mesh` |
| Climate fields | NetCDF, GRIB | NOAA / ECMWF — API | `volume` / `signal` |
| Geology strata | layer JSON | surveys — Scrape | `mesh` |

## 12. Data / Business / Process (org, supply chain, workflow, finance)
| Need | Formats | Source | → |
|---|---|---|---|
| Org / hierarchy | CSV, JSON | internal — D | hierarchy |
| Process / workflow | BPMN, DOT, Mermaid | repos — D | `graph` |
| Supply chain / flow | JSON, CSV | — D | `graph` |
| Financial / time series | CSV, OHLCV API | Yahoo / AlphaVantage — API | `signal` / `table` |

## 13. Mathematics (functions, manifolds, proof structure)
| Need | Formats | Source | → |
|---|---|---|---|
| Function / surface | expression, sampled grid | — D/Gen | `mesh` / `equation` |
| Manifold / field | parametric, mesh | — Gen | `mesh` / `point_cloud` |
| Proof / theorem deps | Lean/Coq dep graph | mathlib — D | `graph` |

## 14. Medical Imaging
| Need | Formats | Source | → |
|---|---|---|---|
| Scans | DICOM, NIfTI | TCIA, OpenNeuro — API | `volume` |
| Segmented organs | mesh / label maps | — D | `mesh` |

## 15. Other media (music, language)
| Need | Formats | Source | → |
|---|---|---|---|
| Music structure | MIDI, MusicXML | — D | `graph` / `signal` |
| Audio | WAV / spectrogram | — D/Gen | `signal` / `image` |
| Language / text | plaintext, dependency parse | — D/L | hierarchy / `graph` |

---

## Open API sources that are $0 and deterministic (no LLM)
arXiv · Semantic Scholar · OpenAlex · Wikidata / DBpedia (SPARQL) · RCSB PDB · AlphaFold DB · PubChem ·
Materials Project · KEGG / Reactome · Allen Brain Atlas · Human Connectome Project · DANDI / OpenNeuro ·
NeuroMorpho · NASA JPL Horizons · NASA 3D · USGS / Copernicus · NOAA / ECMWF · Hugging Face Hub · GitHub ·
OpenStreetMap.

## Build-order implication
The order that unlocks the most domains fastest:
**`graph` lens → `mesh`/`ref` maturity → `matrix` → `signal` → `point_cloud` → `volume`**, each paired
with a per-domain ingestor (deterministic/API first, LLM frontier as fallback, Gen for missing data).
