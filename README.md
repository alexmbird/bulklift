# Bulklift: A Bulk Transcoding Tool for Large Music Collections

It is the year 2019.  Most of humanity has switched to streaming their music from an entity known as "The Cloud".  A brave group of rebels hold out, clinging valiantly to their own music libraries but struggling ever harder to sync them across multiple devices.

Rebels - I bring you a tool to ease your burden.  **Bulklift**.

Bulklift walks your music library looking for `.bulklift.yaml` manifests.  It follows the instructions within to transcode any music that's in the same directory.

Features:

-  [ffmpeg](http://ffmpeg.org/) for transcoding
-  Generate multiple collections of output audio from a single source tree
-  Automatically add [replaygain](https://en.wikipedia.org/wiki/ReplayGain) tags to output files using the excellent [r128gain](https://github.com/desbma/r128gain)
-  Inheritable, per-directory config system makes it a breeze to setup
-  Manifests are just text files stored alongside your music; no database to corrupt or lose
-  Toggle the output tree(s) a source album will be transcoded to.  Want only half of Lady Gaga's albums on your phone?  With each at a different bitrate?  Done.
-  Copies album art (gif, png, jpg) unmolested to the output directory
-  Passthrough `copy` format to copy files without re-encoding
-  Multithreading (4x faster on my Raspberry Pi media server)

Bulklift has approximately zero bells and whistles.  It doesn't try to be clever and decisions about metadata are left to the user.  It won't download misspellings of your favourite artist's name from CDDB and won't force strange genres from other people's tags upon your filesystem.  Never again will Taylor Swift darken your goth folder.

Bulklift is opinionated about the directory structure you keep your music in.  One album, one directory, one `.bulklift.yaml` with other settings inherited from directories above.  It doesn't care about directory names or how many levels there are in your directory tree above the album.

Filenames are simply reused, but with the extension changed to match the output format.


## Building
```plain
$ python3 -m venv venv
$ . venv/bin/activate      # or variant for your shell
$ pip3 install wheel
$ pip3 install -r requirements.txt
```
TBD: release binaries compiled with [PyInstaller](http://www.pyinstaller.org/), packages on [PyPi](https://pypi.org/).


## Testing
```plain
$ python3 -m unittest discover code/
```

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

-   **Regenerate an album** (e.g. if your encoder has improved) - delete the directory from your output tree(s) and run `bulklift transcode` again.
-   **Edit a manifest** - `bulklift edit [path to dir]`.  Default is the current directory.  If no `.bulklift.yaml` exists Bulklift will intelligently generate a template based on the directory's contents and the manifests of its ancestors.


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
2.   At an intermediate level (`__AMBIENT`) a second `.bulklift.yaml` manifest specifying metadata for the genre (`genre: Ambient`).
3.   At the artist level, a third `.bulklift.yaml` specifying metadata for the artist (`artist: Super Xylophone Man`)
4.   At the bottom level (the individual album) switch encoding on (`enabled: true`) for one or more targets and add metadata tags for the name and year of the album (`album: Greatest Hits` / `year: 2018`).

The key concept is that Bulklift merges the the manifest of any directory with those of its parents.  The deepest manifest (i.e. the one in the dir with your music) has precendence so you can override settings from parent directories.  Want to use a different build of ffmpeg to transcode your Dubstep collection?  Override the artist for one particular collaboration album?  The world is your oyster.

Some of the more common options...

| Key        | Required | Example | Meaning |
|------------|----------|---------|---------------------|
| `root`     | Y        | `true`  | Signifies the root directory of your source tree.  Bulklift won't search for any manifests above this.  Must be present **only** in the root manifest; anywhere else and BL will get confused.  |
| `config.binaries.ffmpeg` | - | `${HOME}/.local/bin/ffmpeg` | Ffmpeg binary to use.  Often this is of value when you want to transcode with a more recent build than the one shipped with your OS.  Default is to search your path. |
| `config.binaries.r128gain` | - | `${HOME}/.local/bin/r128gain` | [r128gain](https://github.com/desbma/r128gain) binary to use.  Default is to search your path. |
| `outputs`  | -        | `{}`    | Map of outputs BL _may_ transcode to.  While typically (but not necessarily) defined in your root manifest they only take effect for albums in which their `enabled` flag is set to `true`. |
| `outputs.<name>.enabled` | - | `true` | Toggle transcoding for a given output.  Default is `false` and in the normal use case you'll set it to `true` for any album you want in a given target.  You could also set it `true` in the root manifest (to transcode absolutely everything for a given target) or at an intermediate level (i.e. "give me everything for this specific artist"). |
| `outputs.<name>.codec`| Y | `copy`, `opus` | Codec to use when transcoding objects described by this manifest.  Typically you'll set this once when defining the output.  However you may want to override it in some cases, e.g. to copy mp3 audio rather than re-transcoding it to opus. |
| `outputs.<name>.opus_bitrate`| - | `128k` | Bitrate to use for libopus.  Encoding is VBR so results are approximate. |
| `outputs.<name>.lame_vbr`| - | `3` | VBR setting for libmp3lame.  Encoding is VBR so results are approximate. |
| `metadata.*`| Y | - | Mapping of metadata to use for the content.  To avoid repetition you can build this up level by level - see the [examples](examples/) for how. |

Bulklift will interpolate environment variables used within paths, e.g. `${HOME}/media/target_devices/mp3_player`.

Examples showing use of the config tree are shown in [examples](examples/).


## File Naming
Output filenames are copied from the source with the extension changed.

Output directories are a little more complex.  I didn't want to rely on the source directory name (mine contain metadata about the format) so the output dir name is freshly generated from the metadata.  It defaults to `{genre}/{artist}/{year} {album}/`.



## Source Formats
Garbage in, garbage out.  While Bulklift will merrily transcode from anything your local ffmpeg supports it's best to use a lossless format like [FLAC](https://en.wikipedia.org/wiki/FLAC) for your sources.

If you can't get lossless audio for your source tree don't worry - a `copy` dummy codec is included which will copy the audio into your output tree without transcoding.  It is not recommended to transcode from one lossy format to another (e.g. mp3 -> opus) as this results in further loss of quality.


## Output Formats
The following codecs can be specified for targets:

| Label   | Format  | Codec  | Recommended quality | Notes  |
|---------|---------|--------|---------------------|--------|
| `opus`  | [opus](https://en.wikipedia.org/wiki/Opus_%28audio_format%29) | libopus  | 96k (electronic); 112k (other)  | A modern codec with better performance than mp3.  Supported by Android, VLC and most modern player software.  Definitely not supported by your shonky old mp3 player.  Always used in VBR mode.  |
| `lame`  | [mp3](https://en.wikipedia.org/wiki/MP3)  | libmp3lame  | 3 (electronic); 2 (other)  | The [lame](http://lame.sourceforge.net/) encoder producting the venerable mp3 format.  Quality levels are for VBR; see their [docs](http://lame.sourceforge.net/vbr.php). |
| `copy`  | -  | - | - | Copies audio from the source without transcoding.  Output will be the exact same bitrate and format as input.  Content is still run through ffmpeg so we retain the potential to change metadata.  Use this if you don't have a lossless copy of the original and don't want to further reduce its quality.  |


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
