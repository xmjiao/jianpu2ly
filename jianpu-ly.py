#!/usr/bin/env python

# Jianpu (numbered musical notation) for Lilypond
# v1.731 (c) 2012-2023 Silas S. Brown

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Homepage: http://ssb22.user.srcf.net/mwrhome/jianpu-ly.py
# Git repository: https://github.com/ssb22/jianpu-ly
# and on GitLab: https://gitlab.com/ssb22/jianpu-ly
# and on Bitbucket: https://bitbucket.org/ssb22/jianpu-ly
# and at https://gitlab.developers.cam.ac.uk/ssb22/jianpu-ly
# and in China: https://gitee.com/ssb22/jianpu-ly

# (The following doc string's format is fixed, see --html)
r"""Run jianpu-ly < text-file > ly-file (or jianpu-ly text-files > ly-file)
Text files are whitespace-separated and can contain:
Scale going up: 1 2 3 4 5 6 7 1'
Accidentals: 1 #1 2 b2 1
Octaves: 1,, 1, 1 1' 1''
Shortcuts for 1' and 2': 8 9
Change base octave: < >
Semiquaver, quaver, crotchet (16/8/4th notes): s1 q1 1
Dotted versions of the above (50% longer): s1. q1. 1.
Demisemiquaver, hemidemisemiquaver (32/64th notes): d1 h1
Minims (half notes) use dashes: 1 -
Dotted minim: 1 - -
Semibreve (whole note): 1 - - -
Time signature: 4/4
Time signature with quaver anacrusis (8th-note pickup): 4/4,8
Key signature (major): 1=Bb
Key signature (minor): 6=F#
Tempo: 4=85
Lyrics: L: here are the syl- la- bles (all on one line)
Lyrics (verse 1): L: 1. Here is verse one
Lyrics (verse 2): L: 2. Here is verse two
Hanzi lyrics (auto space): H: hanzi (with or without spaces)
Lilypond headers: title=the title (on a line of its own)
Multiple parts: NextPart
Instrument of current part: instrument=Flute (on a line of its own)
Multiple movements: NextScore
Prohibit page breaks until end of this movement: OnePage
Suppress bar numbers: NoBarNums
Old-style time signature: SeparateTimesig 1=C 4/4
Indonesian 'not angka' style: angka
Add a Western staff doubling the tune: WithStaff
Tuplets: 3[ q1 q1 q1 ]
Grace notes before: g[#45] 1
Grace notes after: 1 ['1]g
Simple chords: 135 1 13 1
Da capo: 1 1 Fine 1 1 1 1 1 1 DC
Repeat (with alternate endings): R{ 1 1 1 } A{ 2 | 3 }
Short repeats (percent): R4{ 1 2 }
Ties (like Lilypond's, if you don't want dashes): 1 ~ 1
Slurs (like Lilypond's): 1 ( 2 )
Erhu fingering (applies to previous note): Fr=0 Fr=4
Erhu symbol (applies to previous note): souyin harmonic up down bend tilde
Tremolo: 1/// - 1///5 -
Rehearsal letters: letterA letterB
Multibar rest: R*8
Dynamics (applies to previous note): \p \mp \f
Other 1-word Lilypond \ commands: \fermata \> \! \( \) etc
Text: ^"above note" _"below note"
Other Lilypond code: LP: (block of code) :LP (each delimeter at start of its line)
Unicode approximation instead of Lilypond: Unicode
Ignored: % a comment
"""

import sys
import os
import re
import shutil
import argparse
import requests
import subprocess
import six

from fractions import Fraction as F  # requires Python 2.6+
from string import ascii_letters as letters
from subprocess import getoutput

unichr, xrange = chr, range

# Control options
bar_number_every = 1
midiInstrument = "choir aahs"  # see  https://lilypond.org/doc/v2.24/Documentation/notation/midi-instruments


def asUnicode(l):
    if isinstance(l, six.text_type):
        return l
    return l.decode("utf-8")


def lilypond_minor_version():
    global _lilypond_minor_version
    try:
        return _lilypond_minor_version
    except:
        pass
    cmd = lilypond_command()
    if cmd:
        m = re.match(r".*ond-2\.([1-9][0-9])\.", cmd)
        if m:
            _lilypond_minor_version = int(m.group(1))
        else:
            _lilypond_minor_version = int(
                getoutput(cmd + " --version").split()[2].split(".")[1]
            )
    else:
        _lilypond_minor_version = 20  # 2.20
    return _lilypond_minor_version


def lilypond_command():
    if hasattr(shutil, "which"):
        w = shutil.which("lilypond")
        if w:
            return "lilypond"
    elif not sys.platform.startswith("win"):
        cmd = getoutput("which lilypond 2>/dev/null")
        if os.path.exists(cmd):
            return "lilypond"
        # e.g. from Mac OS 10.4-10.14 Intel build https://web.archive.org/web/20221121202056/https://lilypond.org/download/binaries/darwin-x86/lilypond-2.22.2-1.darwin-x86.tar.bz2 (unpacked and moved to /Applications), or similarly 2.20 for macOS 10.15+ from https://gitlab.com/marnen/lilypond-mac-builder/-/package_files/9872804/download
        placesToTry = ["/Applications/LilyPond.app/Contents/Resources/bin/lilypond"]
        # if renamed from the above (try specific versions 1st, in case default is older)
        placesToTry = [
            "/Applications/LilyPond-2.22.2.app/Contents/Resources/bin/lilypond",
            "/Applications/LilyPond-2.20.0.app/Contents/Resources/bin/lilypond",
        ] + placesToTry
        # if unpacked 2.24 (which drops the .app; in macOS 13, might need first to manually open at least lilypond and gs binaries for Gatekeeper approval if installing it this way)
        placesToTry += [
            "lilypond-2.24.0/bin/lilypond",
            "/opt/lilypond-2.24.0/bin/lilypond",
        ]
        for t in placesToTry:
            if os.path.exists(t):
                return t


def all_scores_start():
    staff_size = float(os.environ.get("j2ly_staff_size", 20))
    # Normal: j2ly_staff_size=20
    # Large: j2ly_staff_size=25.2
    # Small: j2ly_staff_size=17.82
    # Tiny: j2ly_staff_size=15.87
    r = (
        r"""\version "2.18.0"
#(set-global-staff-size %g)"""
        % staff_size
    )
    r += r"""

% un-comment the next line to remove Lilypond tagline:
\header { tagline=""}

\pointAndClickOff

\paper {
  print-all-headers = ##t %% allow per-score headers

  #(set-default-paper-size "letter" )
  #(set-paper-size "letter")

  % un-comment the next line for no page numbers:
  % print-page-number = ##f

  % un-comment the next 3 lines for a binding edge:
  % two-sided = ##t
  % inner-margin = 25\mm
  % outer-margin = 25\mm
  left-margin = 25\mm
  right-margin = 25\mm
"""
    if (
        os.path.exists("/Library/Fonts/Arial Unicode.ttf")
        and lilypond_minor_version() >= 20
    ):
        r += r"""
  % As jianpu-ly was run on a Mac, we include a Mac fonts workaround.
  % The Mac version of Lilypond 2.18 used Arial Unicode MS as a
  % fallback even in the Serif font, but 2.20 drops this in Serif
  % (using it only in Sans), which means any Serif text (titles,
  % lyrics etc) that includes Chinese will likely fall back to
  % Japanese fonts which don't support all Simplified hanzi.
  % This brings back 2.18's behaviour on 2.20+
  % (you might have to comment it out to run this on 2.18)
  #(define fonts
    (set-global-fonts
     #:roman "Times New Roman,Arial Unicode MS"
     #:factor (/ staff-height pt 20)
    ))
"""
    if has_lyrics:
        r += r"""
  % Might need to enforce a minimum spacing between systems, especially if lyrics are
  % below the last staff in a system and numbers are on the top of the next
  system-system-spacing = #'((basic-distance . 7) (padding . 4) (stretchability . 1e7))
  score-markup-spacing = #'((basic-distance . 9) (padding . 4) (stretchability . 1e7))
  score-system-spacing = #'((basic-distance . 9) (padding . 4) (stretchability . 1e7))
  markup-system-spacing = #'((basic-distance . 2) (padding . 2) (stretchability . 0))
"""
    r += "}\n"  # end of \paper block
    return r


def score_start():
    ret = "\\score {\n"
    if midi:
        ret += "\\unfoldRepeats\n"
    ret += r"<< "
    if not notehead_markup.noBarNums and not midi:
        ret += (
            "\\override Score.BarNumber #'break-visibility = #end-of-line-invisible\n\\override Score.BarNumber #'Y-offset = #1\n\\set Score.barNumberVisibility = #(every-nth-bar-number-visible %d)"
            % bar_number_every
        )
    return ret


def score_end(**headers):
    ret = ">>\n"
    if headers:
        # since about Lilypond 2.7, music must come
        # before the header block if it's per-score
        ret += r"\header{" + "\n"
        for k, v in headers.items():
            if '"' not in v:
                v = '"' + v + '"'
            if k == "title" and "\\" not in v:
                v = r"\markup{\fontsize #3 " + v + "}"
            ret += k + "=" + v + "\n"
        ret += "}\n"

    if midi:
        # will be overridden by any \tempo command used later
        ret += (
            r'\midi { \context { \Score midiInstrument = "'
            + midiInstrument
            + r'" tempoWholesPerMinute = #(ly:make-moment 84 4)}}'
        )
        # ret += r'\midi { \context { \Score tempoWholesPerMinute = #(ly:make-moment 84 4)}}'
    elif notehead_markup.noBarNums:
        ret += r'\layout { indent = 0.0 \context { \Score \remove "Bar_number_engraver" } }'
    else:
        # ret += r"\layout{}"
        ret += r"\layout { indent = 0.0 \context { \Score \override TimeSignature.break-visibility = #'#(#f #t #t) } }"
    return ret + " }"


def uniqName():
    global uniqCount
    r = str(uniqCount)
    uniqCount += 1
    return r.translate((letters * 5)[:256])


def jianpu_voice_start(isTemp=0):
    if not isTemp and maxBeams >= 2:
        # sometimes needed if the semiquavers occur in isolation rather than in groups (TODO do we need to increase this for 3+ beams in some cases?)
        stemLenFrac = "0.5"
    else:
        stemLenFrac = "0"
    voiceName = uniqName()
    r = (r"""\new Voice="%s" {""" % voiceName) + "\n"
    r += r"""
    \override Beam #'transparent = ##f % (needed for LilyPond 2.18 or the above switch will also hide beams)
    """
    if not_angka:
        r += r"""
        \override Stem #'direction = #UP
        \override Tie #'staff-position = #-2.5
        \tupletDown"""
        stemLenFrac = str(0.4 + 0.2 * max(0, maxBeams - 1))
    else:
        r += (
            r"""\override Stem #'direction = #DOWN
        \override Tie #'staff-position = #2.5
        \override Beam.positions = #'(-1 . -1)
        \tupletUp"""
            + "\n"
        )

    r += rf"""
    \override Stem #'length-fraction = #{stemLenFrac}
    \override Beam #'beam-thickness = #0.1
    \override Beam #'length-fraction = #-0.5
    \override Voice.Rest #'style = #'neomensural %% this size tends to line up better (we'll override the appearance anyway)
    \override Accidental #'font-size = #-4
    \override TupletBracket #'bracket-visibility = ##t"""
    r += (
        "\n" + r"""\set Voice.chordChanges = ##t %% 2.19 bug workaround"""
    )  # LilyPond 2.19.82: \applyOutput docs say "called for every layout object found in the context Context at the current time step" but 2.19.x breaks this by calling it for ALL contexts in the current time step, hence breaking our WithStaff by applying our jianpu numbers to the 5-line staff too.  Obvious workaround is to make our function check that the context it's called with matches our jianpu voice, but I'm not sure how to do this other than by setting a property that's not otherwise used, which we can test for in the function.  So I'm 'commandeering' the "chordChanges" property (there since at least 2.15 and used by Lilypond only when it's in chord mode, which we don't use, and if someone adds a chord-mode staff then it won't print noteheads anyway): we will substitute jianpu numbers for noteheads only if chordChanges = #t.
    return r + "\n", voiceName


