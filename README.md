# Bulklift: A Bulk Transcoding Tool for Large Music Collections

It is the year 2019.  Most of humanity has switched to streaming their music from an entity known as "The Cloud".  A brave group of rebels hold out, clinging valiantly to their own music libraries but struggling ever harder to sync them across multiple devices.

Rebels, I bring a tool to ease your burden.  **Bulklift**.

<p align=center><img src="docs/images/1280px-MARSEILLE_MAERSK.jpg" alt="Image from Wikipedia" width="75%"/></p>

Bulklift walks your music library looking for `.bulklift.yaml` manifests.  It follows the instructions within to transcode any music that's in the same directory.

Features:

-  [ffmpeg](http://ffmpeg.org/) for transcoding
-  Generate multiple collections of output audio from a single source tree
-  Automatically add [replaygain](https://en.wikipedia.org/wiki/ReplayGain) tags to output files using the excellent [r128gain](https://github.com/desbma/r128gain)
-  Inheritable, per-directory config system makes it a breeze to setup
-  Manifests are just text files stored alongside your music; no database to corrupt or lose
-  Toggle which output tree(s) a source album will be transcoded to
-  Include/exclude specific tracks based upon filename globbing
-  Copies album art files (gif, png, jpg) unmolested to the output directory
-  Passthrough `copy` format to copy files without re-encoding
-  Minimise IO by transcoding all copies of a source within a [single ffmpeg run](https://trac.ffmpeg.org/wiki/Creating%20multiple%20outputs)
-  Multithreading (4x faster on my Raspberry Pi media server)

Bulklift has approximately zero bells and whistles.  It doesn't try to be clever and decisions about metadata are left to the user.  It won't download misspellings of your favourite artist's name from CDDB and won't force strange genres from other people's tags upon your filesystem.  Never again will Taylor Swift darken your goth folder.

Bulklift is opinionated about the directory structure you keep your music in.  One album, one directory, one `.bulklift.yaml` with other settings inherited from directories above.  It doesn't care about directory names or how many levels there are in your directory tree above the album.

Filenames are simply reused, but with the extension changed to match the output format.


## Requirements

- Python 3.10+
- `apt install ffmpeg`

## Building
```plain
$ python3 -m venv venv
$ . venv/bin/activate      # or variant for your shell
$ pip3 install wheel
$ pip3 install -r requirements.txt
```

## Testing
```plain
$ sudo apt install sox  # used to generate test data
$ python3 -m unittest discover code/
```

Notes:
-   The tests create a fake tree of input media in a tempdir.  To save SSD wear and improve performance you may wish to have `/tmp` [mounted](https://askubuntu.com/questions/173094/how-can-i-use-ram-storage-for-the-tmp-directory-and-how-to-set-a-maximum-amount#173294) as `tmpfs`.


## Usage
```plain
source_tree > $ echo 'root: true' > .bulklift.yaml  # first declare your root
source_tree > $ bulklift edit                       # add other root config
source_tree > $ cd "Lady Gaga/Born This Way"
Born This Way > $ bulklift edit                     # add metadata; enable encoding
Born This Way > $ cd ..
source_tree > $ bulklift transcode .                # transcode any new targets
```

## Common Operations

### Basic Transcoding
```
$ bulklift transcode /path/to/media/root
```

### Re-Encode Files of One Type
Say you've just updated libopus to a newer, better version.  How to re-encode _just_ the .opus files?  Simply delete them and allow Bulklift to create replacements...

```
$ cd /output/tree/root   # be sure to do this on the output, not the source!
$ find . -name '*.opus' -delete
$ bulklift transcode /path/to/source/root
```

### Other Useful Operations

-   Find all instances of a malformed parameter: `find . -name .bulklift.yaml -exec grep -H 'format:' '{}' ';'`
-   Edit a manifest: `bulklift edit [path to dir]`.  Default is the current directory.  If no `.bulklift.yaml` exists Bulklift will try to generate a template based on the directory's contents and the manifests of its ancestors.  Remember a dir inherits the permissions of its parents so you can delete most of the config.


## Configuration
Yaml, nothing more.

The power of bulklift comes from its inheritable manifest system.  At any level in your source tree you can create a `.bulklift.yaml` manifest overriding options from the previous.

Let's demonstrate with an example.  My source music library looks like this:

```plain
.
├── .bulklift.yaml
├── __AMBIENT
│   ├── .bulklift.yaml
│   ├── Artist A
|   │   ├── .bulklift.yaml
│   │   ├── 2006 First Album [flac]
│   │   │   ├── .bulklift.yaml
│   │   │   ├── 01 - Introduction.flac
│   │   │   ├── 02 - The Second Track.flac
│   │   │   ├── 03 - 3333333.flac
│   │   │   ├── 04 - Getting Bored Now.flac
│   │   │   └── cover.jpg
│   │   └── 2008 Difficult Second Album [mp3]
│   │       ├── .bulklift.yaml
│   │       ├── 01 - Track 1 title.mp3
│   │       ├── 02 - Track 2 title.mp3
│   ├── Artist B
│   │   ├── 2006 First Album [flac]
...

```

1.  At the top level set global config options (e.g. path to ffmpeg) and declare target trees with their default bitrates and formats.  This must contain `root: true` so Bulklift knows where to stop when loading manifests from subdirectories deep in your tree.
2.   At an intermediate level (`__AMBIENT`) a `.bulklift.yaml` manifest specifying metadata for the genre (`genre: Ambient`).
3.   At the artist level, a third `.bulklift.yaml` specifies metadata for the artist (`artist: Artist B`)
4.   At the bottom level (the individual album) switch encoding on (`enabled: true`) for one or more targets and add metadata tags for the name and year of the album (`album: Greatest Hits` / `year: 2018`).

The key concept is that Bulklift merges the the manifest of any directory with those of its parents.  The deepest manifest (i.e. the one in the dir with your music) has precendence so you can override settings from parent directories.  Want to use a different build of ffmpeg to transcode your Dubstep collection?  Override the artist for one particular collaboration album?  The world is your oyster.

Some of the more common options...

| Key        | Required | Example | Meaning |
|------------|----------|---------|---------------------|
| `root`     | Y        | `true`  | Signifies the root directory of your source tree.  Bulklift won't search for any manifests above this.  Must be present **only** in the root manifest; anywhere else and BL will get confused.  |
| `config.transcoding.ffmpeg_path` | - | `${HOME}/.local/bin/ffmpeg` | Ffmpeg binary to use for transcoding.  Often this is of value when you want to transcode with a more recent build than the one shipped with your OS.  Default is to search your path. |
| `config.transcoding.threads` | - | `3` | Number of encoding jobs to run in parallel.  Default is the number of available cores.  |
| `config.transcoding.rewrite_metadata` | - | `{'track': null, 'album':'', artist':'{artist}'}` | Rewrite selected tags in the target files.  Value is treated as a `format()` string which will have metadata from the Bulklift manifest interpolated into place.  An empty value will cause the tag to be deleted.  `null` disables any rewriting inherited from a previous manifest.  Valid metadata field names are listed [here](https://wiki.multimedia.cx/index.php?title=FFmpeg_Metadata#MP3). |
| `config.r128gain.r128gain_path` | - | `${HOME}/.local/bin/r128gain` | [r128gain](https://github.com/desbma/r128gain) binary to use.  Default is to search your path. |
| `config.r128gain.type` | - | `album`, `track`, `false` | Run [r128gain](https://github.com/desbma/r128gain) against each target dir after it has been transcoded.  Default is `album`; other options are `track` or `null` (the yaml value, not the string) to disable entirely. |
| `config.r128gain.threads` | - | `2` | Run a specific number of r128gain threads.  Default is to let it choose, usually the number of cores in your system. |
| `config.r128gain.ffmpeg_path` | - | `${HOME}/.local/bin/ffmpeg` | Use a specific ffmpeg binary for r128gain.  Default is to fail back to `config.transcoding.ffmpeg_path` and then the first `ffmpeg` in `$PATH`. |
| `config.target.album_dir` | - | `"{genre}/{year} {album}"` | Template for the directories music will be transcoded into.  The default is suitable for albums with a single artist.  Override it for mixes, soundtracks etc.  Passed to Python's `str.format()` [method](https://docs.python.org/3/library/stdtypes.html#str.format) to interpolate metadata fields.  Set globally rather than for specific targets because it is presumed you'll want consistent naming.  |
| `outputs`  | -        | `[]`    | List of outputs BL _may_ transcode to.  While typically (but not necessarily) defined in your root manifest they only take effect for albums in which their `enabled` flag is set to `true`. |
| `outputs[].name` | - | `myname` | Textual name for the output.  Primarily used for error messages. |
| `outputs[].enabled` | - | `true` | Toggle transcoding for a given output.  Default is `false` and in the normal use case you'll set it to `true` for any album you want in a given target.  NB: Bulklift won't transcode an album unless its directory contains a manifest file, so setting `enabled=true` at the root level won't have an effect for dirs with no `.bulklift.yaml`. |
| `outputs[].sanitize_paths` | - | `vfat` | Translate output path to avoid special characters unsupported on vfat/fat32.  NB: sanitization is applied to the path generated from `config.target.album_dir` + the source track name but **not** to the path to your target tree specified in `outputs.<name>.path`. |
| `outputs[].formats` | Y | `['opus', 'mp3']` | List of codecs the output supports in order of precedence.  In the case of the example Bulklift will use existing .opus files if available then fall back to transcoding lossless -> opus, or if that isn't possible using an mp3 file.  Typically you'll set this once when defining the output.   |
| `outputs[].opus_bitrate`| - | `128k` | Bitrate to use for libopus.  Encoding is VBR so results are approximate. |
| `outputs[].lame_vbr`| - | `3` | VBR setting for libmp3lame.  Encoding is VBR so results are approximate. |
| `outputs[].aac_vbr`| - | `3` | VBR setting for libfdk_aac.  Encoding is VBR so results are approximate. |
| `outputs[].filters.include` | - | `["1-*.flac"]` | List of globs that audio files must match to be included.  Applied before any `exclude` filters.  Use a filter like `1*` to transcode only the first disc of a two-album set.  |
| `outputs[].filters.exclude` | - | `["*track_i_do_not_like.flac"]` | List of globs audio files must *not* match to be included.  Applied after `include` filters.  |
| `metadata.*`| Y | - | Mapping of metadata to use for the content.  To avoid repetition you can build this up level by level. |

Bulklift will interpolate environment variables used within paths, e.g. `${HOME}/media/target_devices/mp3_player`.


## File Naming
Output filenames are copied from the source with the extension changed.

Output directories are a little more complex.  I didn't want to rely on the source directory name (mine contain metadata about the format) so the output dir name is freshly generated from the metadata.  It defaults to `{genre}/{artist}/{year} {album}/`.



## Source Formats
Garbage in, garbage out.  While Bulklift will merrily transcode from anything your local ffmpeg supports it's best to use a lossless format like [FLAC](https://en.wikipedia.org/wiki/FLAC) for your sources.

If you can't get lossless audio for your source tree don't worry - a `copy` dummy codec is included which will copy the audio into your output tree without transcoding.  It is not recommended to transcode from one lossy format to another (e.g. mp3 -> opus) as this results in further loss of quality.


## Output Formats
The following codecs can be specified for targets:

| Label   | Codec  | Recommended quality | Notes  |
|---------|--------|--------|---------------------|
| [`opus`](https://en.wikipedia.org/wiki/Opus_%28audio_format%29)  | libopus  | [libopus](https://opus-codec.org/)  | 96k (electronic); 112k (other)  | A modern codec with better performance than mp3.  Supported by Android, VLC and most modern player software.  Definitely not supported by your shonky old mp3 player.  Always used in VBR mode.  |
| [`mp3`](https://en.wikipedia.org/wiki/MP3)  | libmp3lame  | 3 (electronic); 2 (other)  | The [lame](http://lame.sourceforge.net/) encoder producting the venerable mp3 format.  Quality levels are for VBR; see their [docs](http://lame.sourceforge.net/vbr.php). |
| `copy` | - | - | Copies audio from the source without transcoding.  Output will be the exact same bitrate and format as input.  Audio bitstream is still run through ffmpeg so we retain the potential to change metadata.  Use this if you don't have a lossless copy of the original and don't want to further reduce its quality.  |


## Tips & Tricks

-   Codecs shipped with LTS Linux distributions are often out of date.  For those still rapidly improving (e.g. libopus) this is a problem.  To transcode with the latest & greatest codecs you may wish to build your own ffmpeg binary.  My notes for doing this on Debian are [notes/ffmpeg.md](here).  Alternatively you might use one of [these](https://johnvansickle.com/ffmpeg/) static builds.


## Why?
Originally I'd rip CD's into mp3.  Nowadays disk space is cheap and audio players are good so I've switched to lossless.

Trouble is, not everything has the space (or even support) for lossless audio.  Those FLACs need transcoding into other formats to fit on devices.  With a handful of devices - each with different space and codec requirements - I found myself spending more time transcoding music than listening to it.  Not fun.

Time to automate the process.  There are plenty of library management apps already, but all of them embody someone else's idea of how to arrange a music library.

I value:

-   Simplicity.  It should be easy to understand, easy to extend for new formats and easy to fix when something goes wrong.
-   Robustness.  Hard to break, easy to fix when it does.
-   Transparency.  Metadata & settings should be editable with any text editor and stored alongside the music they refer to.
-   Configurability.  I want to tweak bitrates & formats for parts of my library (e.g. per genre) without having to manually specify them for each album.
-   Machine write-ability.  Presently I write my `.bulklift.yaml` manifests with vim, but in future I may write CLI tools for bulk-editing the config.
-   But most of all - never, ever having to do this job again.


## License / Contributing
GPLv3 / yes please.
