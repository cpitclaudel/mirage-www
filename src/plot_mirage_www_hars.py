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
from clib import tango

def parse_har(fpath):
    """Load har file `fpath`."""
    with open(fpath) as js:
        return json.load(js)

def page_load_time(har):
    """Extract page load time from `har`."""
    pages = har["log"]["pages"]
    assert len(pages) == 1
    # print("{} requests".format(len(har["log"]["entries"])))
    return pages[0]["pageTimings"]["onLoad"]

def read_hars(folder):
    """Read all HAR files in `folder`.

    Returns a mapping from configurations to measurements.
    """
    dirpath, _, filenames = next(os.walk(folder))
    data = defaultdict(list) # type: Dict[Tuple[str], List[int]]
    for fname in filenames:
        config, _ = fname.split("--")
        config = tuple(config.split("-"))
        fpath = os.path.join(dirpath, fname)
        data[config].append(parse_har(fpath))
    return data

def stats(series):
    # ndropped = len(series) // 10
    # without_outliers = sorted(series)[ndropped:-ndropped]
    return statistics.mean(series), statistics.stdev(series)

INTERESTING_CONFIGS = [("Mirage-only", ('',)),
                       ("+ Ethernet encoding", ('ethif', 'encoding',)),
                       ("+ Ethernet decoding", ('ethif', 'encoding', 'ethif', 'decoding',)),
                       ("+ IPv4 encoding", ('ethif', 'encoding', 'ethif', 'decoding',
                                            'ipv4', 'encoding')),
                       ("+ IPv4 encoding", ('ethif', 'encoding', 'ethif', 'decoding',
                                            'ipv4', 'encoding', 'ipv4', 'decoding')),
                       ("+ TCP encoding", ('ethif', 'encoding', 'ethif', 'decoding',
                                           'ipv4', 'encoding', 'ipv4', 'decoding',
                                           'tcp', 'encoding')),
                       ("+ TCP decoding", ('ethif', 'encoding', 'ethif', 'decoding',
                                           'ipv4', 'encoding', 'ipv4', 'decoding',
                                           'tcp', 'encoding', 'tcp', 'decoding'))]

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
COLORS = [HEX["black"][0]] + [hex for color in COLOR_NAMES for hex in HEX[color][0:2]]

def harplot(folder):
    bars = {config: stats([page_load_time(h) for h in hars])
            for (config, hars) in read_hars(folder).items()}

    fig = pyplot.gcf()
    fig.set_size_inches((4, 1))

    ax1 = pyplot.subplot2grid((1, 20), (0, 0))
    ax2 = pyplot.subplot2grid((1, 20), (0, 1), colspan=19, sharey=ax1)
    axs = (ax1, ax2)

    matplotlib.rcParams.update({
        "font.size": 8,
        "font.family": "serif",
        "font.serif": "times",
        "axes.titlesize": "medium",
        "xtick.labelsize": "small",
        "ytick.labelsize": "small",
        "legend.fontsize": "medium",
        "text.usetex": True,
        "text.latex.unicode": True,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05
    })

    chunks = [0]
    labels = []
    for idx, (label, config) in enumerate(INTERESTING_CONFIGS):
        avg, stdev = bars[config]
        delta = " (+{:.1%})".format(max(avg - chunks[-1], 0) / chunks[-1]) if chunks[-1] > 0 else ""
        delta = delta.replace("%", "\\%")
        chunks.append(max(avg, chunks[-1]))
        labels.append((-idx + 0.4, label + delta))
        for ichunk in range(1, len(chunks)):
            width = [chunks[ichunk] - chunks[ichunk-1]]
            color = COLORS[ichunk - 1]
            for ax in axs:
                ax.barh(-idx, width, left=chunks[ichunk-1], color=color, linewidth=0)
        print(stdev)
        # for ax in axs:
        #     ax.errorbar(avg, - idx + 0.4, xerr=stdev, color="black")

    for ax in axs:
        ax.set_ylim(-len(INTERESTING_CONFIGS) + 1, 0.8)
    ax2.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%d$\\:$ms'))

    # patches = [matplotlib.patches.Patch(color=c) for c in COLORS[1:]]
    # legends = [lbl[2:] for (lbl, _) in INTERESTING_CONFIGS[1:]]
    # legends[0] = "Overhead of parsing {} packets with Fiat".format(legends[0])
    # fig.legend(patches, legends, 'lower center', ncol=3, fontsize=7)

    datamin = min(chunks[1:])
    rmin, rmax = (0.9 * datamin, 1.02 * max(chunks))
    ax1.set_xlim(0, (rmax - rmin) / 19)
    ax2.set_xlim(rmin, rmax)
    ax2.yaxis.set_ticks([])
    # for label in ax2.yaxis.get_ticklabels():
    #     label.set_visible(False)
    for y, label in labels:
        ax2.text((rmin + datamin) / 2,  y, label, ha='center', va='center')
    ax1.xaxis.set_ticks([0])
    fig.savefig("mirage-www.pdf", bbox_inches="tight")

def main(folder):
    harplot(folder)

if __name__ == '__main__':
    main(sys.argv[1])
