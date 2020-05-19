"""
Easy conversion of data from different formats to other formats.
"""

import sys
import argparse
import ast

import plotly

import sisl
from sisl.utils import cmd

from .plot import Plot
from .plotutils import get_avail_presets, get_plot_classes
from ._user_customs import PRESETS_FILE, PRESETS_VARIABLE, PLOTS_FILE

__all__ = ['splot']

def general_arguments(parser):

    parser.add_argument('--presets', '-p', type=str, nargs="*", required=False,
                    help=f'The names of the stored presets that you want to use for the settings. Current available presets: {get_avail_presets()}')
    
    parser.add_argument('--template', '-t', type=str, required=False,
                        help=f'''The plotly layout template that you want to use. It is equivalent as passing a template to --layout. 
                        Available templates: {list(plotly.io.templates.keys())}. Default: {plotly.io.templates.default}''')

    parser.add_argument('--layout', '-l', type=ast.literal_eval, required=False,
                        help=f'A dict containing all the layout attributes that you want to pass to the plot.')
    
    parser.add_argument('--save', '-s', type=str, required=False,
                        help='The path where you want to save the plot. Note that you can add the extension .html to save to html.')
    
    parser.add_argument('--no-show', dest='show', action='store_false',
                        help="Pass this flag if you don't want the plot to be displayed.")
    
    parser.add_argument('--shortcuts', '-sh', nargs="*",
                        help="The shortcuts to apply to the plot after it has been built. " +
                        "They should be passed as the sequence of keys that need to be pressed to trigger the shortcut"+
                        "You can pass as many as you want. If the built plot is an animation, the shortcuts will be applied"+
                        "to each plot separately"
    )

                    

def splot():

    parser = argparse.ArgumentParser(prog='splot', 
                                     description="Command utility to plot files fast. This command allows great customability." +
                                     "\n\nOnly you know how you like your plots. Therefore, a nice way to use this command is by " +
                                     "using presets that you stored previously. Note that you can either use sisl's provided presets" +
                                     f" or define your own presets. Sisl is looking for presets under the '{PRESETS_VARIABLE}' variable" +
                                     f" defined in {PRESETS_FILE}. It should be a dict containing all your presets.",
    )

    # Add default sisl version stuff
    cmd.add_sisl_version_cite_arg(parser)

    parser.add_argument('--files', "-f", type=str, nargs="*", default=[],
                        help='The files that you want to plot. As many as you want.'
    )

    general_arguments(parser)
            
    for param in Plot._parameters:
        if param.dtype is not None and not isinstance(param.dtype, str):
            parser.add_argument(f'--{param.key}', type=param._parse, required=False, help=getattr(param, "help", ""))

    subparsers = parser.add_subparsers(
        help="YOU DON'T NEED TO PASS A PLOT CLASS. You can provide a file (see the -f flag) and sisl will decide for you."+
        " However, if you want to avoid sisl automatic choice, you can use these subcommands to select a"+
        " plot class. By doing so, you will also get access to plot-specific settings. Try sgui BandsPlot -h, for example."+
        " Note that you can also build your own plots that will be automatically available here." +
        f" Sisl is looking to import plots defined in {PLOTS_FILE}",
        dest="plot_class"
    )

    avail_plots = get_plot_classes()

    for PlotClass in avail_plots:
        doc = PlotClass.__doc__ or ""
        specific_parser = subparsers.add_parser(PlotClass.plotName(), help=doc.split(".")[0])

        if hasattr(PlotClass, "_default_animation"):
            specific_parser.add_argument('--animated', '-ani', dest="animated", action="store_true", 
                help=f"If this flag is present, the default animation for {PlotClass.__name__} will be build"+
                " instead of a regular plot"
            )

        general_arguments(specific_parser)

        for param in PlotClass._get_class_params()[0]:
            if param.dtype is not None and not isinstance(param.dtype, str):
                specific_parser.add_argument(f'--{param.key}', type=param._parse, required=False, help=getattr(param, "help", ""))
  
    args = parser.parse_args()

    # Select the plotclass that the user requested
    plot_class = Plot
    if args.plot_class:
        for PlotClass in avail_plots:
            if PlotClass.plotName() == args.plot_class:
                plot_class = PlotClass
                break

    settings = { param.key: getattr(args, param.key) for param in plot_class._get_class_params()[0] if getattr(args, param.key, None) is not None}

    layout = {} if args.layout is None else args.layout
    if args.template:
        layout["template"] = args.template

    keyword_args = {**settings, "presets": args.presets, "layout": layout }

    if getattr(args, "animated", False):
        print("Building animation...")
        plot = plot_class.animated(fixed=keyword_args)
    else:
        print("Building plot...")
        plot = plot_class(*args.files, **keyword_args)

    if args.shortcuts:
        print("Applying shortcuts...")
        if getattr(args, "animated", False):
            plots = plot.childPlots
        else:
            plots = [plot]
        for pt in plots:
            for shortcut in args.shortcuts:
                pt.call_shortcut(shortcut)

    if args.save:
        print(f"Saving it to {args.save}...")
        plot.save(args.save)

    if getattr(args, "show", True):
        plot.show()