"""CFF to CFF2 converter."""

from fontTools.ttLib import TTFont, newTable
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.misc.psCharStrings import T2WidthExtractor
from fontTools.cffLib import (
    TopDictIndex,
    FDArrayIndex,
    FontDict,
    buildOrder,
    topDictOperators,
    privateDictOperators,
    topDictOperators2,
    privateDictOperators2,
)
from io import BytesIO
import logging

__all__ = ["convertCFFToCFF2", "main"]


log = logging.getLogger("fontTools.cffLib")


class _NominalWidthUsedError(Exception):
    def __add__(self, other):
        raise self

    def __radd__(self, other):
        raise self


def _convertCFFToCFF2(cff, otFont):
    """Converts this object from CFF format to CFF2 format. This conversion
    is done 'in-place'. The conversion cannot be reversed.

    This assumes a decompiled CFF table. (i.e. that the object has been
    filled via :meth:`decompile` and e.g. not loaded from XML.)"""

    # Clean up T2CharStrings

    topDict = cff.topDictIndex[0]
    fdArray = topDict.FDArray if hasattr(topDict, "FDArray") else None
    charStrings = topDict.CharStrings
    globalSubrs = cff.GlobalSubrs
    localSubrs = [getattr(fd.Private, "Subrs", []) for fd in fdArray] if fdArray else []

    for glyphName in charStrings.keys():
        cs, fdIndex = charStrings.getItemAndSelector(glyphName)
        cs.decompile()

    # Clean up subroutines first
    for subrs in [globalSubrs] + localSubrs:
        for subr in subrs:
            program = subr.program
            i = j = len(program)
            try:
                i = program.index("return")
            except ValueError:
                pass
            try:
                j = program.index("endchar")
            except ValueError:
                pass
            program[min(i, j) :] = []

    # Clean up glyph charstrings
    nominalWidthXError = _NominalWidthUsedError()
    for glyphName in charStrings.keys():
        cs, fdIndex = charStrings.getItemAndSelector(glyphName)
        program = cs.program
        if fdIndex == None:
            fdIndex = 0

        # Intentionally use custom type for nominalWidthX, such that any
        # CharString that has an explicit width encoded will throw back to us.
        extractor = T2WidthExtractor(
            localSubrs[fdIndex] if localSubrs else [],
            globalSubrs,
            nominalWidthXError,
            0,
        )
        try:
            extractor.execute(cs)
        except _NominalWidthUsedError:
            # Program has explicit width. We want to drop it, but can't
            # just pop the first number since it may be a subroutine call.
            # Instead, when seeing that, we embed the subroutine and recurse.
            # This has the problem that some subroutines might become unused.
            # We don't currently prune those. Subset module has code for this
            # kind of stuff, possibly plug it in here if pruning becomes needed.
            while program[1] in ["callsubr", "callgsubr"]:
                subrNumber = program.pop(0)
                op = program.pop(0)
                bias = extractor.localBias if op == "callsubr" else extractor.globalBias
                subrNumber += bias
                subrSet = localSubrs[fdIndex] if op == "callsubr" else globalSubrs
                subrProgram = subrSet[subrNumber].program
                program[:0] = subrProgram
            # Now pop the actual width
            program.pop(0)

        if program and program[-1] == "endchar":
            program.pop()

    # Upconvert TopDict

    cff.major = 2
    cff2GetGlyphOrder = cff.otFont.getGlyphOrder
    topDictData = TopDictIndex(None, cff2GetGlyphOrder)
    for item in cff.topDictIndex:
        # Iterate over, such that all are decompiled
        topDictData.append(item)
    cff.topDictIndex = topDictData
    topDict = topDictData[0]
    if hasattr(topDict, "Private"):
        privateDict = topDict.Private
    else:
        privateDict = None
    opOrder = buildOrder(topDictOperators2)
    topDict.order = opOrder
    topDict.cff2GetGlyphOrder = cff2GetGlyphOrder

    if not hasattr(topDict, "FDArray"):
        fdArray = topDict.FDArray = FDArrayIndex()
        fdArray.strings = None
        fdArray.GlobalSubrs = topDict.GlobalSubrs
        topDict.GlobalSubrs.fdArray = fdArray
        charStrings = topDict.CharStrings
        if charStrings.charStringsAreIndexed:
            charStrings.charStringsIndex.fdArray = fdArray
        else:
            charStrings.fdArray = fdArray
        fontDict = FontDict()
        fontDict.setCFF2(True)
        fdArray.append(fontDict)
        fontDict.Private = privateDict
        privateOpOrder = buildOrder(privateDictOperators2)
        if privateDict is not None:
            for entry in privateDictOperators:
                key = entry[1]
                if key not in privateOpOrder:
                    if key in privateDict.rawDict:
                        # print "Removing private dict", key
                        del privateDict.rawDict[key]
                    if hasattr(privateDict, key):
                        delattr(privateDict, key)
                        # print "Removing privateDict attr", key
    else:
        # clean up the PrivateDicts in the fdArray
        fdArray = topDict.FDArray
        privateOpOrder = buildOrder(privateDictOperators2)
        for fontDict in fdArray:
            fontDict.setCFF2(True)
            for key in list(fontDict.rawDict.keys()):
                if key not in fontDict.order:
                    del fontDict.rawDict[key]
                    if hasattr(fontDict, key):
                        delattr(fontDict, key)

            privateDict = fontDict.Private
            for entry in privateDictOperators:
                key = entry[1]
                if key not in privateOpOrder:
                    if key in list(privateDict.rawDict.keys()):
                        # print "Removing private dict", key
                        del privateDict.rawDict[key]
                    if hasattr(privateDict, key):
                        delattr(privateDict, key)
                        # print "Removing privateDict attr", key

    # Now delete up the deprecated topDict operators from CFF 1.0
    for entry in topDictOperators:
        key = entry[1]
        if key not in opOrder:
            if key in topDict.rawDict:
                del topDict.rawDict[key]
            if hasattr(topDict, key):
                delattr(topDict, key)

    # TODO(behdad): What does the following comment even mean? Both CFF and CFF2
    # use the same T2Charstring class. I *think* what it means is that the CharStrings
    # were loaded for CFF1, and we need to reload them for CFF2 to set varstore, etc
    # on them. At least that's what I understand. It's probably safe to remove this
    # and just set vstore where needed.

    # At this point, the Subrs and Charstrings are all still T2Charstring class
    # easiest to fix this by compiling, then decompiling again
    file = BytesIO()
    cff.compile(file, otFont, isCFF2=True)
    file.seek(0)
    cff.decompile(file, otFont, isCFF2=True)


