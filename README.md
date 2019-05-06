# Bulklift: A Bulk Transcoding Tool for Large Music Collections

It is the year 2019.  Most of humanity has switched to streaming their music from an entity known as "The Cloud".  Only a brave group of rebels holds out, clinging valiantly to their own music libraries but slowly losing the fight to manage them across multiple devices.

Fellow rebels - I bring you **Bulklift**, a simple tool to ease your burden.

Bulklift will walk a tree of source audio (arranged into albums), look for `.bulklift.yaml` files and follow the directions within to transcode selected albums with [ffmpeg](http://ffmpeg.org/).  If there's no `.bulklift.yaml` in a directory it'll simply be ignored.

Features:

-  Generate multiple collections of output audio from a single source tree
-  Automatically add [replaygain](https://en.wikipedia.org/wiki/ReplayGain) tags to output files (presently using the excellent [r128gain](https://github.com/desbma/r128gain))
-  Inheritable, per-directory config system makes specifying settings a breeze
-  Toggle the output tree(s) a source album will be transcoded to.  Want 70s hair metal on your phone but not your laptop?  No problemo.
-  Copies album art (gif, png, jpg) unmolested to the output directory
-  Passthrough `copy` output format to get music onto your flac player
-  Multithreading (4x faster on my Raspberry Pi media server!)

Bulklift has approximately zero bells and whistles.  It doesn't try to be clever and decisions about metadata are left to the user.  It won't download misspellings of your favourite artist's name from CDDB and won't force strange genres from other people's tags upon your filesystem.  Never again will Taylor Swift darken your goth folder.

Bulklift is opinionated about the directory structure in which you store your music.  One album, one directory, one `.bulklift.yaml` with other settings inherited from directories above.  It doesn't care about directory names or how many levels there are in your directory tree above the album.

It only cares about filenames insomuch that the transcoder writes output files with the same name but a modified extension.


## Building
```plain
$ python3 -m venv venv
$ . venv/bin/activate      # or variant for your shell
$ pip3 install wheel
$ pip3 install -r requirements.txt
```
TBD: release binaries compiled with [PyInstaller](http://www.pyinstaller.org/), packages on [PyPi](https://pypi.org/).


## Running
```plain
$ ./code/bulklift /path/to/my/source_tree
```

## Common Operations

-   Regenerate an album (e.g. if your encoder has improved) - delete the directory from your output tree(s) and run bulklift again.


## Configuration
Yaml, nothing more.

Easiest to explain with an example.  My library looks like this:

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

The power of bulklift comes from its inheritable configuration system.  At every level in your source tree you can create a `.bulklift.yaml` overriding options from the previous.  In this case we:

-   At the top level set global config options (e.g. path to ffmpeg) and declare your target trees with default bitrates and formats for each.
-   At an intermediate level (`__AMBIENT`) a second `.bulklift.yaml` specifying metadata for the genre (`genre: Ambient`).
-   At the artist level, a third `.bulklift.yaml` specifying metadata for the artist (`artist: Super Xylophone Man`)
-   At the bottom level (the individual album) switch encoding on (`enabled: true`) for one or more targets and add metadata tags for the name and year of the album (`album: Greatest Hits` / `year: 2018`).

The key concept is that Bulklift merges the config of a directory with that of its parents.  The tip of the tree has precendence so you can override settings you set earlier.  Want to use a different build of ffmpeg for transcoding Dubstep?  Knock yourself out.

Examples showing use of the config tree are shown in [examples](examples/).


## File Naming
Output filenames are copied from the source with the extension changed.

Output directories are a little more complex.  I didn't want to rely on the source directory name (mine contain metadata about the format) so the output dir name is freshly generated from the metadata.  It defaults to `__{genre}/{artist}/{year} {album}/`.

If you don't like my naming scheme you can override it in each target's config.



## Source Formats
Garbage in, garbage out.  While Bulklift will merrily transcode from anything your local ffmpeg supports it's best to use a lossless format like [FLAC](https://en.wikipedia.org/wiki/FLAC) for your sources.

If you can't get lossless audio for your source tree don't worry - a `copy` dummy codec is included which will copy the audio into your output tree without transcoding.  It is not recommended to transcode from one lossy format to another (e.g. mp3 -> opus) as this results in further loss of quality.


## Output Formats
The following codecs can be specified for targets:

| Label   | Format  | Codec  | Recommended quality | Notes  |
|---------|---------|--------|---------------------|--------|
| `opus`  | [opus](https://en.wikipedia.org/wiki/Opus_%28audio_format%29) | libopus  | 96k (electronic); 112k (other)  | A modern codec with better performance than mp3.  Supported by Android, VLC and most modern player software.  Definitely not supported by your shonky old mp3 player. |
| `lame`  | [mp3](https://en.wikipedia.org/wiki/MP3)  | libmp3lame  | 3 (electronic); 2 (other)  | The [lame](http://lame.sourceforge.net/) encoder producting the venerable mp3 format.  Quality levels are for VBR; see their [docs](http://lame.sourceforge.net/vbr.php). |
| `copy`  | -  | - | - | Copies audio from the source without transcoding.  Output will be the exact same bitrate and format as input.  Use this if you don't have a lossless copy of the original and don't want to further reduce its quality.  |


## Tips & Tricks

-   Codecs shipped with LTS Linux distributions are often out of date.  For ones at a mature point in their lifecycle that isn't a problem; for those still getting regular improvements (e.g. libopus) it is.  To help Bulklift utilise the latest & greatest codecs you may want to build your own ffmpeg binary.  My notes for doing this on Debian are [notes/ffmpeg.md](here).


## Why?
Originally I'd rip CD's into mp3 - but now disk space is cheap and audio players are good so I've switched to lossless.

Trouble is, not everything has the space for lossless audio.  Those FLACs need to get converted into other formats to fit on devices.  The opus codec is fantastic but converting albums one at a time with a hacked-together bash script took forever.  And oh boy, next time we all switch to a magical new codec I'll have to do the lot again.  Not fun.

So I bowed to the inevitable and admitted I need a tool to (re)transcode lossless media into target trees.  There are plenty of library management apps about, but all of them embody someone else's idea of how to arrange a music library.  I've never come across one that suits my tastes.

I value:

-   Simplicity.  It should be easy to understand, easy to extend for new formats and easy to fix when something goes wrong.
-   Transparency.  Metadata & settings should be editable with any text editor and stored alongside the music they refer to.
-   Configurability.  I need a way to tweak bitrates & formats for parts of my library (e.g. per genre) without having to manually specify them for each album.
-   Machine write-ability.  Presently I write my `.bulklift.yaml` files in vim but in future I may want to update them with some automated tool.


## License / Contributing
GPLv3 / yes please.
