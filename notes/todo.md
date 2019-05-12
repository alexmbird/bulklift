# Improvements / Roadmap

-   [X] <strike>Delete target directories no longer referenced by manifests (i.e. media you no longer want on devices)</strike>
-   [X] <strike>`test` subcommand, to run through all manifests in the tree and check validity</strike>
-   [X] <strike>Save a signature in each target directory generated from (codec, bitrate, codec_release, metadata) and automatically regenerate media when these things change</strike>
-   [X] <strike>BUGFIX: subdirectories of dirs with `enabled=true` are not handled well</strike>
-   [ ] Dedicated dict-like object for `target`s with sane defaults
-   [ ] Filters to include/exclude files from a dir by list/glob
-   [ ] Transcode for only one target in a single run.  This fits the model of updating a media library on an occasionally-connected device, e.g. a phone mounted with fuse-mtp.
-   [ ] Check manifest content in test mode, not just yaml parsing
-   [ ] Test new manifests after they get created in edit mode
-   [ ] Optionally overwrite metadata in output
-   [ ] Extra output formats (m4a)
-   [ ] Handle ctrl+c more gracefully
-   [ ] Release on PyPy
-   [ ] Static release builds
-   [ ] Unit testing against real (generated) trees of files
