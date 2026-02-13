# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make the doc extension importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "doc" / "_ext"))

from generate_examples import (
    EXAMPLES_BASE_URL,
    build_examples_rst,
    build_section_rst,
    generate_examples_docs,
    group_by_folder,
    ordered_folders,
    write_example_docs,
)

SAMPLE_ENTRIES = {
    "Getting started": {
        "index_abbrv": "GS",
        "index_terms": ["beginner"],
        "categories": ["new"],
        "location": "examples/getting_started/0_Getting_started/0_Getting_started.ipynb",
        "content": "  A hello-world tutorial.",
    },
    "Running quantum circuits on simulators": {
        "index_abbrv": "RQCS",
        "index_terms": ["simulators"],
        "categories": ["new", "simulators"],
        "location": (
            "examples/getting_started/"
            "1_Running_quantum_circuits_on_simulators/"
            "1_Running_quantum_circuits_on_simulators.ipynb"
        ),
        "content": "  Run circuits on simulators.",
    },
    "Grover": {
        "index_abbrv": "Grover",
        "index_terms": ["advanced"],
        "categories": ["advanced"],
        "location": "examples/advanced_circuits_algorithms/Grover/Grover.ipynb",
        "content": "  Grover's search algorithm tutorial.",
    },
    "QAOA": {
        "index_abbrv": "QAOA",
        "index_terms": [],
        "categories": ["hybrid"],
        "location": "examples/hybrid_quantum_algorithms/QAOA/QAOA_braket.ipynb",
        "content": "  QAOA tutorial.",
    },
}


class TestGroupByFolder:
    def test_groups_entries_by_top_level_folder(self):
        groups = group_by_folder(SAMPLE_ENTRIES)
        assert set(groups.keys()) == {
            "getting_started",
            "advanced_circuits_algorithms",
            "hybrid_quantum_algorithms",
        }

    def test_preserves_entry_order_within_group(self):
        groups = group_by_folder(SAMPLE_ENTRIES)
        titles = [title for title, _ in groups["getting_started"]]
        assert titles == [
            "Getting started",
            "Running quantum circuits on simulators",
        ]

    def test_each_entry_is_title_and_dict_pair(self):
        groups = group_by_folder(SAMPLE_ENTRIES)
        for title, entry in groups["getting_started"]:
            assert isinstance(title, str)
            assert "location" in entry

    def test_single_component_location_falls_back_to_other(self):
        entries = {"Odd": {"location": "standalone.ipynb", "content": ""}}
        groups = group_by_folder(entries)
        assert "other" in groups


class TestOrderedFolders:
    def test_known_folders_come_in_section_order(self):
        groups = {
            "hybrid_quantum_algorithms": [],
            "getting_started": [],
            "advanced_circuits_algorithms": [],
        }
        result = ordered_folders(groups)
        assert result == [
            "getting_started",
            "advanced_circuits_algorithms",
            "hybrid_quantum_algorithms",
        ]

    def test_unknown_folders_are_appended_alphabetically(self):
        groups = {
            "getting_started": [],
            "zzz_new": [],
            "aaa_new": [],
        }
        result = ordered_folders(groups)
        assert result[0] == "getting_started"
        assert result[-2] == "aaa_new"
        assert result[-1] == "zzz_new"

    def test_empty_groups_returns_empty(self):
        assert ordered_folders({}) == []