def jianpu_staff_start(inst=None, withStaff=False):
    # (we add "BEGIN JIANPU STAFF" and "END JIANPU STAFF" comments to make it easier to copy/paste into other Lilypond files)
    if withStaff:
        # we'll put the label on the 5-line staff (TODO: use StaffGroup or something?)
        inst = None
    if not_angka:
        r = r"""
%% === BEGIN NOT ANGKA STAFF ===
    \new RhythmicStaff \with {"""
    else:
        r = r"""
%% === BEGIN JIANPU STAFF ===
    \new RhythmicStaff \with {
    \consists "Accidental_engraver" """
    if inst:
        r += 'instrumentName = "' + inst + '"'
    if withStaff:
        r += r"""
   %% Limit space between Jianpu and corresponding-Western staff
   \override VerticalAxisGroup.staff-staff-spacing = #'((minimum-distance . 7) (basic-distance . 7) (stretchability . 0))
"""  # (whether this is needed or not depends on Lilypond version; 2.22 puts more space than 2.18,2.20.  Must set higher than 5, which sometimes gets collisions between beams in 2.20)
    r += r"""
    %% Get rid of the stave but not the barlines:
    \override StaffSymbol #'line-count = #0 %% tested in 2.15.40, 2.16.2, 2.18.0, 2.18.2, 2.20.0 and 2.22.2
    \override BarLine #'bar-extent = #'(-2 . 2) %% LilyPond 2.18: please make barlines as high as the time signature even though we're on a RhythmicStaff (2.16 and 2.15 don't need this although its presence doesn't hurt; Issue 3685 seems to indicate they'll fix it post-2.18)
    }
    { """
    j, voiceName = jianpu_voice_start()
    r += (
        j
        + r"""
    \override Staff.TimeSignature #'style = #'numbered
    \override Staff.Stem #'transparent = ##t
    """
    )
    return r, voiceName


def jianpu_staff_end():
    # \bar "|." is added separately if there's not a DC etc
    if not_angka:
        return "} }\n% === END NOT ANGKA STAFF ===\n"
    else:
        return "} }\n% === END JIANPU STAFF ===\n"


def midi_staff_start():
    return r"""
%% === BEGIN MIDI STAFF ===
    \new Staff { \new Voice="%s" {""" % (
        uniqName(),
    )


def midi_staff_end():
    return "} }\n% === END MIDI STAFF ===\n"


def western_staff_start(inst=None):
    r = r"""
%% === BEGIN 5-LINE STAFF ===
    \new Staff """
    if inst:
        r += r'\with { instrumentName = "' + inst + '" } '
    voiceName = uniqName()
    return (
        (
            r
            + r"""{
    \override Score.SystemStartBar.collapse-height = #11 %% (needed on 2.22)
    \new Voice="%s" {
    #(set-accidental-style 'modern-cautionary)
    \override Staff.TimeSignature #'style = #'numbered
    \set Voice.chordChanges = ##f %% for 2.19.82 bug workaround
"""
            % (voiceName,)
        ),
        voiceName,
    )


def western_staff_end():
    return "} }\n% === END 5-LINE STAFF ===\n"


def lyrics_start(voiceName):
    return r'\new Lyrics = "I%s" { \lyricsto "%s" { ' % (uniqName(), voiceName)


def lyrics_end():
    return "} }"


# Implement dash (-) continuations as invisible ties rather than rests; sometimes works better in awkward beaming situations
dashes_as_ties = True
# Implement short rests as notes (and if there are lyrics, creates temporary voices so the lyrics miss them); sometimes works better for beaming (at least in 2.15, 2.16 and 2.18)
use_rest_hack = True
if __name__ == "__main__" and "--noRestHack" in sys.argv:  # TODO: document
    use_rest_hack = False
    sys.argv.remove("--noRestHack")
assert not (
    use_rest_hack and not dashes_as_ties
), "This combination has not been tested"


def errExit(msg):
    if __name__ == "__main__":
        sys.stderr.write("Error: " + msg + "\n")
        sys.exit(1)
    else:
        raise Exception(msg)


def scoreError(msg, word, line):
    if len(word) > 60:
        word = word[:50] + "..."
    msg += " %s in score %d" % (word, scoreNo)
    if len(line) > 600:
        line = line[:500] + "..."
    if not word in line:
        pass  # above truncations caused problems
    elif "xterm" in os.environ.get("TERM", ""):  # use xterm underline escapes
        msg += "\n" + re.sub(
            r"(\s|^)" + re.escape(word) + r"(?=\s|$)",
            lambda m: m.group(1) + "\x1b[4m" + word + "\x1b[m",
            line,
        )
    elif re.match("[ -~]*$", line):  # all ASCII: we can underline the word with ^^s
        msg += (
            "\n"
            + line
            + "\n"
            + re.sub(
                "[^^]",
                " ",
                re.sub(
                    r"(\s|^)" + re.escape(word) + r"(?=\s|$)",
                    lambda m: m.group(1) + "^" * (len(word)),
                    line,
                ),
            )
        )
    else:  # don't try to underline the word (at least not without ANSI): don't know how the terminal will handle character widths
        msg += "\nin this line: " + line
    errExit(msg)


placeholders = {
    # for accidentals and word-fitting to work
    # (we make them relative to the actual key later
    # so that MIDI pitches are correct)
    "0": "r",
    "1": "c",
    "2": "d",
    "3": "e",
    "4": "f",
    "5": "g",
    "6": "a",
    "7": "b",
    "-": "r",
}


def addOctaves(octave1, octave2):
    # so it can be used with a base-octave change
    octave2 = octave2.replace(">", "'").replace("<", ",")
    while octave1:
        if octave1[0] in "'>":  # go up
            if "," in octave2:
                octave2 = octave2[:-1]
            else:
                octave2 += "'"
        else:  # , or < : go down
            if "'" in octave2:
                octave2 = octave2[:-1]
            else:
                octave2 += ","
        octave1 = octave1[1:]
    return octave2


