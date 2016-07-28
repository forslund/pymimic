# pymimic

*pymimic* is a python wrapper for [mimic](http://github.com/MycroftAI/mimic/) and provides an easy way to synthesize speech from text.

It is currently highly recommended that pymimic is installed in virtualenv due to the early state of the project.

## Dependencies

*pymimic* requires an installation of mimic to work, the installation can either be in the virtual environment used for pymimic or a systemwide installation.

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