class TestBuildSectionRst:
    def test_known_folder_uses_configured_title(self):
        entries = [("Getting started", SAMPLE_ENTRIES["Getting started"])]
        rst = build_section_rst("getting_started", entries)
        assert "Getting started" in rst
        assert "Get started on Amazon Braket" in rst

    def test_unknown_folder_derives_title_from_name(self):
        entries = [
            (
                "Some Entry",
                {"location": "examples/new_stuff/notebook.ipynb", "content": "New."},
            ),
        ]
        rst = build_section_rst("new_stuff", entries)
        assert "New Stuff" in rst

    def test_entry_link_points_to_github(self):
        entries = [("Getting started", SAMPLE_ENTRIES["Getting started"])]
        rst = build_section_rst("getting_started", entries)
        expected_url = EXAMPLES_BASE_URL + SAMPLE_ENTRIES["Getting started"]["location"]
        assert expected_url in rst

    def test_entry_description_is_included(self):
        entries = [("Getting started", SAMPLE_ENTRIES["Getting started"])]
        rst = build_section_rst("getting_started", entries)
        assert "A hello-world tutorial." in rst

    def test_empty_content_is_handled(self):
        entries = [
            (
                "No Desc",
                {"location": "examples/test/t.ipynb", "content": ""},
            ),
        ]
        rst = build_section_rst("getting_started", entries)
        assert "`No Desc <" in rst

    def test_heading_overline_matches_underline(self):
        entries = [("Test", {"location": "examples/t/t.ipynb", "content": "Desc."})]
        rst = build_section_rst("getting_started", entries)
        lines = rst.split("\n")
        for i, line in enumerate(lines):
            # Match overline: a line of repeated chars followed by non-empty text
            if (
                line
                and len(set(line)) == 1
                and line[0] in "#*"
                and i + 2 < len(lines)
                and lines[i + 1]  # title line must be non-empty
            ):
                overline = line
                title_line = lines[i + 1]
                underline = lines[i + 2]
                assert len(overline) == len(title_line)
                assert overline == underline


class TestBuildExamplesRst:
    def test_contains_toctree(self):
        rst = build_examples_rst(["a.rst", "b.rst"])
        assert ".. toctree::" in rst

    def test_lists_all_section_files(self):
        filenames = ["examples-getting-started.rst", "examples-advanced.rst"]
        rst = build_examples_rst(filenames)
        assert "   examples-getting-started.rst" in rst
        assert "   examples-advanced.rst" in rst

    def test_links_to_examples_repo(self):
        rst = build_examples_rst([])
        assert "amazon-braket-examples" in rst


class TestWriteExampleDocs:
    def test_generates_all_expected_files(self, tmp_path):
        write_example_docs(tmp_path, SAMPLE_ENTRIES)

        assert (tmp_path / "examples.rst").exists()
        assert (tmp_path / "examples-getting-started.rst").exists()
        assert (tmp_path / "examples-advanced-circuits-algorithms.rst").exists()
        assert (tmp_path / "examples-hybrid-quantum-algorithms.rst").exists()

    def test_examples_rst_references_section_files(self, tmp_path):
        write_example_docs(tmp_path, SAMPLE_ENTRIES)

        content = (tmp_path / "examples.rst").read_text()
        assert "examples-getting-started.rst" in content
        assert "examples-advanced-circuits-algorithms.rst" in content
        assert "examples-hybrid-quantum-algorithms.rst" in content

    def test_section_file_contains_entry_data(self, tmp_path):
        write_example_docs(tmp_path, SAMPLE_ENTRIES)

        gs = (tmp_path / "examples-getting-started.rst").read_text()
        assert "A hello-world tutorial." in gs
        assert "Run circuits on simulators." in gs

    def test_returns_generated_filenames(self, tmp_path):
        filenames = write_example_docs(tmp_path, SAMPLE_ENTRIES)
        assert "examples-getting-started.rst" in filenames
        assert "examples-advanced-circuits-algorithms.rst" in filenames
        assert "examples-hybrid-quantum-algorithms.rst" in filenames


class TestGenerateExamplesDocs:
    @patch("generate_examples.fetch_entries")
    def test_writes_files_via_sphinx_hook(self, mock_fetch, tmp_path):
        mock_fetch.return_value = SAMPLE_ENTRIES

        app = MagicMock()
        app.srcdir = str(tmp_path)

        generate_examples_docs(app)

        assert (tmp_path / "examples.rst").exists()
        assert (tmp_path / "examples-getting-started.rst").exists()

    @patch("generate_examples.fetch_entries")
    def test_fetch_failure_does_not_raise(self, mock_fetch, tmp_path):
        mock_fetch.side_effect = Exception("Network error")

        app = MagicMock()
        app.srcdir = str(tmp_path)

        generate_examples_docs(app)

        # No files should be generated on failure
        assert not (tmp_path / "examples.rst").exists()
