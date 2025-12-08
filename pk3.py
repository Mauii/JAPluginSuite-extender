"""
Simple PK3/PAK viewer and extractor.

Features:
- List contents with sizes, compression ratio, and timestamp.
- Extract all files or only those matching glob patterns (e.g. *.shader, textures/*).
- Guards against zip-slip path traversal when extracting.
"""

import argparse
import fnmatch
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional
from zipfile import BadZipFile, ZipFile


class ArchiveError(Exception):
    """Raised when a PK3/PAK archive cannot be read or extracted safely."""


def open_pk3(path: Path) -> ZipFile:
    if not path.exists():
        raise ArchiveError(f"File not found: {path}")
    try:
        return ZipFile(path)
    except BadZipFile as exc:
        raise ArchiveError(f"Not a valid PK3/ZIP archive: {path} ({exc})") from exc


def list_contents(archive: ZipFile) -> None:
    entries = archive.infolist()
    if not entries:
        print("Archive is empty.")
        return

    name_width = max(len(info.filename) for info in entries)
    name_width = min(name_width, 60)
    header = f"{'Name'.ljust(name_width)}  {'Size':>10}  {'Comp':>10}  {'Ratio':>6}  {'Timestamp':>16}"
    print(header)
    print("-" * len(header))

    for info in entries:
        ratio = 0.0
        if info.file_size:
            ratio = 100.0 * (1 - (info.compress_size / info.file_size))
        timestamp = datetime(*info.date_time).strftime("%Y-%m-%d %H:%M")
        name = info.filename
        if len(name) > name_width:
            name = name[: name_width - 3] + "..."
        print(
            f"{name.ljust(name_width)}  "
            f"{info.file_size:>10}  "
            f"{info.compress_size:>10}  "
            f"{ratio:>5.1f}%  "
            f"{timestamp}"
        )

    total_uncompressed = sum(info.file_size for info in entries)
    total_compressed = sum(info.compress_size for info in entries)
    print("-" * len(header))
    print(
        f"{'TOTAL'.ljust(name_width)}  "
        f"{total_uncompressed:>10}  "
        f"{total_compressed:>10}  "
        f"{0 if not total_uncompressed else (100.0 * (1 - total_compressed / total_uncompressed)):>5.1f}%"
    )


def filter_members(entries: Iterable, patterns: List[str]):
    if not patterns:
        for entry in entries:
            yield entry
        return

    for entry in entries:
        if any(fnmatch.fnmatch(entry.filename, pattern) for pattern in patterns):
            yield entry