class NoteheadMarkup:
    def __init__(self, withStaff=True):
        self.defines_done = {}
        self.withStaff = withStaff
        self.initOneScore()

    def initOneScore(self):
        self.barLength = 64
        self.beatLength = 16  # in 64th notes
        self.barPos = self.startBarPos = F(0)
        self.inBeamGroup = (
            self.lastNBeams
        ) = self.onePage = self.noBarNums = self.separateTimesig = 0
        self.keepLength = 0
        self.last_octave = self.base_octave = ""
        self.current_accidentals = {}
        self.barNo = 1
        self.tuplet = (1, 1)
        self.last_figures = None
        self.last_was_rest = False
        self.notesHad = []
        self.unicode_approx = []

    def endScore(self):
        if self.barPos == self.startBarPos:
            pass
        elif os.environ.get("j2ly_sloppy_bars", ""):
            sys.stderr.write(
                "Wrong bar length at end of score %d ignored (j2ly_sloppy_bars set)\n"
                % scoreNo
            )
        elif self.startBarPos and not self.barPos:
            # this is on the music theory syllabi at about Grade 3, but you can get up to Grade 5 practical without actually covering it, so we'd better not expect all users to understand "final bar does not make up for anacrusis bar"
            errExit(
                "Score %d should end with a %g-beat bar to make up for the %g-beat anacrusis bar.  Set j2ly_sloppy_bars environment variable if you really want to break this rule."
                % (
                    scoreNo,
                    self.startBarPos / self.beatLength,
                    (self.barLength - self.startBarPos) / self.beatLength,
                )
            )
        else:
            errExit(
                "Incomplete bar at end of score %d (pos %d)" % (scoreNo, self.barPos)
            )

    def setTime(self, num, denom):
        self.barLength = int(64 * num / denom)
        if denom > 4 and num % 3 == 0:
            self.beatLength = 24  # compound time
        else:
            self.beatLength = 16

    def setAnac(self, denom, dotted):
        self.barPos = F(self.barLength) - F(64) / denom
        if dotted:
            self.barPos -= F(64) / denom / 2
        if self.barPos < 0:
            # but anacrusis being exactly equal to bar is OK: we'll just interpret that as no anacrusis
            errExit("Anacrusis is longer than bar in score %d" % scoreNo)
        self.startBarPos = self.barPos

    def wholeBarRestLen(self):
        return {96: "1.", 48: "2.", 32: "2", 24: "4.", 16: "4", 12: "8.", 8: "8"}.get(
            self.barLength, "1"
        )  # TODO: what if irregular?

    def baseOctaveChange(self, change):
        self.base_octave = addOctaves(change, self.base_octave)

    def __call__(self, figures, nBeams, dots, octave, accidental, tremolo, word, line):
        # figures is a chord string of '1'-'7', or '0' or '-'
        # nBeams is 0, 1, 2 .. etc (number of beams for this note)
        # dots is "" or "." or ".." etc (extra length)
        # octave is "", "'", "''", "," or ",,"
        # accidental is "", "#", "b"
        # tremolo is "" or ":32"
        # word,line is for error handling

        if len(figures) > 1:
            if accidental:
                # see TODOs below
                scoreError("Accidentals in chords not yet implemented:", word, line)
            if "0" in figures:
                scoreError("Can't have rest in chord:", word, line)
        self.notesHad.append(figures)
        names = {
            "0": "nought",
            "1": "one",
            "2": "two",
            "3": "three",
            "4": "four",
            "5": "five",
            "6": "six",
            "7": "seven",
            "-": "dash",
        }

        def get_placeholder_chord(figures):
            if len(figures) == 1:
                return placeholders[figures]
            elif not midi and not western:
                return "c"  # we'll override its appearance
            else:
                return "< " + " ".join(placeholders[f] for f in list(figures)) + " >"

        placeholder_chord = get_placeholder_chord(figures)
        invisTieLast = (
            dashes_as_ties
            and self.last_figures
            and figures == "-"
            and not self.last_was_rest
        )
        self.last_was_rest = figures == "0" or (figures == "-" and self.last_was_rest)
        name = "".join(names[f] for f in figures)
        if not_angka:
            # include accidental in the lookup key
            # because it affects the notehead shape
            figures += accidental  # TODO: chords?
            name += {"#": "-sharp", "b": "-flat", "": ""}[accidental]
        if invisTieLast:  # (so figures == "-")
            figures += self.last_figures  # (so "-" + last)
            name += "".join(names[f] for f in self.last_figures)
            placeholder_chord = get_placeholder_chord(self.last_figures)
            octave = self.last_octave  # for MIDI or 5-line
            accidental = self.last_accidental  # ditto
        else:
            octave = addOctaves(octave, self.base_octave)
            if not octave in [",,", ",", "", "'", "''"]:
                scoreError("Can't handle octave " + octave + " in", word, line)
            self.last_octave = octave
        self.last_figures = figures
        if len(self.last_figures) > 1 and self.last_figures[0] == "-":
            self.last_figures = self.last_figures[1:]
        if not accidental in ["", "#", "b"]:
            scoreError("Can't handle accidental " + accidental + " in", word, line)
        self.last_accidental = accidental
        if figures not in self.defines_done and not midi and not western:
            # Define a notehead graphical object for the figures
            self.defines_done[figures] = "note-" + name
            if figures.startswith("-"):
                if not_angka:
                    figuresNew = "."
                else:
                    figuresNew = "\u2013"
                    if not isinstance("", six.text_type):
                        figuresNew = figuresNew.encode("utf-8")
            else:
                figuresNew = figures
            ret = (
                """#(define (%s grob grob-origin context)
  (if (and (eq? (ly:context-property context 'chordChanges) #t)
      (or (grob::has-interface grob 'note-head-interface)
        (grob::has-interface grob 'rest-interface)))
    (begin
      (ly:grob-set-property! grob 'stencil
        (grob-interpret-markup grob
          """
                % self.defines_done[figures]
            )
            if len(figuresNew) == 1 or figures.startswith("-"):
                ret += (
                    """(make-lower-markup 0.5 (make-bold-markup "%s")))))))
"""
                    % figuresNew
                )
            elif not_angka and accidental:  # not chord
                # TODO: the \ looks better than the / in default font
                u338, u20e5 = "\u0338", "\u20e5"
                if not isinstance("", six.text_type):
                    u338, u20e5 = u338.encode("utf-8"), u20e5.encode("utf-8")
                ret += '(make-lower-markup 0.5 (make-bold-markup "%s%s")))))))\n' % (
                    figures[:1],
                    {"#": u338, "b": u20e5}[accidental],
                )
            else:
                ret += (
                    """(markup (#:lower 0.5
          (#:override (cons (quote direction) 1)
          (#:override (cons (quote baseline-skip) 1.8)
          (#:dir-column (\n"""
                    + "".join('    #:line (#:bold "' + f + '")\n' for f in figuresNew)
                    + """)))))))))))
"""
                )  # TODO: can do accidentals e.g. #:halign 1 #:line ((#:fontsize -5 (#:raise 0.7 (#:flat))) (#:bold "3")) but might cause the beam not to extend its full length if this chord occurs at the end of a beamed group, + accidentals won't be tracked by Lilypond and would have be taken care of by jianpu-ly (which might mean if any chord has an accidental on one of its notes we'd have to do all notes in that bar like this, whether they are chords or not)
        else:
            ret = ""
        if self.barPos == 0 and self.barNo > 1:
            ret += "| "  # barline in Lilypond file: not strictly necessary but may help readability
            if self.onePage and not midi:
                ret += r"\noPageBreak "
            ret += "%{ bar " + str(self.barNo) + ": %} "
        if octave not in self.current_accidentals:
            self.current_accidentals[octave] = [""] * 7
        if nBeams == None:  # unspecified
            if self.keepLength:
                nBeams = self.lastNBeams
            else:
                nBeams = 0
        if (
            figures == "-"
            or all(
                "1" <= figure <= "7"
                and not accidental == self.current_accidentals[octave][int(figure) - 1]
                for figure in list(figures)
            )
            and nBeams > self.lastNBeams
        ):
            leftBeams = nBeams  # beam needs to fit under the new accidental (or the dash which might be slightly to the left of where digits are), but if it's no more than last note's beams then we'll hang it only if in same beat.  (TODO: the current_accidentals logic may need revising if other accidental styles are used, e.g. modern-cautionary, although then would need to check anyway if our \consists "Accidental_engraver" is sufficient)
        # TODO: if figures=="0" then that might be typeset a bit to the left as well (because it's also a rest), however extending the line TOO far left in this case could be counterproductive
        elif self.inBeamGroup:
            if nBeams < self.lastNBeams:
                leftBeams = nBeams
            else:
                leftBeams = self.lastNBeams
        else:
            leftBeams = 0
        if leftBeams:
            assert (
                nBeams
            ), "following logic assumes if (leftBeams or nBeams) == if nBeams"
        aftrlast0 = ""
        if not nBeams and self.inBeamGroup:
            if not self.inBeamGroup == "restHack":
                aftrlast0 = "] "
            self.inBeamGroup = 0
        length = 4
        b = 0
        toAdd = F(16)  # crotchet
        while b < nBeams:
            b, length, toAdd = b + 1, length * 2, toAdd / 2
        toAdd0 = toAdd
        for _ in dots:
            toAdd0 /= 2
            toAdd += toAdd0
        toAdd_preTuplet = toAdd
        if not self.tuplet[0] == self.tuplet[1]:
            toAdd = toAdd * self.tuplet[0] / self.tuplet[1]
        # must set these unconditionally regardless of what we think their current values are (Lilypond's own beamer can change them from note to note)
        if nBeams and not midi and not western:
            if not_angka:
                leftBeams = nBeams
                if (self.barPos + toAdd) % self.beatLength == 0:
                    nBeams = 0
            ret += (r"\set stemLeftBeamCount = #%d" + "\n") % leftBeams
            ret += (r"\set stemRightBeamCount = #%d" + "\n") % nBeams
            if not_angka:
                nBeams = leftBeams
        need_space_for_accidental = False
        for figure in list(figures):
            if "1" <= figure <= "7":
                if not accidental == self.current_accidentals[octave][int(figure) - 1]:
                    need_space_for_accidental = True
                # TODO: not sensible (assumes accidental applies to EVERY note in the chord, see above)
                self.current_accidentals[octave][int(figure) - 1] = accidental
        inRestHack = 0
        if not midi and not western:
            if ret:
                ret = ret.rstrip() + "\n"  # try to keep the .ly code vaguely readable
            if octave == "''" and not invisTieLast:
                # inside bar numbers etc
                ret += r"  \once \override Score.TextScript.outside-staff-priority = 45"
            ret += r"  \applyOutput #'Voice #" + self.defines_done[figures] + " "
            if placeholder_chord == "r" and use_rest_hack and nBeams:
                placeholder_chord = "c"
                # C to work around diagonal-tail problem with
                # some isolated quaver rests in some Lilypond
                # versions (usually at end of bar); new voice
                # so lyrics miss it as if it were a rest:
                # (OK if self.withStaff: lyrics will be attached to that instead)
                if has_lyrics and not self.withStaff:
                    ret = jianpu_voice_start(1)[0] + ret
                    inRestHack = 1
                    if self.inBeamGroup and not self.inBeamGroup == "restHack":
                        aftrlast0 = "] "
        if placeholder_chord.startswith("<"):
            # Octave with chords: apply to last note if up, 1st note if down
            notes = placeholder_chord.split()[1:-1]
            assert len(notes) >= 2
            notes[0] += {",": "", ",,": ","}.get(octave, "'")
            for n in range(1, len(notes) - 1):
                notes[n] += "'"
            notes[-1] += {"'": "''", "''": "'''"}.get(octave, "'")
            ret += "< " + " ".join(notes) + " >"
        else:  # single note or rest
            ret += placeholder_chord + {"": "", "#": "is", "b": "es"}[accidental]
            if not placeholder_chord == "r":
                ret += {"": "'", "'": "''", "''": "'''", ",": "", ",,": ","}[
                    octave
                ]  # for MIDI + Western, put it so no-mark starts near middle C
        ret += ("%d" % length) + dots
        if tremolo:
            if lilypond_minor_version() < 20:
                errExit(
                    "tremolo requires Lilypond 2.20+, we found 2."
                    + str(lilypond_minor_version())
                )
            if midi or western:
                if (
                    placeholder_chord.startswith("<")
                    and len(placeholder_chord.split()) == 4
                ):
                    previous, n1, n2, gtLenDot = ret.rsplit(None, 3)
                    previous = previous[:-1]  # drop <
                    ret = r"%s\repeat tremolo %d { %s32 %s32 }" % (
                        previous,
                        int(toAdd_preTuplet / 4),
                        n1,
                        n2,
                    )
                else:
                    ret += tremolo
            elif lilypond_minor_version() >= 22:
                if dots:
                    ret += r"""_\tweak outside-staff-priority ##f ^\tweak avoid-slur #'inside _\markup {\with-dimensions #'(0 . 0) #'(2.8 . 2.1) \postscript "1.6 -0.2 moveto 2.6 0.8 lineto 1.8 -0.4 moveto 2.8 0.6 lineto 2.0 -0.6 moveto 3.0 0.4 lineto stroke" } %{ requires Lilypond 2.22+ %} """
                else:
                    ret += r"""_\tweak outside-staff-priority ##f ^\tweak avoid-slur #'inside _\markup {\with-dimensions #'(0 . 0) #'(2.5 . 2.1) \postscript "1.1 0.4 moveto 2.1 1.4 lineto 1.3 0.2 moveto 2.3 1.2 lineto 1.5 0.0 moveto 2.5 1.0 lineto stroke" } %{ requires Lilypond 2.22+ %} """
            elif dots:
                ret += r"""_\tweak outside-staff-priority ##f ^\tweak avoid-slur #'inside _\markup {\with-dimensions #'(0 . 0) #'(2.8 . 2.6) \postscript "1.4 1.6 moveto 2.4 2.6 lineto 1.6 1.4 moveto 2.6 2.4 lineto 1.8 1.2 moveto 2.8 2.2 lineto stroke" } %{ requires Lilypond 2.20 %} """
            else:
                ret += r"""_\tweak outside-staff-priority ##f ^\tweak avoid-slur #'inside _\markup {\with-dimensions #'(0 . 0) #'(2.5 . 2.6) \postscript "1.1 1.6 moveto 2.1 2.6 lineto 1.3 1.4 moveto 2.3 2.4 lineto 1.5 1.2 moveto 2.5 2.2 lineto stroke" } %{ requires Lilypond 2.20 %} """
        if (
            nBeams
            and (not self.inBeamGroup or self.inBeamGroup == "restHack" or inRestHack)
            and not midi
            and not western
        ):
            # We need the above stemLeftBeamCount, stemRightBeamCount override logic to work even if we're an isolated quaver, so do this:
            ret += "["
            self.inBeamGroup = 1
        self.barPos += toAdd
        # sys.stderr.write(accidental+figure+octave+dots+"/"+str(nBeams)+"->"+str(self.barPos)+" ") # if need to see where we are
        if self.barPos > self.barLength:
            errExit(
                '(notesHad=%s) barcheck fail: note crosses barline at "%s" with %d beams (%d skipped from %d to %d, bypassing %d), scoreNo=%d barNo=%d (but the error could be earlier)'
                % (
                    " ".join(self.notesHad),
                    figures,
                    nBeams,
                    toAdd,
                    self.barPos - toAdd,
                    self.barPos,
                    self.barLength,
                    scoreNo,
                    self.barNo,
                )
            )
        # (self.inBeamGroup is set only if not midi/western)
        if self.barPos % self.beatLength == 0 and self.inBeamGroup:
            # jianpu printouts tend to restart beams every beat
            # (but if there are no beams running anyway, it occasionally helps typesetting to keep the logical group running, e.g. to work around bugs involving beaming a dash-and-rest beat in 6/8) (TODO: what if there's a dash-and-rest BAR?  [..]-notated beams don't usually work across barlines
            ret += "]"
            # DON'T reset lastNBeams here (needed for start-of-group accidental logic)
            self.inBeamGroup = 0
        elif inRestHack and self.inBeamGroup:
            ret += "]"
            self.inBeamGroup = "restHack"
        self.lastNBeams = nBeams
        beamC = "\u0333" if nBeams >= 2 else "\u0332" if nBeams == 1 else ""
        self.unicode_approx.append(
            ""
            + ("-" if invisTieLast else figures[-1:])
            + (
                ""
                if invisTieLast
                else ("\u0323" if "," in octave else "\u0307" if "'" in octave else "")
            )
            + beamC
            + "".join(c + beamC for c in dots)
            + ("" if self.inBeamGroup else " ")
        )  # (NB inBeamGroup is correct only if not midi and not western)
        if self.barPos == self.barLength:
            self.unicode_approx[-1] = self.unicode_approx[-1].rstrip() + "\u2502"
            self.barPos = 0
            self.barNo += 1
            self.current_accidentals = {}
        # Octave dots:
        if not midi and not western and not invisTieLast:
            # Tweak the Y-offset, as Lilypond occasionally puts it too far down:
            if not nBeams:
                ret += {
                    ",": r"-\tweak #'Y-offset #-1.2 ",
                    ",,": r"-\tweak #'Y-offset #1 ",
                }.get(octave, "")
            oDict = {
                "": "",
                "'": "^.",
                "''": r"-\tweak #'X-offset #0.3 ^\markup{\bold :}",
                ",": r"-\tweak #'X-offset #0.6 _\markup{\bold .}",
                ",,": r"-\tweak #'X-offset #0.3 _\markup{\bold :}",
            }
            if not_angka:
                oDict.update(
                    {
                        "'": r"-\tweak #'extra-offset #'(0.4 . 2.7) -\markup{\bold .}",
                        "''": r"-\tweak #'extra-offset #'(0.4 . 3.5) -\markup{\bold :}",
                    }
                )
            ret += oDict[octave]
        if invisTieLast:
            if midi or western:
                b4last, aftrlast = "", " ~"
            else:
                b4last, aftrlast = (
                    r"\once \override Tie #'transparent = ##t \once \override Tie #'staff-position = #0 ",
                    " ~",
                )
        else:
            b4last, aftrlast = "", ""
        if inRestHack:
            ret += " } "
        return (
            b4last,
            aftrlast0 + aftrlast,
            ret,
            need_space_for_accidental,
            nBeams,
            octave,
        )


