"""Plot the existing, deterministic synthetic fixture; never fit or rewrite data."""
import argparse
import hashlib
import json
import pathlib
import platform
from fractions import Fraction

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from PIL import Image, __version__ as pillow_version

HERE = pathlib.Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_checked(source):
    data = json.loads(source.read_text(encoding='utf-8'))
    if data['kind'] != 'original_synthetic_counterexample' or data['units'] != 'dimensionless':
        raise ValueError('Expected the declared dimensionless synthetic fixture')
    if data['upstream_rankreg_executed'] is not False or not all(data['checks'].values()):
        raise ValueError('Fixture identity or checks differ')
    values = list(map(Fraction, data['labels']))
    if len(values) != 3 or set(data['predictions']) != {'A', 'B'}:
        raise ValueError('Expected three objects and two prediction vectors')
    for name, raw in data['predictions'].items():
        predictions = list(map(Fraction, raw))
        if len(predictions) != len(values):
            raise ValueError('Vector lengths differ')
        chosen = [i for i, value in enumerate(predictions) if value == max(predictions)]
        if len(chosen) != 1:
            raise ValueError('Define a tie rule before plotting')
        mse = sum((p-y)**2 for p, y in zip(predictions, values)) / len(values)
        expected = dict(mse=str(mse), selected_index=chosen[0],
                        selected_value=str(values[chosen[0]]), regret=str(max(values)-values[chosen[0]]))
        if expected != data['results'][name]:
            raise ValueError('Saved scores disagree with the supplied vectors')
    return data


