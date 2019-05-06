# Building ffmpeg

...is a whole field of its own.

To run on a Raspberry Pi:

## libopus, for latest opus codec
```
git clone https://github.com/xiph/opus.git
cd opus
./autogen.sh
./configure --with-NE10-includes=/usr/include/ne10 --with-NE10-libraries=/usr/lib/arm-linux-gnueabihf
make -j3
make install   # to /usr/local/..., so need to point ffmpeg there
```

## ffmpeg
Static binary for a Raspberry Pi 2 or above (these [notes](https://maniaclander.blogspot.com/2017/08/ffmpeg-with-pi-hardware-acceleration.html) were helpful):

```
apt install \
  build-essential yasm \
  libomxil-bellagio-dev libomxil-bellagio-bin libmp3lame-dev

env LD_LIBRARY_PATH=/usr/local/lib:/usr/lib C_INCLUDE_PATH=/usr/local/include:/usr/include  \
./configure \
  --disable-ffplay --disable-ffprobe --disable-debug \
  --arch=armhf --enable-omx --enable-omx-rpi \
  --enable-nonfree --enable-gpl \
  --enable-decoder=flac --enable-decoder=libopus \
  --enable-demuxer=flac --enable-demuxer=ogg \
  --enable-muxer=opus --enable-muxer=mp3 \
  --enable-encoder=libmp3lame --enable-encoder=libopus \
  --enable-libmp3lame --enable-libopus

make -j4
make install  # to /usr/local/bin
```