def parseNote(word, origWord, line):
    if word == ".":
        # (for not angka, TODO: document that this is now acceptable as an input word?)
        word = "-"
    word = word.replace("8", "1'").replace("9", "2'")
    if isinstance("", six.text_type):
        word = word.replace("\u2019", "'")
    else:
        word = word.replace("\u2019".encode("utf-8"), "'")
    if "///" in word:
        tremolo, word = ":32", word.replace("///", "", 1)
    else:
        tremolo = ""
    # unrecognised stuff in it: flag as error, rather than ignoring and possibly getting a puzzling barsync fail
    if not re.match(r"[0-7.,'cqsdh\\#b-]+$", word):
        scoreError("Unrecognised command", origWord, line)
    figures = "".join(re.findall("[01234567-]", word))
    dots = "".join(c for c in word if c == ".")
    nBeams = "".join(re.findall(r"[cqsdh\\]", word))
    if re.match(r"[\\]+$", nBeams):
        nBeams = len(
            nBeams
        )  # requested by a user who found British note-length names hard to remember; won't work if the \ is placed at the start, as that'll be a Lilypond command, so to save confusion we won't put this in the docstring
    elif nBeams:
        try:
            nBeams = list("cqsdh").index(nBeams)
        except ValueError:
            scoreError(
                "Can't calculate number of beams from " + nBeams + " in", origWord, line
            )
    else:
        nBeams = None  # unspecified
    octave = "".join(c for c in word if c in "',")
    accidental = "".join(c for c in word if c in "#b")
    return figures, nBeams, dots, octave, accidental, tremolo


def write_docs():
    # Write an HTML or Markdown version of the doc string
    def htmlify(l):
        if "--html" in sys.argv:
            return l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        else:
            return l

    inTable = 0
    justStarted = 1
    for line in __doc__.split("\n"):
        if not line.strip():
            continue
        if ":" in line and line.split(":", 1)[1].strip():
            toGet, shouldType = line.split(":", 1)
            if not inTable:
                if "--html" in sys.argv:
                    # "<tr><th>To get:</th><th>Type:</th></tr>"
                    print("<table border>")
                else:
                    print("")
                inTable = 1
            if re.match(r".*[A-Za-z]\)$", shouldType):
                shouldType, note = shouldType.rsplit("(", 1)
                note = " (" + note
            else:
                note = ""
            if "--html" in sys.argv:
                print(
                    "<tr><td>"
                    + htmlify(toGet.strip())
                    + "</td><td><kbd>"
                    + htmlify(shouldType.strip())
                    + "</kbd>"
                    + htmlify(note)
                    + "</td>"
                )
            else:
                print(toGet.strip() + ": `" + shouldType.strip() + "`" + note + "\n")
        else:
            if "--markdown" in sys.argv:
                print("")
            elif inTable:
                print("</table>")
            elif not justStarted:
                print("<br>")
            inTable = justStarted = 0
            print(htmlify(line))
    if inTable and "--html" in sys.argv:
        print("</table>")


def merge_lyrics(content):
    """
    Merge all lines starting with "H:" in each part of the the given content (separated by "NextPart")
    and replaces the first "H:" line in each part with the merged line.

    Args:
        content (str): The content to process.

    Returns:
        str: The processed content.
    """

    def process_part(part):
        # Extract all lines starting with "H:" and merge them
        h_lines = re.findall(r"^H:.*$", part, re.MULTILINE)
        merged_line = "H:" + " ".join([line[2:].strip() for line in h_lines])

        # Replace the first "H:" line with the merged line and remove all other "H:" lines
        def replace_first_H(match):
            replace_first_H.first_encountered = True
            return merged_line

        replace_first_H.first_encountered = False
        part = re.sub(
            r"^H:.*$",
            lambda m: replace_first_H(m)
            if not replace_first_H.first_encountered
            else "",
            part,
            flags=re.MULTILINE,
        )

        return part

    # Split the content into parts based on "NextPart", process each part and join them back together
    parts = content.split("NextPart")
    processed_parts = [process_part(part) for part in parts]
    return "NextPart".join(processed_parts)


def getInput0(f, is_google_drive=False):
    inDat = []

    # Check if we are reading from Google Drive or a local file
    if is_google_drive:
        inDat.append(merge_lyrics(f))
    else:
        try:
            try:
                # Python 3: try UTF-8 first
                inDat.append(merge_lyrics(open(f, encoding="utf-8").read()))
            except FileNotFoundError:
                # Python 2, or Python 3 with locale-default encoding in case it's not UTF-8
                inDat.append(merge_lyrics(open(f).read()))
        except IOError:
            errExit("Unable to read file " + f)

    if inDat:
        return inDat
    if not sys.stdin.isatty():
        return [fix_utf8(sys.stdin, "r").read()]
    # They didn't give us any input.  Try to use a
    # file chooser.  If that fails, just print the
    # help text.
    if os.path.exists("/usr/bin/osascript"):
        f = (
            os.popen(
                "osascript -e $'tell application \"System Events\"\nactivate\nset f to choose file\nend tell\nPOSIX path of f'"
            )
            .read()
            .rstrip()
        )
        if f:
            try:
                return [open(f, encoding="utf-8").read()]
            except:
                return [open(f).read()]
    sys.stderr.write(__doc__)
    raise SystemExit


def get_input(infile, is_google_drive=False):
    """
    Reads input from a file and returns it as a string.

    Args:
        infile (str): The path to the input file.
        is_google_drive (bool, optional): Whether the input file is stored in Google Drive. Defaults to False.

    Returns:
        str: The input data as a string.
    """
    inDat = getInput0(infile, is_google_drive)

    for i in xrange(len(inDat)):
        if inDat[i].startswith("\xef\xbb\xbf"):
            inDat[i] = inDat[i][3:]
        if inDat[i].startswith(r"\version"):
            errExit(
                "jianpu-ly does not READ Lilypond code.\nPlease see the instructions."
            )

    return " NextScore ".join(inDat)


def fix_utf8(stream, mode):
    if isinstance(
        "", six.text_type
    ):  # Python 3: please use UTF-8 for Lilypond, even if the system locale says something else
        import codecs

        if mode == "r":
            return codecs.getreader("utf-8")(stream.buffer)
        else:
            return codecs.getwriter("utf-8")(stream.buffer)
    else:
        return stream


def fix_fullwidth(t):
    if isinstance("", six.text_type):
        utext = t
    else:
        utext = t.decode("utf-8")
    r = []
    for c in utext:
        if 0xFF01 <= ord(c) <= 0xFF5E:
            r.append(unichr(ord(c) - 0xFEE0))
        elif c == "\u201a":
            r.append(",")  # sometimes used as comma (incorrectly)
        elif c == "\uff61":
            r.append(".")
        else:
            r.append(c)
    utext = "".join(r)
    if isinstance("", six.text_type):
        return utext
    else:
        return utext.encode("utf-8")


def graceNotes_markup(notes, isAfter):
    if isAfter:
        cmd = "jianpu-grace-after"
    else:
        cmd = "jianpu-grace"
    r = []
    afternext = None
    thinspace = "\u2009"
    if not isinstance("", six.text_type):
        thinspace = thinspace.encode("utf-8")
    notes = grace_octave_fix(notes)
    for i in xrange(len(notes)):
        n = notes[i]
        if n == "#":
            r.append(r"\fontsize #-4 { \raise #0.6 { \sharp } }")
        elif n == "b":
            r.append(r"\fontsize #-4 { \raise #0.4 { \flat } }")
        elif n == "'":
            if i and notes[i - 1] == notes[i]:
                continue
            if notes[i : i + 2] == "''":
                above = ":"
            else:
                above = "."
            r.append(
                r"\override #'(direction . 1) \override #'(baseline-skip . 1.2) \dir-column { \line {"
            )
            afternext = r"} \line { " + '"' + thinspace + above + '" } }'
        elif n == ",":
            if i and notes[i - 1] == notes[i]:
                continue
            if notes[i : i + 2] == ",,":
                below = ":"
            else:
                below = "."
            r.append(r"\override #'(baseline-skip . 1.0) \center-column { \line { ")
            afternext = (
                r"} \line { \pad-to-box #'(0 . 0) #'(-0.2 . 0) " + '"' + below + '" } }'
            )
        else:
            if r and r[-1].endswith('"'):
                r[-1] = r[-1][:-1] + n + '"'
            else:
                r.append('"%s"' % n)
            if afternext:
                r.append(afternext)
                afternext = None
    return (
        r"^\tweak outside-staff-priority ##f ^\tweak avoid-slur #'inside ^\markup \%s { \line { %s } }"
        % (cmd, " ".join(r))
    )


def grace_octave_fix(notes):
    """
    This function takes a string of notes in jianpu notation and applies the following fixes:
    1. Moves '+ and ,+ to before the preceding number
    2. Replaces 8 and 9 with the respective higher octave notes

    Args:
    notes (str): A string of notes in jianpu notation

    Returns:
    str: A string of notes with the above fixes applied
    """

    # Move '+ and ,+ to before the preceding number
    notes = re.sub(r"([1-9])(')+", r"\2\1", notes)
    notes = re.sub(r"([1-9])(,)+", r"\2\1", notes)

    # Replacing 8 and 9 with the respective higher octave notes
    notes = notes.replace("8", "'1").replace("9", "'2")

    return notes


def gracenotes_western(notes):
    """
    Converts a list of Jiapu-style grace notes to LilyPond notation.

    Args:
    notes (list): A list of grace notes in Jianpu notation.

    Returns:
    str: A string of LilyPond notation representing the grace notes.
    """

    # for western and MIDI staffs
    notes = grace_octave_fix(notes)

    nextAcc = ""
    next8ve = "'"
    r = []
    for i in xrange(len(notes)):
        n = notes[i]
        if n == "#":
            nextAcc = "is"
        elif n == "b":
            nextAcc = "es"
        elif n == "'":
            if i and notes[i - 1] == notes[i]:
                continue
            if notes[i : i + 2] == "''":
                next8ve = "'''"
            else:
                next8ve = "''"
        elif n == ",":
            if i and notes[i - 1] == notes[i]:
                continue
            if notes[i : i + 2] == ",,":
                next8ve = ","
            else:
                next8ve = ""
        else:
            if n not in placeholders:
                continue  # TODO: errExit ?
            r.append(placeholders[n] + nextAcc + next8ve + "16")
            nextAcc = ""
            next8ve = "'"

    return " ".join(r)


def convert_ties_to_slurs(jianpu):
    """
    Convert tied notes in Jianpu notation to slurs.

    Args:
        jianpu (str): A string containing Jianpu notation with ties.

    Returns:
        str: The Jianpu notation with ties converted to slurs. Time signatures
             following ties are handled properly, preserving their placement.
    """
    # Remove comments from the input
    jianpu = re.sub(r"%.*$", "", jianpu, flags=re.MULTILINE).replace("|", "")

    # Define the pattern to match the entire tied note sequence
    tied_note_sequence_pattern = r"(?<!\\)\([^()]*~[^()]*\)(?<!\\)"

    # protect ties within slurs
    def protect_ties_in_slurs(match):
        return match.group(0).replace("~", "__TIE__")

    jianpu = re.sub(tied_note_sequence_pattern, protect_ties_in_slurs, jianpu)

    # Pattern parts:
    note_pattern = r"([qshb]?(?:[1-7][',]*)+\.?)"  # Matches a note with optional modifier [qshb], digit 1-7, optional ' or ,, and optional dot.
    annotation_pattern = (
        r'(\s*[\^_]"[^"]*")*'  # Matches optional annotations with leading spaces.
    )
    dash_pattern = r"(\s+-)"  # Matches a space followed by a dash.
    tie_pattern = r"(\s+~\s+)"  # Matches a tie symbol with spaces before and after.
    dash_and_annotation_pattern = (
        r"(" + dash_pattern + annotation_pattern + ")*"
    )  # Combines dashes and annotations.
    time_signature_pattern = r"(\s*\d+/\d+\s*)?"

    # Full combined pattern for sequences of tied notes
    combined_tie_pattern = (
        note_pattern
        + annotation_pattern
        + dash_and_annotation_pattern
        + "(?:"  # Use the combined dash and annotation pattern here
        + tie_pattern
        + time_signature_pattern
        + note_pattern  # Include the time signature pattern here, optionally preceded by a newline
        + annotation_pattern
        + dash_and_annotation_pattern
        + ")+"  # And also here
    )

    # This function will be used as the replacement function in the sub call
    def slur_replacement(match):
        # Get the full matched string, preserving newlines
        matched_string = match.group(0)

        # Replace newlines followed by a time signature to a special token to avoid splitting
        matched_string = re.sub(r"(\n\s*\d+/\d+\s*)", r"__TIMESIG__\1", matched_string)

        # Split the string into its parts using the tie symbol as the delimiter
        parts = re.split(r"~\s*", matched_string)

        # Replace the special token back to the original time signature
        parts = [re.sub(r"__TIMESIG__", "", part) for part in parts]

        # Remove trailing whitespace from each part, except for newlines
        parts = [part.rstrip() for part in parts]

        # Construct the slur by wrapping all but the first part in parentheses
        slur_content = parts[0] + " ( " + " ".join(parts[1:]) + " )"

        # Ensure we don't have multiple spaces in a row, but preserve newlines
        slur_content = re.sub(r"[ \t\f\v]{2,}", " ", slur_content)

        # Move parenthesis before dashes
        slur_content = re.sub(
            r'((?:(?:\s+-)(?:\s+[\^_]"[^"]*")*' + r")+)(\s+[\(\)])",
            r"\2\1",
            slur_content,
        )

        return slur_content

    # Replace all instances of ties with slurs using the replacement function
    converted_jianpu = re.sub(combined_tie_pattern, slur_replacement, jianpu)

    return converted_jianpu.strip().replace("__TIE__", "~")


