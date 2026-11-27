# Design system (example)

Every internal FTMO app looks like one product, so nobody has to learn a new screen. Owned by the design
system team; a repo that needs to differ proposes it to them (an example of a company standard: the real one
would point at FTMO's design system and its component library).

- Use the shared components (`Button`, `Table`, `Field`, `Banner`), never hand-made ones.
- Colors and spacing only from tokens: `--surface`, `--text`, `--accent`, `--danger`, `--space-1..6`.
- Numbers in tables are right-aligned, monospaced, with the currency or unit in the header, not in cells.
- Money is shown with its currency and never rounded for display without saying so.
- Every table can be exported to CSV: people will do it anyway, with a screenshot.
- Errors say what happened and what to do next, in one sentence. No codes without words.
