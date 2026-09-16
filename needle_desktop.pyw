from __future__ import annotations

import argparse
from pathlib import Path
import tkinter as tk

from needle_ui import App


def parse_args(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--root')
    parser.add_argument('--query', default='')
    return parser.parse_known_args(argv)[0]


def main(argv=None):
    args = parse_args(argv)
    root = tk.Tk()
    app = App(root)
    if args.query:
        app.query.set(args.query)
    if args.root:
        workspace = Path(args.root).expanduser().resolve()
        cache = Path.home() / '.needle' / 'switchyard-handoff.json'

        def begin_handoff():
            if not workspace.is_dir():
                app.status.set(f'Workspace not found: {workspace}')
                return
            cache.parent.mkdir(parents=True, exist_ok=True)
            app.build_index([str(workspace)], cache, True, False)
            root.after(250, finish_handoff)

        def finish_handoff():
            if app.busy:
                root.after(250, finish_handoff)
                return
            if app.index:
                app.search()

        root.after(120, begin_handoff)
    root.mainloop()


if __name__ == '__main__':
    main()