def process_lyrics_line(line, do_hanzi_spacing):
    """
    Process a line of lyrics, including handling verse numbers and Chinese character spacing.

    Args:
    line (str): The line of lyrics to be processed.
    do_hanzi_spacing (bool): Whether to handle Chinese character spacing.

    Returns:
    str: The processed lyrics line.
    """
    toAdd = ""
    if (
        line
        and "1" <= line[0] <= "9"
        and (line[1] == "." or asUnicode(line)[1] == "\uff0e")
    ):
        # a verse number
        toAdd = r'\set stanza = #"%s." ' % line[:1]
        if line[1] == ".":
            line = line[2:]
        elif not isinstance(line, six.text_type):
            line = line[4:]  # for utf-8 full-width dot in Python 2
        else:
            line = line[2:]  # for full-width dot in Python 3
        line = line.strip()

    if do_hanzi_spacing:
        # Handle Chinese characters (hanzi) and related spacing:
        # for overhanging commas etc to work
        l2 = [r"\override LyricText #'self-alignment-X = #LEFT "]
        if toAdd:
            l2.append(toAdd)
            toAdd = ""
        needSpace = 0
        for c in list(asUnicode(line)):
            # TODO: also cover those outside the BMP?  but beware narrow Python builds
            is_hanzi = 0x3400 <= ord(c) < 0xA700
            is_openquote = c in "\u2018\u201c\u300A"
            if needSpace and (is_hanzi or is_openquote):
                l2.append(" ")
                needSpace = 0
                if is_openquote:  # hang left
                    # or RIGHT if there's no punctuation after
                    l2.append(
                        r"\once \override LyricText #'self-alignment-X = #CENTER "
                    )
            if is_hanzi:
                needSpace = 1
            if c == "-":
                needSpace = 0  # TODO: document this: separate hanzi with - to put more than one on same note
            else:
                l2.append(c)
        line = "".join(l2)
        if not isinstance("", six.text_type):
            line = line.encode("utf-8")  # Python 2

    # Replace certain characters and encode as needed, and
    # prepare the lyrics line with or without verse numbers.
    processed_lyrics = toAdd + re.sub("(?<=[^- ])- ", " -- ", line).replace(
        " -- ", " --\n"
    )
    return processed_lyrics


def process_headers_line(line, headers):
    """
    Process a single line of headers in a Jianpu file.

    Args:
        line (str): A single line of headers in the format "header_name=header_value".
        headers (dict): A dictionary containing the current headers in the Jianpu file.

    Raises:
        ValueError: If the header value does not match the expected value.

    Returns:
        None
    """
    hName, hValue = line.split("=", 1)
    hName, hValue = hName.strip().lower(), hValue.strip()
    if not headers.get(hName, hValue) == hValue:
        if hName == "instrument":
            missing = "NextPart or NextScore"
        else:
            missing = "NextScore"
        errExit(
            f"Changing header '{hName}' from '{headers[hName]}' to '{hValue}' (is there a missing {missing}?)"
        )
    headers[hName] = hValue


def process_key_signature(word, out, midi, western, inTranspose, notehead_markup):
    """
    Process a key signature in LilyPond syntax and add it to the output.

    Args:
        word (str): The key signature in LilyPond syntax.
        out (list): The list to which LilyPond code should be appended.
        midi (bool): Whether the output is for MIDI.
        western (bool): Whether the output is for Western notation.
        inTranspose (int): The current transpose state.
        notehead_markup (NoteheadMarkup): The notehead markup object.

    Returns:
        int: The updated transpose state.
    """

    # Convert '#' and 'b' to Unicode for approximation display
    unicode_repr = (
        re.sub("(?<!=)b$", "\u266d", word.replace("#", "\u266f")).upper() + " "
    )
    notehead_markup.unicode_approx.append(unicode_repr)

    if midi or western:
        # Close any open transposition block
        if inTranspose:
            out.append("}")

        transposeTo = word.split("=")[1].replace("#", "is").replace("b", "es").lower()

        # Ensure correct octave for MIDI pitch
        if midi and transposeTo[0] in "gab":
            transposeTo += ","

        # Transpose command for key
        out.append(r"\transpose c " + transposeTo + r" { \key c \major ")

        inTranspose = 1
    else:
        # Non-transposing key change marker for display
        out.append(
            r"\mark \markup{%s}" % word.replace("b", r"\flat").replace("#", r"\sharp")
        )

    # Return the updated transpose state
    return inTranspose


def process_fingering(word, out):
    """
    Extracts the fingering from the word and maps it to a Unicode character.
    The Unicode character is then appended to the LilyPond finger notation command.

    Args:
    word (str): A string containing the fingering to be extracted.
    out (list): A list to which the LilyPond finger notation command is appended.

    Returns:
    None
    """
    # Extract the fingering from the word
    finger = word.split("=")[1]
    # Mapping from textual representation to Unicode character
    finger_to_unicode = {
        "1": "\u4e00",  # Chinese numeral 1
        "2": "\u4c8c",  # Chinese numeral 2
        "3": "\u4e09",  # Chinese numeral 3
        "4": "\u56db",  # Chinese numeral 4
        "souyin": "\u4e45",  # Symbol for Souyin
        "harmonic": "\u25cb",  # White circle symbol for harmonic
        "up": "\u2197",  # NE arrow
        "down": "\u2198",  # SE arrow
        "bend": "\u293b",  # Bottom arc anticlockwise arrow
        "tilde": "\u223c",  # Full-width tilde
    }
    # Get the Unicode character for the fingering, defaulting to the original string
    finger_unicode = finger_to_unicode.get(finger, finger)

    # Append the LilyPond finger notation command
    out.append(r'\finger "%s"' % finger_unicode)


def process_time_signature(word, out, notehead_markup, midi):
    """
    Process a time signature and add it to the output.

    Args:
    - word (str): The time signature in the form of "num/denom".
    - out (list): The list to which the output should be appended.
    - notehead_markup (NoteheadMarkup): The NoteheadMarkup object to be updated.
    - midi (bool): Whether or not MIDI output is being generated.

    Returns:
    - None
    """

    # Check if there is an anacrusis (pickup measure) indicated by a comma
    if "," in word:  # anacrusis
        word, anac = word.split(",", 1)
    else:
        anac = ""

    # Add a markup for the time signature if it should be separate and if we're not generating MIDI
    if notehead_markup.separateTimesig and not midi:
        out.append(r"\mark \markup{" + word + "}")

    # Add the time signature to the output
    out.append(r"\time " + word)

    # Set the time signature in the notehead_markup for later reference
    num, denom = word.split("/")
    notehead_markup.setTime(int(num), int(denom))

    # If there is an anacrusis, handle it accordingly
    if anac:
        # Check for dotted anacrusis (e.g., "2.")
        if anac.endswith("."):
            a2 = anac[:-1]
            anacDotted = 1
        else:
            a2, anacDotted = anac, 0

        # Set the anacrusis in the notehead_markup
        notehead_markup.setAnac(int(a2), anacDotted)

        # Add the partial (anacrusis) to the output
        out.append(r"\partial " + anac)


def process_note(
    word,
    out,
    notehead_markup,
    lastPtr,
    afternext,
    not_angka,
    need_final_barline,
    maxBeams,
    line,
):
    """
    Process a note and return the updated values of lastPtr, afternext, need_final_barline, and maxBeams.

    This function takes a note (word) and various parameters regarding the notation and modifies the output list accordingly.
    It processes the note by applying octave changes, parsing the note, and applying any necessary markups. It also updates
    the pointer to the last note, the markup for the next note, and the maximum number of beams needed for the music piece.

    Args:
    - word (str): the note to be processed
    - out (list): the list of notes (output of processed notes)
    - notehead_markup (function): a function that returns the notehead markup
    - lastPtr (int): the index of the last note in the list
    - afternext (str): the markup for the next note
    - not_angka (bool): whether the note is a number or not (pertains to a specific notation system)
    - need_final_barline (bool): whether a final barline is needed at the end of the music piece
    - maxBeams (int): the maximum number of beams encountered so far in the piece
    - line (int): the line number in the source LilyPond data

    Returns:
    - lastPtr (int): the updated index of the last note in the list
    - afternext (str): the updated markup for the next note
    - need_final_barline (bool): the updated value indicating if a final barline is needed
    - maxBeams (int): the updated maximum number of beams
    """

    word0 = word  # Keep a copy of the original word for later use

    # Extract octave changes from the note, if present (indicated by "<" or ">")
    baseOctaveChange = "".join(c for c in word if c in "<>")
    if baseOctaveChange:
        notehead_markup.baseOctaveChange(baseOctaveChange)
        word = "".join(
            c for c in word if not c in "<>"
        )  # Remove octave changes from the note
        if not word:
            # If the word was only octave changes, no further processing is needed
            return lastPtr, afternext, need_final_barline, maxBeams

    # Parse the note to separate its components (figures, beams, etc.)
    figures, nBeams, dots, octave, accidental, tremolo = parseNote(word, word0, line)
    need_final_barline = (
        True  # After processing a note, a final barline is assumed to be needed
    )

    # Call the notehead markup function to get necessary markups before and after the note
    b4last, aftrlast, this, need_space_for_accidental, nBeams, octave = notehead_markup(
        figures, nBeams, dots, octave, accidental, tremolo, word0, line
    )

    # If there's any markup before the last note, prepend it to the last note in the output
    if b4last:
        out[lastPtr] = b4last + out[lastPtr]

    # If there's any markup after the last note, insert it after the last note in the output
    if aftrlast:
        out.insert(lastPtr + 1, aftrlast)

    # Update the pointer to the last note
    lastPtr = len(out)
    out.append(this)  # Add the current note to the output

    # If there's any markup for the next note, handle accidental spacing and append it
    if afternext:
        if need_space_for_accidental:
            afternext = afternext.replace(r"\markup", r"\markup \halign #2 ", 1)
        out.append(afternext)
        afternext = None  # Reset the markup for the next note

    # Update the maximum number of beams, accounting for octave if the notation is numerical
    if not_angka and "'" in octave:
        maxBeams = max(maxBeams, len(octave) * 0.8 + nBeams)
    else:
        maxBeams = max(maxBeams, nBeams)

    # Return the updated values
    return lastPtr, afternext, need_final_barline, maxBeams


