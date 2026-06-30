"""Offline routing/parse tests for the API ingestors (no network — parsing logic only)."""
from loupe_ingest.ingestors import ArxivIngestor, GitHubIngestor, PDBIngestor, Source


def test_arxiv_id_extraction_and_routing():
    ing = ArxivIngestor()
    assert ing._extract_id("arxiv:1706.03762") == "1706.03762"
    assert ing._extract_id("https://arxiv.org/abs/2407.12844v2") == "2407.12844v2"
    assert ing._extract_id("not an id") is None
    assert ing.can_handle(Source("arxiv:1706.03762"))
    assert ing.can_handle(Source("https://arxiv.org/abs/2407.12844"))
    assert not ing.can_handle(Source("pdb:1CRN"))


def test_pdb_id_extraction_and_routing():
    ing = PDBIngestor()
    assert ing._extract_id("pdb:1CRN") == "1CRN"
    assert ing._extract_id("pdb:4hhb") == "4HHB"
    assert ing._extract_id("1CRN") == "1CRN"  # bare 4-char id parses; prefix gating is in can_handle
    assert ing._extract_id("toolong") is None
    assert ing.can_handle(Source("pdb:1CRN"))
    assert ing.can_handle(Source("1abc", kind_hint="pdb"))
    assert not ing.can_handle(Source("1CRN"))  # no prefix/hint → not claimed
    assert not ing.can_handle(Source("github:a/b"))


def test_pdb_ca_parsing():
    ing = PDBIngestor()
    sample = "\n".join([
        "ATOM      1  N   MET A   1      10.000  10.000  10.000  1.00  0.00           N",
        "ATOM      2  CA  MET A   1      11.000  10.000  10.000  1.00  0.00           C",
        "ATOM      3  CA  GLY A   2      12.000  11.000  10.000  1.00  0.00           C",
        "ATOM      4  CA  SER B   1      20.000  20.000  20.000  1.00  0.00           C",
        "HETATM    5  O   HOH A 100      30.000  30.000  30.000  1.00  0.00           O",
    ])
    chains = ing._parse_ca(sample)
    assert set(chains) == {"A", "B"}
    assert len(chains["A"]) == 2  # two CA atoms in chain A
    assert chains["A"][0]["pos"] == [11.0, 10.0, 10.0]
    assert len(chains["B"]) == 1


def test_github_repo_extraction_and_routing():
    ing = GitHubIngestor()
    assert ing._extract_repo("github:pallets/flask") == ("pallets", "flask")
    assert ing._extract_repo("https://github.com/pallets/flask.git") == ("pallets", "flask")
    assert ing._extract_repo("nope") is None
    assert ing.can_handle(Source("github:pallets/flask"))
    assert ing.can_handle(Source("https://github.com/pallets/flask"))
    assert not ing.can_handle(Source("arxiv:1706.03762"))


def test_github_safe_id():
    ing = GitHubIngestor()
    assert ing._safe_id("src/app.py") == "f_src__app_py"
