# Recording the demo GIF

Tool: [LICEcap](https://www.cockos.com/licecap/) (Windows/macOS) or
[Peek](https://github.com/phw/peek) (Linux).

Target: 15–20 seconds, 800×500px window, 10fps.

## Script for Needle

1. Launch the app — show the empty state with no index loaded
2. Click **Build New Index**, choose a small project folder, and save the index (cut the recording while it builds if it takes more than a few seconds)
3. Type a two-word query and click **Search** — show the ranked results
4. Select a result to show the matching snippet, then misspell one word of the query to show typo tolerance still finding it
5. Click **Reveal** on the selected result to show it in the file manager

Record against throwaway data: the GIF is public, so keep real paths, hostnames,
tokens and project names out of frame.

Save as `docs/demo.gif`. Update the README img tag to point to it, and remove
the "Demo GIF coming" note beneath the screenshot.