def draw(source, output):
    data = load_checked(source)
    output.mkdir(parents=True, exist_ok=True)
    blue, black, gray = '#1557A6', '#202124', '#62666D'
    style = {'font.family': 'DejaVu Sans', 'font.size': 9,
             'axes.labelsize': 9, 'axes.titlesize': 10,
             'axes.edgecolor': gray, 'axes.linewidth': .65,
             'xtick.labelsize': 9, 'ytick.labelsize': 9,
             'text.color': black, 'axes.labelcolor': black,
             'xtick.color': black, 'ytick.color': black,
             'figure.facecolor': 'white', 'axes.facecolor': 'white',
             'pdf.fonttype': 42, 'svg.fonttype': 'path',
             'svg.hashsalt': 'metric-tradeoff-original-20261101'}
    with plt.rc_context(style):
        fig = plt.figure(figsize=(180/25.4, 108/25.4), dpi=300)
        grid = fig.add_gridspec(2, 2, width_ratios=[1.04, 1],
                               left=.085, right=.965, bottom=.18, top=.78,
                               wspace=.48, hspace=1.25)
        raw_ax = fig.add_subplot(grid[:, 0])
        error_ax = fig.add_subplot(grid[0, 1])
        utility_ax = fig.add_subplot(grid[1, 1])
        fig.text(.085, .94, 'Lower prediction error can give a worse selection',
                 fontsize=12, weight='bold', va='top')
        fig.text(.085, .885, 'Original synthetic example | Three objects | No model training', fontsize=9)
        positions = [1, 2, 3]
        truth = list(map(lambda s: float(Fraction(s)), data['labels']))
        raw_ax.scatter([x-.14 for x in positions], truth, marker='D', s=31,
                       facecolors='white', edgecolors=gray, zorder=3)
        for name, shift, marker, color in [('A', 0, 'o', blue), ('B', .14, 's', black)]:
            predictions = [float(Fraction(s)) for s in data['predictions'][name]]
            raw_ax.scatter([x+shift for x in positions], predictions,
                           marker=marker, s=30, color=color, zorder=4)
        raw_ax.set(title='a  Supplied values', xlabel='Object ID (categorical)',
                   ylabel='Value (dimensionless)', xlim=(.55, 3.45), ylim=(-.15, 3.2))
        raw_ax.set_xticks(positions)
        raw_ax.set_yticks([0, 1, 2, 3])
        raw_ax.grid(axis='y', color='#E5E7EB', linewidth=.6, zorder=0)
        legend = [Line2D([], [], linestyle='none', marker='D', markerfacecolor='white',
                         markeredgecolor=gray, label='True value'),
                  Line2D([], [], linestyle='none', marker='o', color=blue, label='Vector A'),
                  Line2D([], [], linestyle='none', marker='s', color=black, label='Vector B')]
        raw_ax.legend(handles=legend, loc='upper left', frameon=False,
                      handlelength=1, handletextpad=.45, borderpad=.1, labelspacing=.4)
        for ax, field, title, label, limit, ticks in [
                (error_ax, 'mse', 'b  Numerical error: lower is better',
                 'MSE (dimensionless squared)', .75, [0, .3, .6]),
                (utility_ax, 'selected_value', 'c  Selection utility: higher is better',
                 'Selected true value (dimensionless)', 2.5, [0, 1, 2])]:
            scores = [float(Fraction(data['results'][name][field])) for name in ['A', 'B']]
            ax.barh([1, 0], scores, height=.48, color=['white', black],
                    edgecolor=[blue, black], hatch=['////', ''], linewidth=1.1, zorder=3)
            ax.set(title=title, xlabel=label, xlim=(0, limit), ylim=(-.6, 1.6))
            ax.set_yticks([1, 0], ['A', 'B'])
            ax.set_xticks(ticks)
            ax.grid(axis='x', color='#E5E7EB', linewidth=.6, zorder=0)
            for y, score, name in zip([1, 0], scores, ['A', 'B']):
                text = f'{score:.4f}' if field == 'mse' else f'{score:g}'
                ax.text(score+limit*.025, y, text, va='center', fontsize=9)
        for ax in [raw_ax, error_ax, utility_ax]:
            ax.spines[['top', 'right']].set_visible(False)
            title = ax.get_title()
            ax.set_title('')
            ax.set_title(title, loc='left', pad=9)
        fig.text(.085, .045, 'Select the largest predicted value: A chooses object 2; B chooses object 3.', fontsize=9)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        # Check the rendered text boundary. This does not replace visual inspection.
        overflow = []
        for artist in fig.findobj(matplotlib.text.Text):
            if artist.get_visible() and artist.get_text():
                bounds = artist.get_window_extent(renderer)
                if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > fig.bbox.width+1 or bounds.y1 > fig.bbox.height+1:
                    overflow.append(artist.get_text())
        if overflow:
            raise ValueError(f'Text outside figure: {overflow}')
        fig.savefig(output/'metric-tradeoff.svg', metadata={'Date': None, 'Creator': 'Original synthetic fixture visualization'})
        fig.savefig(output/'metric-tradeoff.pdf', metadata={'CreationDate': None, 'ModDate': None,
                                                         'Creator': 'Original synthetic fixture visualization'})
        fig.savefig(output/'metric-tradeoff.png', dpi=300, facecolor='white')
        plt.close(fig)
    with Image.open(output/'metric-tradeoff.png') as rendered:
        rendered.convert('L').save(output/'metric-tradeoff-gray.png', dpi=(300, 300))
        pixels = list(rendered.size)
    names = ['metric-tradeoff.svg', 'metric-tradeoff.pdf', 'metric-tradeoff.png', 'metric-tradeoff-gray.png']
    manifest = {'kind': 'original_synthetic_figure', 'input_sha256': digest(source),
                'plot_script_sha256': digest(pathlib.Path(__file__)),
                'evaluation_script_sha256': data['script_sha256'],
                'python': platform.python_version(), 'matplotlib': matplotlib.__version__, 'pillow': pillow_version,
                'width_mm': 180, 'height_mm': 108, 'png_pixels': pixels, 'dpi': 300,
                'minimum_font_pt': 9, 'text_outside_canvas': overflow,
                'transformations': ['exact rational scores verified from all input vectors',
                                    'fractions converted to float only for plotting',
                                    'horizontal category offsets; no smoothing, exclusions or uncertainty intervals',
                                    'whole-image luminance conversion for grayscale preview'],
                'files': {name: digest(output/name) for name in names}}
    (output/'figure-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=pathlib.Path, default=HERE/'results.json')
    parser.add_argument('--output', type=pathlib.Path, default=HERE)
    args = parser.parse_args()
    draw(args.input.resolve(), args.output.resolve())
