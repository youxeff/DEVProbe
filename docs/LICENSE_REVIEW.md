# Dependency and hosted-use review

Checked against installed package metadata, npm lockfiles, and the linked upstream material on 2026-09-21. This is a release inventory and engineering review, not a legal clearance. DevProbe itself has no newly assigned open-source license.

The machine-readable [dependency inventory](dependency-licenses.json) covers the Python runtime dependency closure, the separate Semgrep environment, and the frontend/analyzer npm dependency trees. Recreate it with `python backend/scripts/license_inventory.py` after installing both Python environments. It includes development dependencies marked in npm lockfiles; it does not cover Debian packages inside an image that has not yet been built.

| Component | Declared license / terms | Build decision |
| --- | --- | --- |
| FastAPI, Pydantic, SQLAlchemy, Alembic, Next.js, React, Tailwind, Recharts, Radix UI | MIT declarations | Preserve notices in distributions. |
| shadcn/ui source components | MIT | Upstream notice is retained in `THIRD_PARTY_NOTICES.md`. |
| Bandit | Apache-2.0 | Invoked as an installed static tool; preserve upstream notices. |
| Radon, ESLint, typescript-eslint | MIT | DevProbe-owned fixed configuration; no customer plugins/configuration. |
| Semgrep Community Edition 1.177.0 | LGPL-2.1-or-later package declaration | Separate unmodified CLI environment; only the three DevProbe-owned rules are used. Review redistribution/source obligations for the shipped image. |
| Semgrep-maintained Registry/Pro rules | Separate restricted rules license | **Not used.** Do not replace the local configuration with `--config auto` or Registry rules without a new license review. |
| Psycopg / psycopg-binary | LGPL-3.0-only declarations | Review LGPL and bundled native library notices for image redistribution. |
| certifi | MPL-2.0 | Preserve the package's license and notices. |
| Redis server in Compose | Redis 7.2 image family | Deliberately pinned to the 7.2 release family; verify the exact image's license and digest before release. The Python Redis client is MIT. |
| PostgreSQL | PostgreSQL License | Native PostgreSQL 16 image is configured; image build/run remains a CI gate. |
| Stripe Python SDK | MIT | Hosted Stripe service terms and account activation are separate. No live payments were made. |
| OpenAI API / GitHub API | Hosted service terms, independent of client-library licenses | Configure accounts and review customer-data/provider terms before hosting customer data. No provider key is distributed. |

Semgrep's current documentation explicitly distinguishes its LGPL CE engine from its maintained rules and proprietary products. The maintained rules are restricted for competing hosted products. DevProbe avoids those rules, registry downloads, and proprietary engines. [Semgrep licensing](https://docs.semgrep.dev/licensing).

Upstream licenses: [Bandit](https://github.com/PyCQA/bandit/blob/main/LICENSE), [Radon](https://github.com/rubik/radon/blob/master/LICENSE), [ESLint](https://github.com/eslint/eslint/blob/main/LICENSE), [Psycopg](https://www.psycopg.org/license/), [Redis 7.2](https://github.com/redis/redis/blob/7.2/COPYING), [PostgreSQL](https://www.postgresql.org/about/licence/), [shadcn/ui](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md).

Remaining release work: inspect the exact container OS/native-library SBOM, preserve required notices and corresponding source/offer obligations, approve provider/customer terms, and repeat the inventory for each dependency upgrade. Commercial hosting has not been activated or represented as license-cleared.

The metadata-only inventory leaves `face` and `peewee` undeclared. Their installed wheel license files were inspected: `face` 26.0.1 contains the BSD 3-clause text (`face-26.0.1.dist-info/licenses/LICENSE`); `peewee` 3.19.0 contains the MIT text (`peewee-3.19.0.dist-info/licenses/LICENSE`). These reviewed files resolve the metadata gaps for this tested environment.
