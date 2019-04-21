# TigerTamer

This program is specifically designed to convert cut-lists from the Mozaik
cabinet design software (CSV files ending in `.dat`) into
TigerTouch-compatible cut-lists (XML files ending in `.tiger`). TigerTouch
is a frontend/controller for the TigerStop hardware  (a programmable saw-stop).

## Why?

**TLDR:** **TigerTamer** makes the output more readable/correct on-demand, and
signals any errors along the way.

TigerTouch/TigerLink includes a user-configurable CSV parser, that will
watch a folder for new files, parse them according to the user's configuration,
and output `.tiger` files to use with the TigerTouch controller software.
However, it does not include any features to 'massage' the data before creating
the XML, and requires TigerLink to be running before any new files are added
to the input directory. TigerLink and TigerTouch cannot run at the same time,
so this requires a few extra steps to get your `.csv` files converted into
`.tiger` files. It also does not signal the user in any way to let them know
that the files were parsed, or that something went wrong.

That alone is annoying, but Mozaik's output format makes matters even worse.
Mozaik outputs long lines when several cabinets use the same part. The lines
are too long to display in TigerTouch, so **TigerTamer** will split the large
part-lines into several smaller parts. Mozaik will also 'drop' parts sometimes.
Mozaik may output a CSV line like this:
```
12,1.5,86.50001,RS,R5:1&2&3&4&5&6&10&11 R7:1&2&3&7&8,
```

If you count the rooms and cabinet numbers, there are 13 parts here. Mozaik
will sometimes output a quantity of 12.
The other part was lost somewhere along the way.

**TigerTamer** will count actual room numbers and cabinet numbers, including any
quantity specifiers like `R7:1(2)`, and output the correct quantity while
splitting these long lines. It will also log the inconsistent count so the bug
could possibly be reported (good luck with that).

## Usage

**TigerTamer** will run in the console (`./tigertamer.py`) or with a GUI (`./tigertamer.py -g`).

It will always log errors to `tigertamer.log`, but can also log everything it
does so you can see how parts are converted/split (using `--debug`).

Use `--preview` to parse files without writing the tiger file to disk, or
load the GUI and click `Admin -> Tiger Viewer -> File -> Preview Mozaik File`.

```
Usage:
    tigertamer.py (-F | -h | -L | -v) [-D]
    tigertamer.py -f func [-e] [-s] [-D]
    tigertamer.py -g [-e] [-r] [-s] [-D]
    tigertamer.py (-u | -U) [-a dir | ARCHIVE_FILE...] [-D]
    tigertamer.py [-g] (-p | -V) FILE... [-D]
    tigertamer.py (-m | -M | -t | -T) FILE... [-D]
    tigertamer.py [FILE...] [-e] [-i dir...] [-I text...]
                  [-n] [-s] [-D]
    tigertamer.py [FILE...] [-e] [-i dir...] [-I text...]
                  [-o dir [-a dir]] [-s] [-D]

Options:
    ARCHIVE_FILE          : One or more archived file paths to unarchive.
    FILE                  : One or more CSV (.dat) files to parse,
                            or Tiger (.tiger) files to view with -V.
    -a dir,--archive dir  : Directory for completed master files, or for
                            unarchiving all files at once.
                            Use - to disable archiving when converting
                            files.
                            Disabled when printing to stdout.
    -D,--debug            : Show more info while running.
    -e,--extra            : Use extra data from Mozaik files.
    -F,--functions        : List all available functions for -f and exit.
    -f name, --func name  : Run a function from WinMain for debugging.
                            This automatically implies -g,--gui.
    -g,--gui              : Load the Tiger Tamer GUI.
    -h,--help             : Show this help message.
    -I str,--IGNORE str   : One or more strings to ignore when looking
                            for mozaik files (applies to full file path).
    -i dir,--ignore dir   : One or more directories to ignore when looking
                            for mozaik files.
                            The output and archive directories are
                            included automatically.
    -L,--labelconfig      : Print label config and exit.
    -M,--MASTERFILE       : Like -m, but separate into width files first.
    -m,--masterfile       : Parse, split parts, combine parts, and then
                            output another Mozaik master file (.dat) to
                            stdout.
    -n,--namesonly        : Just show which files would be generated.
    -o dir,--output dir   : Output directory.
                            Use - for stdout output.
    -p,--preview          : Preview output for a Mozaik (.dat) file.
                            This will not create any Tiger (.tiger) files.
    -r,--run              : Automatically run with settings in config.
    -s,--nosplit          : Do not split parts into single line items.
    -T,--TREE             : Like -t, but separate into width files first.
                            This adjusts the tree to width-first.
    -t,--tree             : Print parts in tree-form.
    -u,--unarchive        : Undo any archiving, if possible.
    -U,--UNARCHIVE        : Undo any archiving, and remove all output
                            files.
    -V,--view             : View a formatted .tiger file in the console,
                            or with the GUI if -g is also used.
    -v,--version          : Show version.
```

