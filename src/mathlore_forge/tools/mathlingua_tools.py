"""Tool implementations for Mathlingua authoring and `mlg` CLI interactions."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from mathlore_forge.mlg.client import MlgClient
from mathlore_forge.mlg.editor import (
    find_item_by_id as _find_item,
    insert_item_after_id as _insert_item,
    read_content_file as _read_file,
    replace_item_by_id as _replace_item,
    write_content_file as _write_file,
)


class MathlinguaToolkit:
    """Toolkit providing tool functions for the Mathlingua authoring agent.

    Configurable with:
        content_root: Root directory of the Mathlingua collection (where `mlg.json` lives).
        mlg_bin: Path to or name of the `mlg` binary.
    """

    def __init__(self, content_root: Path | str, mlg_bin: Path | str = "mlg"):
        self.content_root = Path(content_root).resolve()
        self.mlg_bin = str(mlg_bin)
        self.mlg_client = MlgClient(content_root=self.content_root, mlg_bin=self.mlg_bin)

    # -------------------------------------------------------------------------
    # `mlg` CLI Tools
    # -------------------------------------------------------------------------

    def run_mlg(self, subcommand: str, args: list[str] | None = None) -> str:
        """Executes an `mlg` command-line tool invocation on the Mathlingua collection.

        Supported subcommands include:
        - 'check': Checks the collection or specified files for syntax and semantic errors. Automatically formats and generates missing UUIDs on check. Pass file paths in args (e.g. args=['content/07_algebra/02_groups.mlg', '--json']).
        - 'structure': Returns collection layout, pages, and items with IDs and headings as JSON (use args=['--json']).
        - 'search': Searches for items, definitions, and concepts across the collection (e.g. args=['group', '--json']).
        - 'format': Reformats `.mlg` files according to configured margins.
        - 'version': Displays the Mathlingua compiler version.

        Args:
            subcommand: The mlg subcommand to execute (e.g. 'check', 'structure', 'search', 'format').
            args: Optional list of command-line arguments or flags (e.g. ['--json', 'path/to/file.mlg']).

        Returns:
            The command output, or error message with diagnostic details.
        """
        cmd_args = [subcommand]
        if args:
            cmd_args.extend(args)
        proc = self.mlg_client.run_raw(cmd_args)
        output = proc.stdout
        if proc.stderr:
            output = f"{output}\n{proc.stderr}".strip() if output else proc.stderr
        return output or f"Command `mlg {subcommand}` completed with code {proc.returncode}."

    def mlg_check(self, paths: list[str] | None = None) -> str:
        """Checks the specified Mathlingua files or entire collection for syntax and semantic errors.

        Note: When `formatOnCheck: true` is configured in `mlg.json`, `mlg check`
        automatically generates and assigns fresh UUIDs to any newly added top-level items
        that omit `Id:`.

        Args:
            paths: Optional list of file paths to check (e.g. ['07_algebra/02_groups.mlg']). If omitted, checks all files.

        Returns:
            A human-readable report indicating clean pass or listing specific diagnostic messages with line numbers.
        """
        report = self.mlg_client.check(paths=paths, json_output=True)
        return report.summary()

    def mlg_structure(self) -> str:
        """Inspects the collection layout, table of contents, and items with their IDs and headings.

        Returns:
            JSON string containing collection title, directories, files, and items.
        """
        return self.mlg_client.structure(json_output=True)

    def mlg_search(self, query: str) -> str:
        """Searches items, definitions, and command signatures across the Mathlingua collection.

        Args:
            query: The concept, symbol, or signature to search for (e.g. 'group', '\\monoid', 'abelian').

        Returns:
            JSON string containing matching items, locations, and snippets.
        """
        return self.mlg_client.search(query=query, json_output=True)

    def mlg_format(self) -> str:
        """Reformats `.mlg` source files in the collection according to standard print margins.

        Returns:
            Confirmation or error status.
        """
        return self.mlg_client.format()

    # -------------------------------------------------------------------------
    # Content Authoring & File Editing Tools
    # -------------------------------------------------------------------------

    def read_content_file(self, file_path: str) -> str:
        """Reads the full content of a Mathlingua (.mlg) file in the collection.

        Args:
            file_path: Relative path (e.g. '07_algebra/02_groups.mlg' or 'content/07_algebra/02_groups.mlg') or filename.

        Returns:
            The text content of the file.
        """
        try:
            return _read_file(self.content_root, file_path)
        except Exception as err:
            return f"Error reading file '{file_path}': {err}"

    def write_content_file(self, file_path: str, content: str) -> str:
        """Creates or overwrites a Mathlingua (.mlg) file in the collection.

        Args:
            file_path: Relative path or filename where the content should be written.
            content: The text content to write.

        Returns:
            Confirmation message with the resolved file path.
        """
        try:
            resolved = _write_file(self.content_root, file_path, content)
            return f"Successfully wrote {len(content)} characters to {resolved.relative_to(self.content_root)}."
        except Exception as err:
            return f"Error writing file '{file_path}': {err}"

    def insert_item_after(self, file_path: str, after_id: str, new_item_content: str) -> str:
        """Inserts new Mathlingua content directly after the item with ID `after_id` in `file_path`.

        Maintains standard two-blank-line separation between top-level items.
        Guideline: Omit `Id:` in `new_item_content`; running `mlg_check` will automatically generate and attach a UUID.

        Args:
            file_path: Path to the .mlg file (e.g. '07_algebra/02_groups.mlg' or 'content/07_algebra/02_groups.mlg').
            after_id: The UUID of the preceding item (e.g. 'e4d7371d-29bd-431f-ab09-e114fe89e5cf').
            new_item_content: The Mathlingua code snippet to insert.

        Returns:
            Success confirmation with insertion location and preview of surrounding lines.
        """
        try:
            res = _insert_item(self.content_root, file_path, after_id, new_item_content)
            return (
                f"Successfully inserted content after item '{res.after_id}' in {res.relative_path} "
                f"at line {res.inserted_line}.\n\nSurrounding preview:\n{res.preview}"
            )
        except Exception as err:
            return f"Error inserting content after '{after_id}' in '{file_path}': {err}"

    def find_item_by_id(self, item_id: str, file_path: str | None = None) -> str:
        """Locates an item by its ID across the collection or in a specific file.

        Args:
            item_id: The UUID of the item to search for.
            file_path: Optional file path to restrict the search. If omitted, searches all .mlg files.

        Returns:
            The file path, line numbers, and full item content if found.
        """
        info = _find_item(self.content_root, item_id, file_path=file_path)
        if not info:
            return f"Item with ID '{item_id}' was not found" + (f" in '{file_path}'." if file_path else " in the collection.")
        return (
            f"Found item '{info.id}' in {info.relative_path} (lines {info.start_line}-{info.end_line}):\n\n"
            f"{info.content}"
        )

    def replace_item_by_id(self, file_path: str, item_id: str, new_item_content: str) -> str:
        """Replaces an existing item matching `item_id` in `file_path` with `new_item_content`.

        Args:
            file_path: Path to the .mlg file containing the item.
            item_id: The UUID of the item to replace.
            new_item_content: The replacement Mathlingua code.

        Returns:
            Confirmation message and preview of the replaced section.
        """
        try:
            res = _replace_item(self.content_root, file_path, item_id, new_item_content)
            return (
                f"Successfully replaced item '{res.item_id}' in {res.relative_path} "
                f"(lines {res.start_line}-{res.end_line}).\n\nPreview:\n{res.preview}"
            )
        except Exception as err:
            return f"Error replacing item '{item_id}' in '{file_path}': {err}"

    # -------------------------------------------------------------------------
    # Tool registration helpers
    # -------------------------------------------------------------------------

    def get_tools(self) -> list[Callable]:
        """Returns the full list of callable tools for the Mathlingua authoring agent."""
        return [
            self.run_mlg,
            self.mlg_check,
            self.mlg_structure,
            self.mlg_search,
            self.mlg_format,
            self.read_content_file,
            self.write_content_file,
            self.insert_item_after,
            self.find_item_by_id,
            self.replace_item_by_id,
        ]

    def get_mlg_tools(self) -> list[Callable]:
        """Returns only the `mlg` CLI tools."""
        return [
            self.run_mlg,
            self.mlg_check,
            self.mlg_structure,
            self.mlg_search,
            self.mlg_format,
        ]
