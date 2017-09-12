# pymimic

*pymimic* is a python wrapper for [mimic](http://github.com/MycroftAI/mimic/) and provides an easy way to synthesize speech from text.

It is currently highly recommended that pymimic is installed in virtualenv due to the early state of the project.

## Dependencies

*pymimic* requires an installation of mimic-core to work (with plugins if desired). The
default search paths are

- System library paths
- $VIRTUAL_ENV/lib
- $VIRTUAL_ENV/usr/lib

Search order can be changed by modifying `pymimic.lib_paths`.

### Get mimic

```
git clone git@github.com:MycroftAI/mimic-core.git
```

### Install mimic in the virtual environment

```
meson builddir mimic-core --prefix="$VIRTUAL_ENV" --libdir="lib"
ninja -C builddir test install
```

### Install pymimic

```sh
git clone https://github.com/forslund/pymimic
cd pymimic
./setup.py install
```

### Use pymimic
To use pymimic you will need to activate the virtual environment and set `LD_LIBRARY_PATH`.

```sh
export LD_LIBRARY_PATH="${VIRTUAL_ENV}/lib" # LD_LIBRARY_PATH is not set by activate
source ${VIRTUAL_ENV}/bin/activate
```

