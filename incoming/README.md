# incoming/

Put a project `.zip` here and push to `main`.

The **Incoming → Build → Release** workflow will:

1. take the newest zip (by version order),
2. replace the whole project with its contents (the folder `incoming/` and `.github/workflows/` are kept),
3. run the tests and build TilePrint for Windows, macOS and Linux,
4. only if everything succeeded: commit the new project state and delete the zip,
5. publish a GitHub Release `vX.Y.Z` with the three packages, the source zip and checksums.

The version is read from the `VERSION` file inside the zip (fallback: the number in the zip file name,
e.g. `tileprint-0.2.0.zip`). If that tag already exists, the last number is bumped automatically
(`0.1.9` → `0.1.10`), so every drop produces a new release.

If a build fails, nothing is committed: the zip stays in `incoming/`, fix it and push again.