def process_grace_notes(
    word, out, notehead_markup, midi, western, afternext, defined_jianpuGrace
):
    """
    Process grace notes in the given word and append the corresponding notation to `out`.

    Args:
        word (str): The word containing the grace note to be processed.
        out (list): The list to which the processed notation will be appended.
        notehead_markup: The notehead markup object.
        midi (bool): Whether to use MIDI notation.
        western (bool): Whether to use Western notation.
        afternext: The afternext object.
        defined_jianpuGrace (bool): Whether the jianpu-grace markup definition has already been appended to `out`.

    Returns:
        Tuple[bool, Any]: A tuple containing the updated value of `defined_jianpuGrace` and `afternext`.
    """
    gracenote_content = word[2:-1]  # Extract the content between 'g[' and ']'

    if midi or western:
        # Append Western notation grace note
        out.append(r"\acciaccatura { " + gracenotes_western(gracenote_content) + " }")
    else:
        # Handle the jianpu notation for grace note
        afternext = graceNotes_markup(gracenote_content, 0)
        if not notehead_markup.withStaff:
            out.append(r"\once \textLengthOn ")
        if not defined_jianpuGrace:
            defined_jianpuGrace = True
            # Append the necessary jianpu-grace markup definition to `out`
            out.append(
                r"""#(define-markup-command (jianpu-grace layout props text)
(markup?) "Draw right-pointing jianpu grace under text."
(let ((textWidth (cdr (ly:stencil-extent (interpret-markup layout props (markup (#:fontsize -4 text))) 0))))
(interpret-markup layout props
(markup
  #:line
  (#:right-align
   (#:override
    (cons (quote baseline-skip) 0.2)
    (#:column
     (#:line
      (#:fontsize -4 text)
      #:line
      (#:pad-to-box
       (cons -0.1 0)  ; X padding before grace
       (cons -1.6 0)  ; affects height of grace
       (#:path
        0.1
        (list (list (quote moveto) 0 0)
              (list (quote lineto) textWidth 0)
              (list (quote moveto) 0 -0.3)
              (list (quote lineto) textWidth -0.3)
              (list (quote moveto) (* textWidth 0.5) -0.3)
              (list (quote curveto) (* textWidth 0.5) -1 (* textWidth 0.5) -1 textWidth -1)))))))))))) """
            )
    return defined_jianpuGrace, afternext


def process_grace_notes_after(
    word, out, lastPtr, notehead_markup, midi, western, defined_JGR
):
    """
    Process the grace notes after the last note.

    Args:
    - word: str, the grace note content.
    - out: list, the list of output strings.
    - lastPtr: int, the index of the last note.
    - notehead_markup: object, the notehead markup object.
    - midi: bool, whether to use MIDI notation.
    - western: bool, whether to use Western notation.
    - defined_JGR: bool, whether the jianpu-grace-after markup command is defined.

    Returns:
    - defined_JGR: bool, whether the jianpu-grace-after markup command is defined.
    """
    gracenote_content = word[
        1:-2
    ]  # Remove the "[" and "]g" to isolate the grace note content
    if midi or western:
        # Handle grace notes for MIDI or Western notation:
        out[lastPtr] = (
            r" \afterGrace { "
            + out[lastPtr]
            + " } { "
            + gracenotes_western(gracenote_content)
            + " }"
        )
    else:
        # Handle grace notes for Jianpu notation:
        if not notehead_markup.withStaff:
            out[lastPtr] = r"\once \textLengthOn " + out[lastPtr]
        out.insert(lastPtr + 1, graceNotes_markup(gracenote_content, 1))
        if not defined_JGR:
            defined_JGR = True
            out[lastPtr] = (
                r"""#(define-markup-command (jianpu-grace-after layout props text)
(markup?) "Draw left-pointing jianpu grace under text."
(let ((textWidth (cdr (ly:stencil-extent (interpret-markup layout props (markup (#:fontsize -4 text))) 0))))
(interpret-markup layout props
(markup
  #:line
  (#:halign -4
   (#:override
    (cons (quote baseline-skip) 0.2)
    (#:column
     (#:line
      (#:fontsize -4 text)
      #:line
      (#:pad-to-box (cons 0 0)
       (cons -1.6 0)  ; affects height of grace
      (#:path
       0.1
       (list (list (quote moveto) 0 0)
             (list (quote lineto) textWidth 0)
             (list (quote moveto) 0 -0.3)
             (list (quote lineto) textWidth -0.3)
             (list (quote moveto) (* textWidth 0.5) -0.3)
             (list (quote curveto) (* textWidth 0.5) -1 (* textWidth 0.5) -1 0 -1)))))))))))) """
                + out[lastPtr]
            )
    return defined_JGR


def collapse_tied_notes(out):
    """
    Collapse sequences of tied notes into longer ones in the given LilyPond code.

    Args:
        out: str
            A string containing LilyPond musical notation code.

    Returns:
        str: The inputted LilyPond code with sequences of tied notes collapsed
        into longer notes, staff spacing corrected and bar checks adjusted.

    This function transforms sequences of tied notes into their equivalent
    longer note representations. It also corrects the staff spacing to maintain
    a consistent look throughout the score and adjusts bar checks for accurate
    measure counting.
    """
    # Patterns for converting sequences of tied notes into longer notes
    note_patterns = [
        (4, r"\.", "1."),  # in 12/8, 4 dotted crotchets = dotted semibreve
        (4, "", "1"),  # 4 crotchets = semibreve
        (3, "", "2."),  # 3 crotchets = dotted minim
        (2, r"\.", "2."),  # in 6/8, 2 dotted crotchets = dotted minim
        (2, "", "2"),  # 2 crotchets = minim
    ]

    # Use regular expressions to match tied note patterns and
    # replace them with the corresponding long note.
    for numNotes, dot, result in note_patterns:
        # Define regex pattern for tied notes.
        tied_note_pattern = (
            r"(?P<note>[^<][^ ]*|<[^>]*>)4"
            + dot
            + r"((?::32)?) +~(( \\[^ ]+)*) "
            + " +~ ".join([r"(?P=note)4" + dot] * (numNotes - 1))
        )
        out = re.sub(tied_note_pattern, r"\g<note>" + result + r"\g<2>\g<3>", out)

        tremolo_pattern = (
            r"\\repeat tremolo "
            + str(4 if not dot else 6)
            + r" { (?P<note1>[^ ]+)32 (?P<note2>[^ ]+)32 } +~(( \\[^ ]+)*) "
            + " +~ ".join([r"< (?P=note1) (?P=note2) >4" + dot] * (numNotes - 1))
        )
        out = re.sub(
            tremolo_pattern,
            r"\\repeat tremolo "
            + str(4 * numNotes if not dot else 6 * numNotes)
            + r" { \g<note1>32 \g<note2>32 }\g<3>",
            out,
        )

        out = out.replace(" ".join([r"r4" + dot] * numNotes), "r" + result)

    # Dynamics should be attached inside the tremolo, except for '\bar'.
    out = re.sub(
        r"(\\repeat tremolo [^{]+{ [^ ]+)( [^}]+ })(( +\\[^b][^ ]*)+)",
        r"\g<1>\g<3>\g<2>",
        out,
    )

    # Replace placeholders with actual bar numbers.
    out = re.sub(r"(%\{ bar [0-9]*: %\} )r([^ ]* \\bar)", r"\g<1>R\g<2>", out)

    # Adjust staff spacing for consistent look across the entire score.
    out = out.replace(
        r"\new RhythmicStaff \with {",
        r"\new RhythmicStaff \with {"
        + r"\override VerticalAxisGroup.default-staff-staff-spacing = "
        + r"#'((basic-distance . 6) (minimum-distance . 6) (stretchability . 0)) ",
    )

    return out


def finalize_output(out_list, need_final_barline, midi, western, not_angka):
    """
    Refines the music notation output by making several adjustments.

    Args:
        out_list (list): A list of strings representing the music score.
        need_final_barline (bool): Indicates whether a final barline is needed.
        midi (bool): Flag for whether the output format is MIDI.
        western (bool): Flag for whether the output format is Western notation.
        not_angka (bool): Flag for whether the output format is numeric notation.

    Returns:
        str: The refined musical score as a string.

    This function fine-tunes the musical notation output by carrying out various tasks like adding
    a final barline if needed, consolidating consecutive \mark \markup{} commands, ensuring each line
    is suitably terminated and does not exceed 60 characters in length, combining tied notes into
    their corresponding single notes, replacing bold markup commands with simple ones, and correcting
    the improper partitioning of long note sequences.
    """

    # Add a final barline if it's needed and we're not creating a MIDI file.
    if need_final_barline and not midi:
        out_list.append(r'\bar "|."')

    # Combine consecutive \mark \markup{} commands into a single command.
    i = 0
    while i < len(out_list) - 1:
        while (
            i < len(out_list) - 1
            and out_list[i].startswith(r"\mark \markup{")
            and out_list[i].endswith("}")
            and out_list[i + 1].startswith(r"\mark \markup{")
            and out_list[i + 1].endswith("}")
        ):
            nbsp = " "  # No need for the encoded non-breaking space, Python 3 defaults to unicode
            out_list[i] = (
                out_list[i][:-1]
                + nbsp
                + " "
                + out_list[i + 1][len(r"\mark \markup{") :]
            )
            del out_list[i + 1]
        i += 1

    # Ensure that each line ends properly and does not surpass 60 characters.
    for i in range(len(out_list) - 1):
        if not out_list[i].endswith("\n"):
            if "\n" in out_list[i] or len(out_list[i]) > 60:
                out_list[i] += "\n"
            else:
                out_list[i] += " "

    # Join all sequences and strings in the output list into a single string.
    out_str = "".join(out_list)

    # If we're outputting to MIDI or using Western notation, collapse tied notes.
    if midi or western:
        out_str = collapse_tied_notes(out_str)

    # If we're using numeric notation, change all bold markup commands to simple markup.
    if not_angka:
        out_str = out_str.replace("make-bold-markup", "make-simple-markup")

    # Adjust the breaking up of long notes in the musical score.
    pattern = r"([a-g]+[',]*)4\s*~\s*\(\s*([a-g]+[',]*)2\."
    out_str = re.sub(
        pattern,
        lambda m: m.group(1) + "1 (" if m.group(1) == m.group(2) else m.group(0),
        out_str,
    )

    return out_str


