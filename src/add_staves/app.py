"""
Analytical Stave Appender

Insert systems between musical staves.
"""


# Imports #

import re
import os
import typer
import operator

from pathlib import Path
from pypdf import PageObject, PaperSize, PdfReader, PdfWriter
from typing import Annotated, Optional, List
from functools import reduce


# Argument Validation #

def outputCallback(ctx: typer.Context, input: Optional[Path]) -> Path:
    """
    Callback for the output option in 'run' that creates a default
    output path if none was provided:

    path/to/score.pdf -> path/to/score-analysis.pdf

    Create the default path can fail in case a fil with this name
    already exists. Providing the '--force'-flag allows overwriting of
    this file.
    """
    if input is None:
        score = Path(ctx.params["score"])
        path = score.parent / (score.stem + "-analysis.pdf")
        if path.exists() and not ctx.params["force"]:
            print("[red]A file at the default path [bright_white]'%s'[/] already exists. Please provide an explicit output path with the [green bold]'-o'[/] option or force overwriting with the [green bold]'-f'[/] flag.[/]"
                  % path)
            raise typer.Exit(1)
        return path
    else:
        return input


def groupsParser(input: Optional[str]) -> Optional[List[int]]:
    """
    Parse a string of comma-separated or space-separated
    numbers into a list of integers.

    This will default to an empty list if an error occurs.
    """
    if input is None:
        return None
    try:
        numbers = [int(num) for num in input.split(",")]
    except:
        numbers = []
    try:
        numbers = [int(num) for num in re.split(r"\s+", input)]
    except:
        pass
    return numbers if all(num > 0 for num in numbers) else []


def stavesParser(input: Optional[str]) -> PageObject:
    """
    Fetches the correct empty staves pdf from the resources.

    Valid counts are 0...6.
    """
    stavesPath = os.path.join(os.path.dirname(__file__), "staves", "empty-%d.pdf" % int(input))
    return PdfReader(stavesPath).pages[0]


# Helpers #

def getHeight(page: List[List[PageObject]], innerSpacing: int, outerSpacing: int, topMargin: int, bottomMargin: int) -> int:
    "Get the total height of PAGE."
    return (
        len(page) * innerSpacing
        + (len(page) - 1) * outerSpacing
        + topMargin
        + bottomMargin
        + (reduce(operator.add, [object.cropbox.height for objects in page for object in objects], 0))
    )


def printPage(page: List[List[PageObject]], writer, innerSpacing: int, outerSpacing: int, topMargin: int, bottomMargin: int, leftMargin: int, pageHeight: int, pageWidth: int, ragged: bool, shift: int, dropFirst: bool, dropLast: bool):
    """
    Print PAGE to WRITER.

    Origin of the PDF is at the bottom
    """
    # Keep track of the current height, to fine tune the translations.
    height = max(getHeight(page, innerSpacing, outerSpacing, topMargin, bottomMargin), pageHeight)

    # Dynamically increase outerSpacing if ragged is True:
    raggedOuterSpacing = outerSpacing + (pageHeight - getHeight(page, innerSpacing, outerSpacing, topMargin, bottomMargin)) / len(page)

    # Set the canvas.
    canvas = writer.add_blank_page(width=pageWidth, height=height)

    height -= topMargin

    for outerIndex, system in enumerate(page):
        for innerIndex, object in enumerate(system):
            if dropFirst and object.cropbox.width == 538.582461 and outerIndex == 0:
                continue
            elif dropLast and object.cropbox.width == 538.582461 and (outerIndex + 1) == len(page):
                continue
            else:
                canvas.merge_translated_page(object,
                                             tx=leftMargin-object.cropbox.left+(shift if object.cropbox.width == 538.582461 else 0),
                                             ty=height-object.cropbox.top,
                                             over=False,
                                             expand=False)
                height -= object.cropbox.height
                if (innerIndex + 1) != len(system):
                    height -= innerSpacing
        if (outerIndex + 1) != len(page):
            height -= (outerSpacing if ragged else raggedOuterSpacing)