def convertCFFToCFF2(font):
    cff = font["CFF "].cff
    del font["CFF "]
    _convertCFFToCFF2(cff, font)
    table = font["CFF2"] = newTable("CFF2")
    table.cff = cff


def main(args=None):
    """Convert CFF OTF font to CFF2 OTF font"""
    if args is None:
        import sys

        args = sys.argv[1:]

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools cffLib.CFFToCFF2",
        description="Upgrade a CFF font to CFF2.",
    )
    parser.add_argument(
        "input", metavar="INPUT.ttf", help="Input OTF file with CFF table."
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT.ttf",
        default=None,
        help="Output instance OTF file (default: INPUT-CFF2.ttf).",
    )
    parser.add_argument(
        "--no-recalc-timestamp",
        dest="recalc_timestamp",
        action="store_false",
        help="Don't set the output font's timestamp to the current time.",
    )
    loggingGroup = parser.add_mutually_exclusive_group(required=False)
    loggingGroup.add_argument(
        "-v", "--verbose", action="store_true", help="Run more verbosely."
    )
    loggingGroup.add_argument(
        "-q", "--quiet", action="store_true", help="Turn verbosity off."
    )
    options = parser.parse_args(args)

    from fontTools import configLogger

    configLogger(
        level=("DEBUG" if options.verbose else "ERROR" if options.quiet else "INFO")
    )

    import os

    infile = options.input
    if not os.path.isfile(infile):
        parser.error("No such file '{}'".format(infile))

    outfile = (
        makeOutputFileName(infile, overWrite=True, suffix="-CFF2")
        if not options.output
        else options.output
    )

    font = TTFont(infile, recalcTimestamp=options.recalc_timestamp, recalcBBoxes=False)

    convertCFFToCFF2(font)

    log.info(
        "Saving %s",
        outfile,
    )
    font.save(outfile)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))