def getLY(score, headers=None, midi=True):
    """
    Transforms a given score into LilyPond format.

    Args:
        score (str): The raw input string containing musical notation.
        headers (dict): A dictionary with LilyPond header information, defaults to None.
        midi (bool): A Boolean flag indicating whether MIDI output is desired, defaults to True.

    Returns:
        tuple: A 4-tuple containing the generated output in LilyPond format,
               the maximum number of beams found, a list of processed lyrics,
               and the dictionary of headers.
    """

    # Convert ties to slurs if MIDI output is not being generated
    if not midi:
        score = convert_ties_to_slurs(score)

    # Use an empty dictionary for headers if not provided to avoid mutable default argument
    if not headers:
        headers = {}

    lyrics = []  # Initialize list to store processed lyrics
    notehead_markup.initOneScore()  # Initialize notation specifics for one score
    out = []  # Output list to accumulate LilyPond code
    maxBeams = 0  # Variable to track the maximum number of beams
    need_final_barline = False  # Flag to determine if a final barline is needed
    repeatStack = []  # Stack to handle repeat barlines
    lastPtr = 0  # Position tracker for handling elements added to `out`
    escaping = inTranspose = 0  # Flags for escaping LilyPond blocks and transposing
    afternext = defined_jianpuGrace = defined_JGR = None  # Initialize state flags

    for line in score.split("\n"):
        line = fix_fullwidth(line).strip()
        # Upgrade path compatibility for tempo
        line = re.sub(r"^%%\s*tempo:\s*(\S+)\s*$", r"\1", line)
        if line.startswith("LP:"):
            # Escaped LilyPond block.
            escaping = 1
            if len(line) > 3:
                out.append(line[3:] + "\n")  # remainder of current line
        elif line.startswith(":LP"):
            # TODO: and process the rest of the line?  (assume on line of own for now)
            escaping = 0
        elif escaping:
            out.append(line + "\n")
        elif not line:
            pass
        elif line.startswith("L:") or line.startswith("H:"):
            # lyrics
            do_hanzi_spacing = line.startswith("H:")
            line = line[2:].strip()
            processed_lyrics = process_lyrics_line(line, do_hanzi_spacing)
            lyrics.append(processed_lyrics)
        elif re.match(r"\s*[A-Za-z]+\s*=", line):
            # Lilypond header
            process_headers_line(line, headers)
        else:
            line = re.sub(
                '(?<= )[_^]"[^" ]* [^"]*"(?= |$)',
                lambda m: m.group().replace(" ", chr(0)),
                " " + line,
            )[
                1:
            ]  # multi-word text above/below stave
            for word in line.split():
                word = word.replace(chr(0), " ")
                if word in ["souyin", "harmonic", "up", "down", "bend", "tilde"]:
                    word = "Fr=" + word  # (Fr= before these is optional)
                if word.startswith("%"):
                    break  # a comment
                elif re.match("[1-468]+[.]*=[1-9][0-9]*$", word):
                    out.append(r"\tempo " + word)  # TODO: reduce size a little?
                elif re.match("[16]=[A-Ga-g][#b]?$", word):  # key
                    inTranspose = process_key_signature(
                        word, out, midi, western, inTranspose, notehead_markup
                    )
                elif word.startswith("Fr="):
                    process_fingering(word, out)
                elif re.match("letter[A-Z]$", word):
                    # TODO: not compatible with key change at same point, at least not in lilypond 2.20 (2nd mark mentioned will be dropped)
                    out.append(r'\mark \markup { \box { "%s" } }' % word[-1])
                elif re.match(r"R\*[1-9][0-9\/]*$", word):
                    if not western:
                        # \compressFullBarRests on Lilypond 2.20, \compressEmptyMeasures on 2.22, both map to \set Score.skipBars
                        out.append(
                            r"\set Score.skipBars = ##t \override MultiMeasureRest #'expand-limit = #1 "
                        )
                    out.append(r"R" + notehead_markup.wholeBarRestLen() + word[1:])
                elif re.match(
                    "[1-9][0-9]*/[1-468]+(,[1-9][0-9]*[.]?)?$", word
                ):  # time signature
                    process_time_signature(word, out, notehead_markup, midi)
                elif word == "OnePage":
                    if notehead_markup.onePage:
                        sys.stderr.write(
                            "WARNING: Duplicate OnePage, did you miss out a NextScore?\n"
                        )
                    notehead_markup.onePage = 1
                elif word == "KeepOctave":
                    pass  # undocumented option removed in 1.7, no effect
                # TODO: document this.  If this is on, you have to use c in a note to go back to crotchets.
                elif word == "KeepLength":
                    notehead_markup.keepLength = 1
                elif word == "NoBarNums":
                    if notehead_markup.noBarNums:
                        sys.stderr.write(
                            "WARNING: Duplicate NoBarNums, did you miss out a NextScore?\n"
                        )
                    notehead_markup.noBarNums = 1
                elif word == "SeparateTimesig":
                    if notehead_markup.separateTimesig:
                        sys.stderr.write(
                            "WARNING: Duplicate SeparateTimesig, did you miss out a NextScore?\n"
                        )
                    notehead_markup.separateTimesig = 1
                    out.append(r"\override Staff.TimeSignature #'stencil = ##f")
                elif word in ["angka", "Indonesian"]:
                    global not_angka
                    if not_angka:
                        sys.stderr.write(
                            "WARNING: Duplicate angka, did you miss out a NextScore?\n"
                        )
                    not_angka = True
                elif word == "WithStaff":
                    pass
                elif word == "PartMidi":
                    pass  # handled in process_input
                elif word == "R{":
                    repeatStack.append((1, 0, 0))
                    out.append(r"\repeat volta 2 {")
                elif re.match("R[1-9][0-9]*{$", word):
                    times = int(word[1:-1])
                    repeatStack.append((1, notehead_markup.barPos, times - 1))
                    out.append(r"\repeat percent %d {" % times)
                elif word == "}":
                    numBraces, oldBarPos, extraRepeats = repeatStack.pop()
                    out.append("}" * numBraces)
                    # Re-synchronise so bar check still works if percent is less than a bar:
                    newBarPos = notehead_markup.barPos
                    while newBarPos < oldBarPos:
                        newBarPos += notehead_markup.barLength
                    # newBarPos-oldBarPos now gives the remainder (mod barLength) of the percent section's length
                    notehead_markup.barPos = (
                        notehead_markup.barPos + (newBarPos - oldBarPos) * extraRepeats
                    ) % notehead_markup.barLength
                    # TODO: update barNo also (but it's used only for error reports)
                elif word == "A{":
                    repeatStack.append((2, notehead_markup.barPos, 0))
                    out.append(r"\alternative { {")
                elif word == "|" and repeatStack and repeatStack[-1][0] == 2:
                    # separate repeat alternates (if the repeatStack conditions are not met i.e. we're not in an A block, then we fall through to the undocumented use of | as barline check below)
                    out.append("} {")
                    notehead_markup.barPos = repeatStack[-1][1]
                elif (
                    word.startswith("\\")
                    or word in ["(", ")", "~", "->", "|"]
                    or word.startswith('^"')
                    or word.startswith('_"')
                ):
                    # Lilypond command, \p, ^"text", barline check (undocumented, see above), etc
                    if out and "afterGrace" in out[lastPtr]:
                        # apply to inside afterGrace in midi/western
                        out[lastPtr] = out[lastPtr][:-1] + word + " }"
                    else:
                        out.append(word)
                elif re.match(r"[1-9][0-9]*\[$", word):
                    # tuplet start, e.g. 3[
                    fitIn = int(word[:-1])
                    i = 2
                    while i < fitIn:
                        i *= 2
                    if i == fitIn:
                        num = int(fitIn * 3 / 2)
                    else:
                        num = int(i / 2)
                    out.append("\\times %d/%d {" % (num, fitIn))
                    notehead_markup.tuplet = (num, fitIn)
                elif word == "]":  # tuplet end
                    out.append("}")
                    notehead_markup.tuplet = (1, 1)
                elif re.match(r"g\[[#b',1-9\s]+\]$", word):
                    defined_jianpuGrace, afternext = process_grace_notes(
                        word,
                        out,
                        notehead_markup,
                        midi,
                        western,
                        afternext,
                        defined_jianpuGrace,
                    )
                elif re.match(r"\[[#b',1-9]+\]g$", word):
                    defined_JGR = process_grace_notes_after(
                        word, out, lastPtr, notehead_markup, midi, western, defined_JGR
                    )
                elif word == "Fine":
                    need_final_barline = False
                    out.append(
                        r'''\once \override Score.RehearsalMark #'break-visibility = #begin-of-line-invisible \once \override Score.RehearsalMark #'self-alignment-X = #RIGHT \mark "Fine" \bar "|."'''
                    )
                elif word == "DC":
                    need_final_barline = False
                    out.append(
                        r'''\once \override Score.RehearsalMark #'break-visibility = #begin-of-line-invisible \once \override Score.RehearsalMark #'self-alignment-X = #RIGHT \mark "D.C. al Fine" \bar "||"'''
                    )
                else:  # note (or unrecognised)
                    lastPtr, afternext, need_final_barline, maxBeams = process_note(
                        word,
                        out,
                        notehead_markup,
                        lastPtr,
                        afternext,
                        not_angka,
                        need_final_barline,
                        maxBeams,
                        line,
                    )

    # Final checks and finalizations
    if notehead_markup.barPos == 0 and notehead_markup.barNo == 1:
        errExit("No jianpu in score %d" % scoreNo)
    if (
        notehead_markup.inBeamGroup
        and not midi
        and not western
        and not notehead_markup.inBeamGroup == "restHack"
    ):
        out[lastPtr] += "]"  # needed if ending on an incomplete beat
    if inTranspose:
        out.append("}")
    if repeatStack:
        errExit("Unterminated repeat in score %d" % scoreNo)
    if escaping:
        errExit("Unterminated LP: in score %d" % scoreNo)
    notehead_markup.endScore()  # perform checks

    # Finalize the output by performing additional cleanup
    out = finalize_output(out, need_final_barline, midi, western, not_angka)

    return out, maxBeams, lyrics, headers


def process_input(inDat, withStaff=False):
    """
    Process the input data and return the corresponding LilyPond code.

    Args:
    - inDat: str - The input data to be processed.
    - withStaff: bool - Whether to include staff notation in the output.

    Returns:
    - str - The LilyPond code corresponding to the input data.
    """
    global unicode_mode
    unicode_mode = not not re.search(r"\sUnicode\s", " " + inDat + " ")
    if unicode_mode:
        return get_unicode_approx(
            re.sub(r"\sUnicode\s", " ", " " + inDat + " ").strip()
        )
    ret = []
    global scoreNo, western, has_lyrics, midi, not_angka, maxBeams, uniqCount, notehead_markup
    uniqCount = 0
    notehead_markup = NoteheadMarkup(withStaff)
    scoreNo = 0  # incr'd to 1 below
    western = False
    for score in re.split(r"\sNextScore\s", " " + inDat + " "):
        if not score.strip():
            continue
        scoreNo += 1
        # The occasional false positive doesn't matter: has_lyrics==False is only an optimisation so we don't have to create use_rest_hack voices.  It is however important to always detect lyrics if they are present.
        has_lyrics = not not re.search("(^|\n)[LH]:", score)
        parts = [p for p in re.split(r"\sNextPart\s", " " + score + " ") if p.strip()]
        for midi in [False, True]:
            not_angka = False  # may be set by getLY
            if scoreNo == 1 and not midi:
                # now we've established non-empty
                ret.append(all_scores_start())
            # TODO: document this (results in 1st MIDI file containing all parts, then each MIDI file containing one part, if there's more than 1 part)
            separate_score_per_part = (
                midi
                and re.search(r"\sPartMidi\s", " " + score + " ")
                and len(parts) > 1
            )
            for separate_scores in (
                [False, True] if separate_score_per_part else [False]
            ):
                headers = {}  # will accumulate below
                for partNo, part in enumerate(parts):
                    if partNo == 0 or separate_scores:
                        ret.append(score_start())
                    out, maxBeams, lyrics, headers = getLY(part, headers, midi)

                    if notehead_markup.withStaff and notehead_markup.separateTimesig:
                        errExit(
                            "Use of both WithStaff and SeparateTimesig in the same piece is not yet implemented"
                        )
                    if len(parts) > 1 and "instrument" in headers:
                        inst = headers["instrument"]
                        del headers["instrument"]
                    else:
                        inst = None
                    if midi:
                        ret.append(
                            midi_staff_start() + " " + out + " " + midi_staff_end()
                        )
                    else:
                        staffStart, voiceName = jianpu_staff_start(
                            inst, notehead_markup.withStaff
                        )
                        ret.append(staffStart + " " + out + " " + jianpu_staff_end())
                        if notehead_markup.withStaff:
                            western = True
                            staffStart, voiceName = western_staff_start(inst)
                            ret.append(
                                staffStart
                                + " "
                                + getLY(part)[0]
                                + " "
                                + western_staff_end()
                            )
                            western = False
                        if lyrics:
                            ret.append(
                                "".join(
                                    lyrics_start(voiceName)
                                    + l
                                    + " "
                                    + lyrics_end()
                                    + " "
                                    for l in lyrics
                                )
                            )
                    if partNo == len(parts) - 1 or separate_scores:
                        ret.append(score_end(**headers))
    ret = "".join(r + "\n" for r in ret)
    ret = re.sub(r'([\^_])"([^"]+)"', r"\1\2", ret)

    if lilypond_minor_version() >= 24:
        # needed to avoid deprecation warnings on Lilypond 2.24
        ret = re.sub(r"(\\override [A-Z][^ ]*) #'", r"\1.", ret)
    return ret


def get_unicode_approx(inDat):
    if re.search(r"\sNextPart\s", " " + inDat + " "):
        errExit("multiple parts in Unicode mode not yet supported")
    if re.search(r"\sNextScore\s", " " + inDat + " "):
        errExit("multiple scores in Unicode mode not yet supported")
    # TODO: also pick up on other not-supported stuff e.g. grace notes (or check for unicode_mode when these are encountered)
    global notehead_markup, western, midi, uniqCount, scoreNo, has_lyrics, not_angka, maxBeams
    notehead_markup = NoteheadMarkup()
    western = midi = not_angka = False
    # doesn't matter for our purposes (see 'false positive' comment above)
    has_lyrics = True
    uniqCount = 0
    scoreNo = 1
    getLY(inDat, {})
    u = "".join(notehead_markup.unicode_approx)
    if u.endswith("\u2502"):
        u = u[:-1] + "\u2551"
    return u