# Main #

app = typer.Typer(rich_markup_mode="rich")

@app.command()
def main(score: Annotated[Path, typer.Argument(metavar="SCORE",
                                              help="Path to the cropped score.",
                                              show_default=False,
                                              exists=True,
                                              readable=True),],
         force: Annotated[bool, typer.Option("--force", "-f",
                                             help="Overwrite the output destination.",
                                             is_flag=True,
                                             rich_help_panel="Behaviour")] = False,
         output: Annotated[Optional[Path], typer.Option("--output", "-o",
                                                        metavar="PATH",
                                                        help="Path to the output file. \\[default: <score>-analysis.pdf]",
                                                        rich_help_panel="Behaviour",
                                                        file_okay=True,
                                                        show_default=False,
                                                        callback=outputCallback)] = None,
         groups: Annotated[Optional[str], typer.Option("--combining", "-c",
                                                       metavar="TEXT",
                                                       show_default=False,
                                                       rich_help_panel="Page Layout",
                                                       help="Groups of systems combined on one page as space- or comma-seperated text.",
                                                       parser=groupsParser)] = None,
         staves: Annotated[int, typer.Option("--staves", "-s",
                                             min=0, max=6,
                                             clamp=True,
                                             help="Number of staves to add (0...6).",
                                             metavar="NUMBER",
                                             rich_help_panel="Page Layout",
                                             parser=stavesParser)] = 2,
         above: Annotated[bool, typer.Option("--above", "-a",
                                             help="Include the analysis staves above the system.",
                                             show_default=True,
                                             rich_help_panel="Page Layout")] = False,
         innerSpacing: Annotated[int, typer.Option(metavar="NUMBER",
                                                    help="Configure the spacing between the score system and the analysis staff.",
                                                    rich_help_panel="Page Dimensions")] = 20,
         outerSpacing: Annotated[int, typer.Option(metavar="NUMBER",
                                                    help="Configure the spacing between two systems.",
                                                    rich_help_panel="Page Dimensions")] = 30,
         topMargin: Annotated[int, typer.Option(metavar="NUMBER",
                                                 help="Configure the margin at the top of the page.",
                                                 rich_help_panel="Page Dimensions")] = 30,
         bottomMargin: Annotated[int, typer.Option(metavar="NUMBER",
                                                 help="Configure the margin at the bottom of the page.",
                                                 rich_help_panel="Page Dimensions")] = 40,
         leftMargin: Annotated[int, typer.Option(metavar="NUMBER",
                                                 help="Configure the margin at the left side of the page.",
                                                 rich_help_panel="Page Dimensions")] = 20,
         pageHeight: Annotated[int, typer.Option(metavar="NUMBER",
                                                 help="Configure the total height of a page. This defaults to a DIN A4 page.",
                                                 rich_help_panel="Page Dimensions")] = PaperSize.A4.height,
         pageWidth: Annotated[int, typer.Option(metavar="NUMBER",
                                                 help="Configure the total width of a page. This defaults to a DIN A4 page.",
                                                 rich_help_panel="Page Dimensions")] = PaperSize.A4.width,
         ragged: Annotated[bool, typer.Option(rich_help_panel="Page Layout",
                                              help="Allow space at the bottom of each page.",
                                              is_flag=True)] = False,
         raggedLast: Annotated[bool, typer.Option(rich_help_panel="Page Layout",
                                                  help="Allow space at the bottom of the last page.",
                                                  is_flag=True)] = True,
         shift: Annotated[int, typer.Option(rich_help_panel="Page Layout",
                                            help="Manually shift the annotation staves horizontally.",
                                            metavar="NUMBER")] = 0,
         dropFirst: Annotated[bool, typer.Option(rich_help_panel="Behaviour",
                                                 help="Drop the first annotation staff of the first page.",
                                                 is_flag=True)] = False,
         dropLast: Annotated[bool, typer.Option(rich_help_panel="Behaviour",
                                                help="Drop the last annotation staff of the last page.",
                                                is_flag=True)] = False,
         ):
    """Add analytical staves to a score.

    ---------------------------------

    The tool will treat each page of the provided score as one unit
    under which it will add empty staves. Therefore use an external
    tool (e.g. '[link=https://briss.sourceforge.net/]briss[/link]') to
    separate the score into the desired units.

    By default, the tool tries to fit as many systems (plus their
    staves) as possible on one DIN A4 page. This behaviour can be
    overridden, by providing a comma- or space-separated list of
    numbers, declaring how many pages to group together. This is
    especially useful, if you want to keep the page numbers of the
    original score:

    Given a 2-page score of which the first page consists of 4 systems
    and the second of 5 system, the command to keep this grouping is:

    [green bold]add-staves my-score.pdf --combining "4 5"[/]

    Take note of the option [green]--combining "4 5"[/]. This tells
    the tool to combine the first 4 and then the next 5 pages on a
    single page. A page will never be smaller than a DIN A4 page. If
    no numbers are provided [green]--combining ""[/], a single (very
    long) output page will be generated. 
    """
    # print("score: %s\nforce: %s\noutput: %s\ngroups: %s\nstaves: %s\nabove: %s\ninnerSpacing: %s\nouterSpacing: %s\ntopMaring: %s\nbottomMargin: %s\nleftMargin: %s\npageHeight: %s\npageWidth: %s\n"
    #       % (score, force, output, groups, staves, above, innerSpacing, outerSpacing, topMargin, bottomMargin, leftMargin, pageHeight, pageWidth))
    
    reader = PdfReader(score)
    systems = [[staves, score] if above else [score, staves] for score in reader.pages]

    # A list of pages containing systems.
    pages: List[List[PageObject]] = [[]]

    # And some state to keep track of the current page.
    pageIndex = 0
    systemIndex = 0
    groupIndex = 0

    # Loop over all systems and decide whether to append them to a page in
    # PAGES or start a new page.
    while systemIndex < len(systems):
        system = systems[systemIndex]
        
        # Decide whether to include the system on the page or start a
        # new page.
        match groups:
            case None: 
                # Layout on a DIN A4 page.
                if getHeight(pages[pageIndex] + [system],
                          innerSpacing, outerSpacing,
                          topMargin, bottomMargin) <= pageHeight:
                    pages[pageIndex].append(system)
                else:
                    pageIndex += 1
                    pages.append([])
                    pages[pageIndex].append(system)
            case []:
                # Draw all systems on a single page.
                pages[pageIndex].append(system)
            case _:
                # Follow the grouping
                if groupIndex == len(groups):
                    groups = None
                    systemIndex -= 1
                elif len(pages[pageIndex]) < groups[groupIndex]:
                    pages[pageIndex].append(system)
                elif len(pages[pageIndex]) == groups[groupIndex]:
                    groupIndex += 1
                    pageIndex += 1
                    pages.append([])
                    pages[pageIndex].append(system)

        # Increase the running index.
        systemIndex += 1

    # The only thing left is to write PAGES to a new document.
    writer = PdfWriter()

    for index, page in enumerate(pages):
        printPage(page,
                  writer,
                  innerSpacing,
                  outerSpacing,
                  topMargin,
                  bottomMargin,
                  leftMargin,
                  pageHeight,
                  pageWidth,
                  raggedLast if (index + 1) == len(pages) else ragged,
                  shift,
                  dropFirst if index == 0 else False,
                  dropLast if (index + 1) == len(pages) else False,
                  )

    # Write to disk.
    print(output)
    with open(output, "wb") as fp:
        writer.write(fp)
            
                
if __name__ == "__main__":
    app()



# File Local Variables #

# Local Variables:
# eval: (page-mode +1)
# End:



