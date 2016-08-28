# pymimic

*pymimic* is a python wrapper for [mimic](http://github.com/MycroftAI/mimic/) and provides an easy way to synthesize speech from text.

It is currently highly recommended that pymimic is installed in virtualenv due to the early state of the project.

## Dependencies

*pymimic* requires an installation of mimic (configured with `--enable-shared`) to work. The default search paths are

- System library paths
- $VIRUTALENV/lib
- $VIRTUALENV/usr/lib

Search order can be changed by modifying `pymimic.lib_paths`.

### Get mimic

```
git clone git@github.com:MycroftAI/mimic.git
```

### Install mimic in the virtual environment

```
cd mimic
./configure --prefix=$VIRTUAL_ENV --enable-shared --with-audio=none --disable-voices-all
make
make install
```

### Install pymimic

```sh
git clone https://github.com/forslund/pymimic
cd pymimic
./setup.py install
```
