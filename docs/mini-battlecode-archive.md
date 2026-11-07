# Mini Battlecode archive (icaijy.com)

The game engine lives in a **different repository**: `icaijy/mini-battlecode`. This Django app contains **only public, read-only database views** and an offline archive importer. It does not compile/run any participant code or read files from the engine repo.

## First deployment

Pull this website update on the production server. In its virtual environment, run:

```bash
python manage.py migrate
python manage.py check
# Reload existing Django service after deploying code.
```

No background worker, new database service, compiler or Cron job is required for this feature.

## Publishing a season

1. In the external engine, use `mbc finals --season /your/game.zip ...`. This creates a `database_import.zip` under the chosen output directory.
2. Copy that ZIP from your own computer to the Django server with `scp` (or another secure file transfer).
3. Run:

```bash
python manage.py import_battlecode /tmp/database_import.zip
# For a corrected final, explicitly overwrite the season:
python manage.py import_battlecode /tmp/database_import.zip --replace
```

The entire ZIP is stored in `BattleSeason.original_archive` (**database BLOB**); season metadata, rules, viewer HTML, participants and results are in DB columns; all match and replay JSON is in `BattleMatch`. Bot sources are retained as private JSON for audit, and not publicly listed. No result ZIP is committed to either GitHub repository. Site pages: `/battlecode/`, `/battlecode/<id>/`, `/battlecode/<id>/match/<index>/`.

## Security

Only a trusted server administrator can run the management command; there is no public upload endpoint. An uploaded archive is validated for file size, names, participant references, match count, duplicate entries and replay/result consistency; the site **never imports or executes** archive Python/C++ code.

The per-season `viewer.html` is untrusted JavaScript and renders in a sandboxed iframe with opaque origin and restrictive CSP. The parent sends public replay JSON into it via `postMessage`; there is no website-network fetch in the iframe. New viewers must implement the message handler defined in the engine's `SEASON_PROMPT_ZH.md`.

Large archives increase the site SQLite database size. Current default cap is 80 MiB per ZIP, 4000 matches and 200 MiB total uncompressed bytes. Plan periodic SQLite backups before adding new seasons.

**GitHub updates do not deploy or migrate production automatically.** Verify the server was reloaded before expecting `/battlecode/` to appear online.
