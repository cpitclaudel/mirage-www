#!/usr/bin/env python3

"""Parse outputs of `benchmark.py`

Usage: plot.py FOLDER-CONTAINING-HARS-FILES.
"""

from collections import defaultdict
import json
import os
import os.path
from typing import *
import sys
import statistics

import matplotlib
from matplotlib import pyplot

import numpy as np
import scipy.stats

# def read_wget_times(folder):
#     """Read all wget.time files in `folder`.

#     Returns a mapping from configurations to measurements.
#     """
#     root, dirnames, _fnames = next(os.walk(folder))
#     data = defaultdict(list) # type: Dict[Tuple[str], List[int]]
#     for dirname in dirnames:
#         config, _idx = dirname.split(".")
#         config = tuple(config.split("+"))
#         dirpath = os.path.join(root, dirname)
#         data[config].append(read_wget_time(dirpath))
#     return data

def read_times(folder):
    with open(os.path.join(folder, "all.json")) as f:
        return json.load(f)

# https://stackoverflow.com/questions/15033511/compute-a-confidence-interval-from-sample-data
def stats(data, confidence=0.95):
    n = len(data)
    data = np.array(data) / 1000.0
    mean, se = np.mean(data), scipy.stats.sem(data)
    h = se * scipy.stats.t.ppf((1 + confidence) / 2., n - 1)
    return mean, h # h: confidence interval half-width

INTERESTING_CONFIGS = [("MirageOS ('blog/' page)", ('',)),
                       # ("+ verified Ethernet encoding", ('ethif-encoding',)),
                       ("+ verified Ethernet encoding & decoding", ('ethif-encoding', 'ethif-decoding',)),
                       # ("+ verified IPv4 encoding", ('ethif-encoding', 'ethif-decoding',
                       #                               'ipv4-encoding')),
                       ("+ verified IPv4 encoding & decoding", ('ethif-encoding', 'ethif-decoding',
                                                     'ipv4-encoding', 'ipv4-decoding')),
                       # ("+ verified TCP encoding", ('ethif-encoding', 'ethif-decoding',
                       #                              'ipv4-encoding', 'ipv4-decoding',
                       #                              'tcp-encoding')),
                       ("+ verified TCP encoding & decoding", ('ethif-encoding', 'ethif-decoding',
                                                    'ipv4-encoding', 'ipv4-decoding',
                                                    'tcp-encoding', 'tcp-decoding'))]

from collections import OrderedDict
HEX = OrderedDict((("yellow", ("#fce94f", "#edd400", "#c4a000")),
                   ("orange", ("#fcaf3e", "#f57900", "#ce5c00")),
                   ("brown",  ("#e9b96e", "#c17d11", "#8f5902")),
                   ("green",  ("#8ae234", "#73d216", "#4e9a06")),
                   ("blue",   ("#729fcf", "#3465a4", "#204a87")),
                   ("purple", ("#ad7fa8", "#75507b", "#5c3566")),
                   ("red",    ("#ef2929", "#cc0000", "#a40000")),
                   ("grey",   ("#eeeeec", "#d3d7cf", "#babdb6")),
                   ("black",  ("#888a85", "#555753", "#2e3436"))))

COLOR_NAMES = ["orange", "green", "purple"]
COLORS = [HEX["black"]] + [HEX[color] for color in COLOR_NAMES]

def plot(folder):
    bars = {tuple(config.split("+")): stats([w["real"] for w in wget_times])
            for (config, wget_times) in read_times(folder).items()}

    from pprint import pprint; pprint(bars)
    fig = pyplot.gcf()
    fig.set_size_inches((4, 0.7))

    ax2 = pyplot.subplot(1, 1, 1)
    axs = (ax2,)
    # ax1 = pyplot.subplot2grid((1, 20), (0, 0))
    # ax2 = pyplot.subplot2grid((1, 20), (0, 1), colspan=19, sharey=ax1)
    # axs = (ax1, ax2)

    matplotlib.rcParams.update({
        "font.size": 6,
        "font.family": "Ubuntu Mono",
        "font.serif": "times",
        "axes.titlesize": "medium",
        "xtick.labelsize": "5",
        "ytick.labelsize": "small",
        # "legend.fontsize": "small",
        # "text.usetex": True,
        "text.latex.unicode": True,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05
    })

    chunks = [0]
    labels = []
    height = 0.5
    for idx, (label, config) in enumerate(INTERESTING_CONFIGS):
        avg, h = bars[config]
        print(label, avg)
        d = (avg - chunks[-1]) / chunks[-1]
        delta = " ({}{:.1%})".format("+" if d >= 0 else "", d) if idx > 0 else ""
        # delta = delta.replace("%", "\\%")
        chunks.append(avg)
        if not label.startswith("*"):
            y = -idx * height * 1.2
            labels.append((y + height / 2, label + delta))
            for ichunk in range(1, len(chunks)):
                width = chunks[ichunk] - chunks[ichunk - 1]
                color = COLORS[ichunk - 1][0]
                edgecolor = COLORS[ichunk - 1][2]
                x = chunks[ichunk - 1]
                for ax in axs:
                    ax.barh(y + height / 2, [width], left=x, height=height, color=color, edgecolor=edgecolor, linewidth=0.2)
            ax2.errorbar(chunks[-1], y + height / 2, xerr=h, ecolor="black", capsize=2, capthick=1, elinewidth=1)
        print(h)
        print(chunks)
        # for ax in axs:
        #     ax.errorbar(avg, - idx + 0.4, xerr=stdev, color="black")

    for ax in axs:
        ax.set_ylim((1 - len(INTERESTING_CONFIGS)) * height * 1.2, height)
    ax2.xaxis.set_ticks_position('bottom')
    ax2.tick_params('both', length=2, width=1, which='major')
    ax2.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.2f s'))
    for tick in ax2.xaxis.get_major_ticks():
        # import pdb; pdb.set_trace()
        tick.label.set_fontsize(6)
        tick.label.set_family("Ubuntu Mono")

    # patches = [matplotlib.patches.Patch(color=c) for c in COLORS[1:]]
    # legends = [lbl[2:] for (lbl, _) in INTERESTING_CONFIGS[1:]]
    # legends[0] = "Overhead of parsing {} packets with Fiat".format(legends[0])
    # fig.legend(patches, legends, 'lower center', ncol=3, fontsize=7)

    # datamin = min(chunks[1:])
    # rmin, rmax = (0.9 * datamin, 1.02 * max(chunks))
    rmin, rmax = (0, 1.03 * max(chunks))
    # ax1.set_xlim(0, (rmax - rmin) / 19)
    ax2.set_xlim(rmin, rmax)
    ax2.yaxis.set_ticks([])
    # for label in ax2.yaxis.get_ticklabels():
    #     label.set_visible(False)
    for y, label in labels:
        # label = r"\textbf{" + label + "}"
        ax2.text(rmin,  y, " " + label, ha='left', va='center', size=8)
        # ax2.text((rmin + datamin) / 2,  y, label, ha='center', va='center')
    # ax1.xaxis.set_ticks([0])
    fig.savefig("mirage-www.pdf", bbox_inches="tight")

def main(folder):
    plot(folder)

if __name__ == '__main__':
    main(sys.argv[1])