try:
    from shlex import quote
except:

    def quote(f):
        return "'" + f.replace("'", "'\"'\"'") + "'"


def write_output(outDat, fn, infile):
    if sys.stdout.isatty():
        if unicode_mode:
            if sys.platform == "win32" and sys.version_info() < (3, 6):
                # Unicode on this console could be a problem
                print(
                    """
For Unicode approximation on this system, please do one of these things:
(1) redirect output to a file,
(2) upgrade to Python 3.6 or above, or
(3) switch from Microsoft Windows to GNU/Linux"""
                )
                return
        else:  # normal Lilypond
            if not fn:
                # They didn't redirect our output.
                # Try to be a little more 'user friendly'
                # and see if we can put it in a temporary
                # Lilypond file and run Lilypond for them.
                # New in jianpu-ly v1.61.
                if len(sys.argv) > 1:
                    fn = os.path.split(infile)[1]
                else:
                    fn = "jianpu"
                if os.extsep in fn:
                    fn = fn[: -fn.rindex(os.extsep)]
                fn += ".ly"
                import tempfile

                cwd = os.getcwd()
                os.chdir(tempfile.gettempdir())
                print("Outputting to " + os.getcwd() + "/" + fn)
            else:
                cwd = None

            o = open(fn, "w")
            fix_utf8(o, "w").write(outDat)
            o.close()
            pdf = fn[:-3] + ".pdf"

            try:
                os.remove(pdf)  # so won't show old one if lilypond fails
            except:
                pass
            cmd = lilypond_command()
            if cmd:
                if lilypond_minor_version() >= 20:
                    # if will be viewed on-screen rather than printed, and it's not a Retina display
                    cmd += " -dstrokeadjust"
                os.system(cmd + " " + quote(fn))
                if sys.platform == "darwin":
                    os.system("open " + quote(pdf.replace("..pdf", ".pdf")))
                elif sys.platform.startswith("win"):
                    import subprocess

                    subprocess.Popen([quote(pdf)], shell=True)
                elif hasattr(shutil, "which") and shutil.which("evince"):
                    os.system("evince " + quote(pdf))
            if cwd:
                os.chdir(cwd)
            return
    fix_utf8(sys.stdout, "w").write(outDat)


def reformat_key_time_signatures(s):
    """
    Reformat the key and time signatures within a given string representing musical notation.

    The function performs the following operations:

    1. Reformat key signatures found in the string:
       It searches for key signature markup patterns such as "\\markup{1=A\\flat}" and
       reformats them to "\markup{1=bA}", where 'A' represents any note and '\\flat'
       is optional, indicating a flat note.

    2. Extract the section of the string that contains Jianpu staff notation, which is
       bounded by the markers "%% === BEGIN JIANPU STAFF ===" and "% === END JIANPU STAFF ===".

    3. Within the extracted Jianpu staff notation section, it finds all unique time signatures
       that match the pattern "\time X/Y", where X and Y are numerical values.

    4. Sort the unique time signatures by their numerical values and format them as spaced strings
       using the pattern "\hspace #1 \fraction X Y".

    5. Dynamically compute horizontal spacing based on the number of time signatures found, and
       reformat the key signature line in the original string to include the sorted time
       signatures and dynamic spacing. If only one time signature is found, it includes the
       command to omit the time signature from the staff.

    Args:
    - s (str): The input string containing the musical notation to be reformatted.

    Returns:
    - str: The reformatted string with updated key and time signatures.
    """

    # This pattern captures the key signature part including '1=' and any following \flat
    key_signature_pattern = re.compile(r"\\markup\{\s*1=([A-G])(\\flat)?\}")

    # Replace occurrences with the correct formatting.
    def replace_key_signature(match):
        note = match.group(1)
        alteration = match.group(2)
        alteration_symbol = "b" if alteration == "\\flat" else ""
        return f"\\markup{{1={alteration_symbol}{note}}}"

    # Replace key signatures using the pattern
    s = key_signature_pattern.sub(replace_key_signature, s)

    # Extract section between "%% === BEGIN JIANPU STAFF ===" and "% === END JIANPU STAFF ==="
    jianpu_staff_section_match = re.search(
        r"%% === BEGIN JIANPU STAFF ===(.*?)% === END JIANPU STAFF ===", s, re.DOTALL
    )

    if jianpu_staff_section_match:
        jianpu_staff_section = jianpu_staff_section_match.group(1)

        # Find unique time signatures
        time_signatures = set(re.findall(r"\\time\s+(\d+)/(\d+)", jianpu_staff_section))

        # Sort time signatures from smallest to largest (by their numerical values)
        time_signatures_sorted = sorted(
            time_signatures, key=lambda ts: (int(ts[0]), int(ts[1]))
        )

        # Convert sorted time signatures back to strings in the desired format
        time_signatures_str = " ".join(
            [
                f"\\hspace #1 \\fraction {num} {denom}"
                for num, denom in time_signatures_sorted
            ]
        )

        # Compute the dynamic spacing based on the length of the time signatures
        hspace_value = 11 + (len(time_signatures) - 1) * 2

        omittimesig = r"\\omit Staff.TimeSignature" if len(time_signatures) == 1 else ""

        # Update key signature line in the original string
        s = re.sub(
            r"(\\mark \\markup\{)1=(b?[A-G](\\sharp)?)\}",
            rf"\1\\hspace #{hspace_value} 1=\2 "
            + time_signatures_str.replace("\\", "\\\\")
            + "}"
            + omittimesig,
            s,
            re.MULTILINE,
        )

    return s


def filter_out_jianpu(lilypond_text):
    """
    This function accepts a LilyPond formatted text string as input and removes
    any section between the lines that start with "%% === BEGIN JIANPU STAFF ==="
    and "% === END JIANPU STAFF ===" (both lines inclusive).

    Parameters:
    lilypond_text (str): String containing LilyPond notation

    Returns:
    str: The modified LilyPond text with all JIANPU sections removed
    """

    begin_jianpu = "\n%% === BEGIN JIANPU STAFF ===\n"
    end_jianpu = "\n% === END JIANPU STAFF ===\n"

    while True:
        start_index = lilypond_text.find(begin_jianpu)
        end_index = lilypond_text.find(end_jianpu) + len(end_jianpu)

        if start_index != -1 and end_index != -1:
            # Remove the JIANPU section
            lilypond_text = lilypond_text[:start_index] + lilypond_text[end_index:]
        else:
            # No more JIANPU sections exist, so break from the loop
            break

    return lilypond_text


# Function to download plain text file from Google Drive
def download_file_from_google_drive(id):
    """
    This function downloads a Google Docs document as plain text using its file ID.

    :param id: The ID of the file to download from Google Drive
    :returns: The text content of the downloaded file
    """

    # Construct the URL for downloading the document as plain text
    url = f"https://docs.google.com/document/export?format=txt&id={id}"

    # Send a GET request to the constructed URL
    response = requests.get(url)
    response.raise_for_status()

    # Decode the response content with UTF-8
    text = response.content.decode("utf-8")

    # Remove BOM if present
    if text.startswith("\ufeff"):
        text = text[len("\ufeff") :]

    # Replace CRLF with LF
    text = text.replace("\r\n", "\n")

    # Return the processed text
    return text


def parse_arguments():
    # Create ArgumentParser object
    parser = argparse.ArgumentParser()

    # Define command-line options
    parser.add_argument(
        "--html", action="store_true", default=False, help="output in HTML format"
    )
    parser.add_argument(
        "-m",
        "--markdown",
        action="store_true",
        default=False,
        help="output in Markdown format",
    )
    parser.add_argument(
        "-s",
        "--staff-only",
        action="store_true",
        default=False,
        help="only output Staff sections",
    )
    parser.add_argument(
        "-B",
        "--with-staff",
        action="store_true",
        default=False,
        help="output both Jianpu and Staff sections",
    )
    parser.add_argument(
        "-b",
        "--bar-number-every",
        type=int,
        default=1,
        help="option to set bar number, default is 1",
    )
    parser.add_argument(
        "-i",
        "--instrument",
        action="store",
        default="",
        help="instrument to be used with MIDI",
    )
    parser.add_argument(
        "-M",
        "--metronome",
        action="store_true",
        default=False,
        help="Whether to enable metronome in the mp3 file",
    )
    parser.add_argument(
        "-g",
        "--google-drive",
        action="store_true",
        default=False,
        help="Use if the input_file is a Google Drive ID",
    )

    # Add positional arguments
    parser.add_argument(
        "input_file", help="input file name or Google Drive file ID (if -g is enabled)"
    )
    parser.add_argument(
        "output_file", nargs="?", default="", help="output file name (optional)"
    )

    args = parser.parse_args()

    global bar_number_every, midiInstrument

    bar_number_every = args.bar_number_every

    if args.instrument:
        midiInstrument = args.instrument
    elif args.metronome:
        midiInstrument = "choir aahs"
    else:
        midiInstrument = "flute"

    # Parse options from command line
    return args


def get_title_from_text(input_text):
    """
    Extracts the title from a string of text that contains a line with 'title='.

    Args:
        input_text (str): The input text to search for the title.

    Returns:
        str or None: The extracted title as a string, or None if no title is found.
    """
    # Find the line containing 'title=' and extract <title>
    title_line = next(
        (line for line in input_text.split("\n") if "title=" in line), None
    )
    if title_line:
        title = title_line.split("=")[1].strip()  # Remove leading/trailing whitespaces
        title = title.replace(" ", "_")  # Replace spaces with underscores
        return title
    return None  # Return None if no title is found


def set_output_file(args, input_text):
    """
    Sets the output file name based on the input arguments and text.

    If the output file name is not specified in the input arguments, the function
    attempts to extract the title from the input text and use it as the output file
    name. If a title cannot be extracted, the default output file name 'song.ly' is
    used.

    Args:
        args: The input arguments.
        input_text: The input text.

    Returns:
        The updated input arguments with the output file name set.
    """
    if not args.output_file:
        title = get_title_from_text(input_text)
        if title:
            args.title = title
            args.output_file = f"{title}.ly"  # Set output file name
        else:
            args.title = "song"
            args.output_file = "song.ly"  # Default output file name
    return args


def convert_midi_to_mp3(base_name, with_metronome):
    """
    Converts a MIDI file to an MP3 file using either 'mscore', 'musescore', or 'timidity' with 'lame'.
    If 'with_metronome' is True, uses either 'mscore' or 'musescore' to include a metronome in the output.
    Otherwise, uses 'timidity' with 'lame' to convert the MIDI file to MP3.

    Args:
        base_name (str): The base name of the MIDI file (without the '.midi' extension).
        with_metronome (bool): Whether to include a metronome in the output.

    Returns:
        None
    """

    # Check if 'mscore' or 'musescore' exists
    command = None

    if with_metronome and shutil.which("mscore"):
        # use mscore
        command = f"mscore -o {base_name}.mp3 {base_name}.midi"
    elif with_metronome and shutil.which("musescore"):
        # use musescore
        command = f"musescore -o {base_name}.mp3 {base_name}.midi"
    else:
        # fallback to timidity
        command = f"timidity {base_name}.midi -Ow -o - | lame - -b 192 {base_name}.mp3"

    # execute the command
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()

    if error:
        print(f"Error: {error}")
    else:
        print(f"Output: {output}")


def main():
    """
    Main function that processes input data and writes output to a file.
    """
    args = parse_arguments()

    if args.html or args.markdown:
        return write_docs()

    # Check whether to read file from google drive or local directory
    if args.google_drive:
        input_text = download_file_from_google_drive(args.input_file)
        inDat = get_input(input_text, True)
        args = set_output_file(args, input_text)
    else:
        inDat = get_input(args.input_file)

    out = process_input(inDat, args.staff_only or args.with_staff)
    if not args.staff_only and not args.with_staff:
        out = reformat_key_time_signatures(out)

    if args.staff_only:
        out = filter_out_jianpu(out)

    write_output(out, args.output_file, args.input_file)
    if args.google_drive:
        convert_midi_to_mp3(args.title, args.metronome)


if __name__ == "__main__":
    main()
