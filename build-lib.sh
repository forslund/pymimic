#! /usr/bin/env sh

CONFIG=./mimic/config/config
HOST_OS=`grep HOST_OS $CONFIG | sed -n -e 's/^.* //p'`
HOST_CPU=`grep HOST_CPU $CONFIG | sed -n -e 's/^.* //p'`
LIB_DIR=./mimic/build/$HOST_CPU-$HOST_OS/lib
gcc -shared -o libpymimic.so  -Wl,--whole-archive $LIB_DIR/libmimic_usenglish.shared.a $LIB_DIR/libmimic_cmu_grapheme_lang.shared.a $LIB_DIR/libmimic_cmu_grapheme_lex.shared.a $LIB_DIR/libmimic_cmulex.shared.a $LIB_DIR/libmimic.shared.a -Wl,--no-whole-archive
#gcc -shared -o libmimic.so ./speech/*.o synth/cst_ffeatures.o synth/cst_phoneset.o synth/cst_synth.o synth/cst_utt_utils.o synth/cst_voice.o synth/mimic.o utils/*.o wavesynth/*.o regex/*.o hrg/*.o lexicon/*.o cg/*.o stats/*.o  -Wl,--whole-archive ../../lib/libmimic_usenglish.a ../../lib/libmimic_cmu_grapheme_lang.a ../../lib/libmimic_cmu_grapheme_lex.a ../../lib/libmimic_cmulex.a -Wl,--no-whole-archive
