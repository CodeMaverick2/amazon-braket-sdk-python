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

"""Sphinx extension that generates examples documentation from ENTRIES.json.

The amazon-braket-examples repository maintains an ``ENTRIES.json`` catalog of
all example notebooks.  This extension fetches that catalog at doc-build time
and produces the RST files that form the *Examples* section of the SDK
documentation, so the list of examples never goes stale.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

ENTRIES_URL = (
    "https://raw.githubusercontent.com/amazon-braket/amazon-braket-examples"
    "/main/docs/ENTRIES.json"
)

EXAMPLES_BASE_URL = (
    "https://github.com/amazon-braket/amazon-braket-examples/blob/main/"
)

# Ordered mapping from example folder name to display metadata.
# Controls section ordering in the generated docs.  Folders present in
# ENTRIES.json but absent here are appended alphabetically with a
# title derived from the folder name.
SECTIONS = [
    (
        "getting_started",
        {
            "title": "Getting started",
            "description": (
                "Get started on Amazon Braket with some introductory examples."
            ),
        },
    ),
    (
        "braket_features",
        {
            "title": "Amazon Braket features",
            "description": "Learn more about the individual features of Amazon Braket.",
        },
    ),
    (
        "advanced_circuits_algorithms",
        {
            "title": "Advanced circuits and algorithms",
            "description": (
                "Learn more about working with advanced circuits and algorithms."
            ),
        },
    ),
    (
        "hybrid_quantum_algorithms",
        {
            "title": "Hybrid quantum algorithms",
            "description": "Learn more about hybrid quantum algorithms.",
        },
    ),
    (
        "pennylane",
        {
            "title": "Quantum machine learning and optimization with PennyLane",
            "description": (
                "Learn more about how to combine PennyLane with Amazon Braket."
            ),
        },
    ),
    (
        "hybrid_jobs",
        {
            "title": "Amazon Braket Hybrid Jobs",
            "description": "Learn more about hybrid jobs on Amazon Braket.",
        },
    ),
    (
        "analog_hamiltonian_simulation",
        {
            "title": "Analog Hamiltonian Simulation",
            "description": (
                "Learn more about analog Hamiltonian simulation on Amazon Braket."
            ),
        },
    ),
    (
        "pulse_control",
        {
            "title": "Pulse control",
            "description": "Learn more about pulse-level control on Amazon Braket.",
        },
    ),
    (
        "nvidia_cuda_q",
        {
            "title": "NVIDIA CUDA-Q",
            "description": (
                "Learn more about using NVIDIA CUDA-Q with Amazon Braket."
            ),
        },
    ),
    (
        "qiskit",
        {
            "title": "Qiskit on Amazon Braket",
            "description": "Learn more about using Qiskit with Amazon Braket.",
        },
    ),
    (
        "experimental_capabilities",
        {
            "title": "Experimental capabilities",
            "description": "Explore experimental features on Amazon Braket.",
        },
    ),
]


def fetch_entries(url=ENTRIES_URL):
    """Fetch and parse ENTRIES.json from the examples repository."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def group_by_folder(entries):
    """Group entries by their top-level directory under ``examples/``.

    Returns a dict mapping folder names to lists of ``(title, entry)`` tuples,
    preserving the insertion order from *ENTRIES.json*.
    """
    groups: dict[str, list[tuple[str, dict]]] = {}
    for title, entry in entries.items():
        parts = entry["location"].split("/")
        folder = parts[1] if len(parts) >= 2 else "other"
        groups.setdefault(folder, []).append((title, entry))
    return groups


def ordered_folders(groups):
    """Return folder names in display order.

    Known folders appear in the order defined by :data:`SECTIONS`.
    Any remaining folders are appended alphabetically.
    """
    known = [folder for folder, _ in SECTIONS]
    ordered = [f for f in known if f in groups]
    for f in sorted(groups):
        if f not in ordered:
            ordered.append(f)
    return ordered


def _rst_heading(text, char):
    """Return an RST heading with matching overline and underline."""
    line = char * len(text)
    return f"{line}\n{text}\n{line}"


def _section_info(folder):
    """Look up display metadata for *folder*, with a sensible fallback."""
    for name, info in SECTIONS:
        if name == folder:
            return info
    return {"title": folder.replace("_", " ").title(), "description": ""}


def build_section_rst(folder, entries):
    """Build RST content for a single examples section."""
    info = _section_info(folder)

    lines = [_rst_heading(info["title"], "#"), ""]
    if info["description"]:
        lines.append(info["description"])
        lines.append("")

    for title, entry in entries:
        url = EXAMPLES_BASE_URL + entry["location"]
        link_text = f"`{title} <{url}>`_"
        lines.append(_rst_heading(link_text, "*"))
        lines.append("")
        description = entry.get("content", "").strip()
        if description:
            lines.append(description)
            lines.append("")

    return "\n".join(lines)


def build_examples_rst(section_filenames):
    """Build the top-level ``examples.rst`` that includes every section."""
    lines = [
        _rst_heading("Examples", "#"),
        "",
        "There are several examples available in the Amazon Braket repo:",
        "https://github.com/amazon-braket/amazon-braket-examples.",
        "",
        ".. toctree::",
        "    :maxdepth: 2",
        "",
    ]
    for filename in section_filenames:
        lines.append(f"   {filename}")
    lines.append("")
    return "\n".join(lines)


def write_example_docs(srcdir, entries):
    """Generate all examples RST files into *srcdir*.

    This is the core routine called by the Sphinx hook but is also usable
    independently (e.g. for testing).
    """
    srcdir = Path(srcdir)
    groups = group_by_folder(entries)
    folders = ordered_folders(groups)

    section_filenames = []
    for folder in folders:
        filename = f"examples-{folder.replace('_', '-')}.rst"
        rst_content = build_section_rst(folder, groups[folder])
        (srcdir / filename).write_text(rst_content, encoding="utf-8")
        section_filenames.append(filename)

    examples_content = build_examples_rst(section_filenames)
    (srcdir / "examples.rst").write_text(examples_content, encoding="utf-8")

    return section_filenames


def generate_examples_docs(app):
    """``builder-inited`` callback that writes the examples RST files."""
    try:
        entries = fetch_entries()
    except Exception as exc:
        logger.warning(
            "Failed to fetch ENTRIES.json (%s). "
            "Examples documentation will not be updated.",
            exc,
        )
        return

    filenames = write_example_docs(app.srcdir, entries)
    logger.info(
        "Generated examples docs: %d sections, %d entries",
        len(filenames),
        len(entries),
    )


def setup(app):
    """Register the extension with Sphinx."""
    app.connect("builder-inited", generate_examples_docs)
    return {"version": "1.0", "parallel_read_safe": True}
