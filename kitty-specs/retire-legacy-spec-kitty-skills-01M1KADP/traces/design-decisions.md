# Design Decisions Trace

- **D-001**: The explicit 14-entry legacy-to-canonical mapping is the single
  retirement and replacement authority.
- **D-002**: This is standard change mode, not bulk edit; no same token is being
  mechanically replaced across multiple files.
- **D-003**: Runtime candidate verification is isolated. Installation and real
  user-profile cleanup remain separate gates.
- **D-004**: Keep legacy source directories bundled for compatibility and
  reference use; retirement is enforced at the canonical registry boundary.