## Dependencies

There are a few third-party PyPi packages needed to run this.
To install them, run `pip install -r requirements.txt`.

Package: | Description:
------: | -----
[colr](https://pypi.org/project/colr) | Used for terminal colors.
[docopt](https://pypi.org/project/docopt) | Used for command-line argument parsing.
[easysettings](https://pypi.org/project/easysettings) | Used for JSON-based configuration.
[lxml](https://pypi.org/project/lxml) | Used to create XML files.
[printdebug](https://pypi.org/project/printdebug) | Used for debug mode printing/logging.

## Installation

There is no installer right now. Clone this repo and create a desktop shortcut
to `python tigertamer.py -g`. Make sure you use Python 3.5+.
You can also include any other options you need.
There is an icon/image file included in `/resources`. Use the one that works
best for you.

## Configuration

Almost everything can be configured with the GUI (soon everything will be).
Config is stored as JSON in `tigertamer.json`.

Paths are written in linux/python style. Forward slashes are used.

```javascript
{
    // Where to store archived .dat files:
    "archive_dir": "C:/Archived",
    // Whether to exit TigerTamer after creating the tiger files in GUI mode.
    "auto_exit": true,
    // Whether to create tiger files on load (using config values) in GUI mode.
    "auto_run": false,
    // Input directories/files, where Mozaik (.dat) files will be found.
    "dat_dir": [
        "C:/Cutlists"
    ],
    // Whether to use the extra data column from Mozaik (.dat) files.
    // This is usually a note about the part, but could be empty.
    "extra_data": true,
    // Input directories to ignore. Mozaik files will not be loaded from these.
    // The `archive_dir`, and `tiger_dir` are automatically added at run-time.
    "ignore_dirs": [
        "C:/dir/is/ignored",
    ],
    // List of strings that causes a file path (including directory) to be ignored.
    "ignore_strs": [
        ".bak"
    ],
    // Disable long-line-splitting (the best feature in TigerTamer).
    // This will closely match the output of TigerLink.
    "no_part_split": false,
    // Tkinter theme to use.
    "theme": "clam",
    // Output directory, where Tiger (.tiger) files will be stored.
    "tiger_dir": "C:/my/dir/for/output",
    // Settings for TigerTouch, stored in the Tiger files.
    // These are the same settings you edit in CutLists.xml for TigerLink.
    // The meaning of these is also in the TigerTouch/TigerLink manual.
    "tiger_settings": {
        // How much to cut off the head-end of a board before optimizing.
        "headCut": "0",
        // Whether this is a cascade-style list.
        // If set to true, TigerStop will automatically look for and load the
        // the next cascade-style list when this list is completed.
        "isCascade": "false",
        // Sets all part quantities to infinity.
        "isInfinite": "false",
        // Whether to optimize the cut list.
        "isOptimized": "true",
        // TigerTamer-specific config for label printing:
        "labels": [
            [
                // Column name (must be a valid tiger file column name).
                "part",
                {
                    // Font size for this column.
                    "fontsize": "24",
                    // X position for this column.
                    "x": "50",
                    // Y position for this column.
                    "y": "0"
                }
            ],
            [
                "no",
                {
                    "fontsize": "24",
                    "x": "50",
                    "y": "60"
                }
            ],
            [
                "note",
                {
                    "fontsize": "12",
                    "x": "50",
                    "y": "90"
                }
            ],
            [
                "index",
                {
                    "fontsize": "12",
                    "x": "50",
                    "y": "105"
                }
            ]
        ],
        // This is for pattern/pull-style lists.
        // This tells the TigerStop which column contains the stock length.
        "patternStockLength": "0",
        // Used for pack-sawing. Tells TigerStop whether you are stacking material
        // and cutting more than one part at a time.
        "quantityMultiples": "false",
        // Whether to make the file name available for viewing.
        "sendFileName": "true",
        // List style to use (from TigerLink manual):
        // Push - Push material into the tool.
        // Pull - Pull material from the tool.
        // Setpoint - Process lists as a stop, using absolute values.
        // Pattern - Pattern style list.
        "style": "Setpoint",
        // How much to cut off the tail-end of the board while optimizing.
        "tailCut": "0",
    },
}
```

## Notes

This software was designed for a very specific use-case. I uploaded it to
GitHub to archive it, and easily install upgrades. If you find it useful, or
have any ideas about how to make it better, file an issue or a pull-request.
