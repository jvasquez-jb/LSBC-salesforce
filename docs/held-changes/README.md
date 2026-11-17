# Held changes

Built and tested in LSBC-Partial, but held back from the active org configuration until Jonathan approves them.

| Patch | What it does | Held since | How to test it now |
| --- | --- | --- | --- |
| `nightly-license-expiry.patch` | `Business License Schedule: Expired And Lapsed Licenses` sets an Active license's Status to Expired once its Period End has passed. On its first run it would expire about 666 licenses, almost all migrated. | 16 Nov 2026 | Version 3 of the flow is in the org but inactive (version 2 runs nightly). Setup > Flows > the flow > open version 3 > Debug > choose one Active license whose Period End has passed > untick rollback > Run. The license becomes Expired and Look Up a License shows "Expired on <date>". |

To release: `git apply docs/held-changes/nightly-license-expiry.patch`, deploy the flow (it becomes the active version), commit, and update the Deployment Manifest.