def safe_extract_members(
    archive: ZipFile, destination: Path, members, on_progress=None
) -> List[str]:
    """
    Extract specific ZipInfo members safely to destination.
    Returns the list of extracted entry names.
    """
    destination = destination.resolve()
    extracted = []

    for info in members:
        target = destination / info.filename
        resolved_target = target.resolve()
        if not str(resolved_target).startswith(str(destination)):
            raise ArchiveError(f"Unsafe path detected in archive entry: {info.filename}")

        if info.is_dir():
            resolved_target.mkdir(parents=True, exist_ok=True)
            continue

        resolved_target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, open(resolved_target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        extracted.append(info.filename)
        if on_progress:
            on_progress(info.filename)

    return extracted


def safe_extract(
    archive: ZipFile, destination: Path, patterns: List[str], on_progress=None
) -> List[str]:
    members = list(filter_members(archive.infolist(), patterns))
    if not members:
        return []
    return safe_extract_members(archive, destination, members, on_progress=on_progress)


def launch_gui(initial_archive: Optional[Path] = None) -> None:
    # Imported locally so CLI usage stays lightweight.
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class PK3Gui:
        def __init__(self, root: tk.Tk, initial: Optional[Path]):
            self.root = root
            self.archive: Optional[ZipFile] = None
            self.archive_path: Optional[Path] = None
            self.entries = []
            self.filtered_entries = []
            self.last_output_dir = Path.cwd()

            self.path_var = tk.StringVar(value="No archive loaded.")
            self.pattern_var = tk.StringVar()
            self.status_var = tk.StringVar(value="Open a PK3/PAK/ZIP to start.")

            self._build_ui()
            if initial:
                self.load_archive(initial)

        def _build_ui(self) -> None:
            self.root.title("PK3/PAK Viewer & Extractor")
            self.root.geometry("900x520")

            top = ttk.Frame(self.root, padding=10)
            top.pack(fill="x")
            ttk.Button(top, text="Open PK3/PAK...", command=self.prompt_open).pack(side="right")
            ttk.Label(top, textvariable=self.path_var).pack(side="left", fill="x", expand=True)

            filter_frame = ttk.Frame(self.root, padding=(10, 0))
            filter_frame.pack(fill="x", pady=(0, 8))
            ttk.Label(filter_frame, text="Filter (comma-separated globs):").pack(side="left")
            ttk.Entry(filter_frame, textvariable=self.pattern_var, width=45).pack(
                side="left", padx=6
            )
            ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filter).pack(side="left")

            tree_frame = ttk.Frame(self.root, padding=(10, 0))
            tree_frame.pack(fill="both", expand=True)

            columns = ("name", "size", "comp", "ratio", "timestamp")
            self.tree = ttk.Treeview(
                tree_frame,
                columns=columns,
                show="headings",
                selectmode="extended",
                height=16,
            )
            self.tree.heading("name", text="Name")
            self.tree.heading("size", text="Size")
            self.tree.heading("comp", text="Comp")
            self.tree.heading("ratio", text="Ratio")
            self.tree.heading("timestamp", text="Timestamp")

            self.tree.column("name", width=450, anchor="w")
            self.tree.column("size", width=80, anchor="e")
            self.tree.column("comp", width=80, anchor="e")
            self.tree.column("ratio", width=60, anchor="center")
            self.tree.column("timestamp", width=140, anchor="center")

            vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
            hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
            self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

            self.tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            tree_frame.columnconfigure(0, weight=1)
            tree_frame.rowconfigure(0, weight=1)

            actions = ttk.Frame(self.root, padding=10)
            actions.pack(fill="x")
            ttk.Button(actions, text="Extract Selected...", command=self.extract_selected).pack(
                side="right", padx=(6, 0)
            )
            ttk.Button(actions, text="Extract Filtered...", command=self.extract_filtered).pack(
                side="right"
            )
            ttk.Button(actions, text="Reload", command=self.reload_archive).pack(side="left")

            status = ttk.Frame(self.root, padding=10)
            status.pack(fill="x")
            ttk.Label(status, textvariable=self.status_var).pack(side="left")

        def set_status(self, message: str) -> None:
            self.status_var.set(message)
            self.root.update_idletasks()

        def prompt_open(self) -> None:
            file_path = filedialog.askopenfilename(
                title="Open PK3/PAK/ZIP",
                filetypes=[("PK3/PAK/ZIP", "*.pk3 *.pak *.zip"), ("All files", "*.*")],
            )
            if file_path:
                self.load_archive(Path(file_path))

        def reload_archive(self) -> None:
            if self.archive_path:
                self.load_archive(self.archive_path)

        def load_archive(self, path: Path) -> None:
            try:
                if self.archive:
                    self.archive.close()
                self.archive = open_pk3(path)
            except ArchiveError as exc:
                messagebox.showerror("Failed to open archive", str(exc))
                self.set_status("Ready.")
                return

            self.archive_path = path
            self.entries = self.archive.infolist()
            self.filtered_entries = list(self.entries)
            self.path_var.set(str(path))
            self.set_status(f"Loaded {len(self.entries)} entries.")
            self.refresh_tree(self.filtered_entries)

        def refresh_tree(self, entries) -> None:
            self.tree.delete(*self.tree.get_children())
            for idx, info in enumerate(entries):
                ratio = 0.0
                if info.file_size:
                    ratio = 100.0 * (1 - (info.compress_size / info.file_size))
                timestamp = datetime(*info.date_time).strftime("%Y-%m-%d %H:%M")
                self.tree.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(
                        info.filename,
                        info.file_size,
                        info.compress_size,
                        f"{ratio:0.1f}%",
                        timestamp,
                    ),
                )

        def current_patterns(self) -> List[str]:
            return [p.strip() for p in self.pattern_var.get().split(",") if p.strip()]

        def apply_filter(self) -> None:
            if not self.archive:
                messagebox.showinfo("No archive", "Open an archive first.")
                return
            patterns = self.current_patterns()
            self.filtered_entries = list(filter_members(self.entries, patterns))
            self.refresh_tree(self.filtered_entries)
            self.set_status(f"Showing {len(self.filtered_entries)} entries.")

        def extract_entries(self, entries) -> None:
            if not self.archive:
                messagebox.showinfo("No archive", "Open an archive first.")
                return
            if not entries:
                messagebox.showinfo("Nothing to extract", "No entries match the current selection.")
                return

            dest = filedialog.askdirectory(
                title="Select destination folder", initialdir=str(self.last_output_dir)
            )
            if not dest:
                return
            destination = Path(dest)
            self.last_output_dir = destination

            try:
                safe_extract_members(
                    self.archive,
                    destination,
                    entries,
                    on_progress=lambda name: self.set_status(f"Extracted {name}"),
                )
            except ArchiveError as exc:
                messagebox.showerror("Extraction failed", str(exc))
                return

            messagebox.showinfo(
                "Extraction complete", f"Extracted {len(entries)} item(s) to:\n{destination}"
            )
            self.set_status(f"Extracted {len(entries)} item(s).")

        def extract_selected(self) -> None:
            selection = self.tree.selection()
            if not selection:
                messagebox.showinfo("No selection", "Select one or more files to extract.")
                return
            entries = [self.filtered_entries[int(iid)] for iid in selection]
            self.extract_entries(entries)

        def extract_filtered(self) -> None:
            self.extract_entries(self.filtered_entries)

    root = tk.Tk()
    PK3Gui(root, initial_archive)
    root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PK3/PAK viewer and extractor")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="List archive contents")
    list_parser.add_argument("archive", type=Path, help="Path to .pk3/.pak/.zip file")

    extract_parser = subparsers.add_parser("extract", help="Extract files from the archive")
    extract_parser.add_argument("archive", type=Path, help="Path to .pk3/.pak/.zip file")
    extract_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("extracted"),
        help="Destination directory (default: ./extracted)",
    )
    extract_parser.add_argument(
        "-p",
        "--pattern",
        action="append",
        help="Glob pattern to filter entries (e.g. *.shader, textures/*). Can be used multiple times.",
    )

    gui_parser = subparsers.add_parser("gui", help="Launch GUI viewer/extractor")
    gui_parser.add_argument(
        "archive",
        nargs="?",
        type=Path,
        help="Optional archive to open immediately",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # If no command is provided (e.g., double-click or plain "python pk3_tool.py"),
    # default to launching the GUI.
    if not getattr(args, "command", None):
        args.command = "gui"
        args.archive = None
    try:
        if args.command == "gui":
            launch_gui(args.archive)
            return

        archive = open_pk3(args.archive)

        if args.command == "list":
            list_contents(archive)
        elif args.command == "extract":
            extracted = safe_extract(
                archive,
                args.output,
                args.pattern or [],
                on_progress=lambda name: print(f"Extracted {name}"),
            )
            if not extracted:
                print("No matching files to extract.")
        else:
            sys.exit("Unknown command")
    except ArchiveError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
