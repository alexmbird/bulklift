# Improvements / Roadmap

-   [ ] Delete target directories no longer referenced by manifests (i.e. media you no longer want on devices)
-   [ ] Save a signature in each target directory generated from (codec, bitrate, codec_release, metadata) and automatically regenerate media when these things change
-   [ ] Filters to include/exclude files from a dir by list/glob
-   [ ] `test` subcommand, to run through all manifests in the tree and check validity
-   [ ] Optionally overwrite metadata in output
-   [ ] Extra output formats (m4a)
-   [ ] Handle ctrl+c more gracefully
-   [ ] Release on PyPy
-   [ ] Static release builds
-   [ ] Unit testing against real (generated) trees of files
