# Report policy bundle

The reviewed repository identity is exactly
`https://github.com/axendo79/ProjectNyx.git`, this project's public repository.
Deployment binds that identity to its local checkout; no network read occurs.
The `decisions/` prefixes include only pinned public decision artifacts.

Reviewed commits, all reachable from main at implementation baseline `34ec397`:

- `34ec397e7eaa5daf10ffbff4c4f5b5021d4fed40`: shipped baseline including accepted ADR 0031.
- `98dc48d395a0945cf0c3d728c706e429db3ada97`: proposed ADR 0031, for differing revision reports.
- `823b3ab776faf2635f37c8c3bcdd645c3850f784`: R092 fixture's before tree.
- `902467afa54887de0d15ab9f1a9d23403e9628cc`: ratified R092 fixture's after tree.
- `531a679598dfbcce45a6a0a239c85be958ec55fd`: ratified later Python ADR 0009 fixture.

These entries implement the public ADR corpus and fixture choices in ADR 0031
sections 7 and 8(c)/(h). A readable local path or a caller URL adds no admission.
The importer accepts only exact repository/revision/path/blob expansions.
New revisions require review and a complete validated policy at restart.

Vocabulary definitions retain their original source bytes under digest filenames.
`report-admission.json` is the manifest of admitted bindings; the retained
definitions also supply historical bindings, including retired versions. Backup
bundles preserve both files and every definition. Removing admission retires a
definition; deleting its file prevents startup on a store that used it.
