# Demo evidence

The repository includes real UI captures at `docs/screenshots/customer-discovery.png` and `docs/screenshots/seat-map.png`, taken after the application was built, migrated, and seeded. To reproduce them:

1. Start Compose and apply migrations.
2. Run `python -m app.database.seed` in the backend container.
3. Open <http://localhost:5173>.
4. Sign in with a seeded account from the README.

The concurrency evidence is generated—not hand-written—at `backend/tests/integration/concurrency-report.json` by the 50-customer integration test.
