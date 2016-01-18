from statistics import mean
from collections import namedtuple

import flask
from flask_wtf import Form
from wtforms.fields import TextAreaField, SubmitField, FloatField

from . import flucalc
from . import keys

app = flask.Flask(__name__)
app.secret_key = keys.secret_key


Values = namedtuple('Values', ['m', 'mu', 'mu_interval'])
CalcResult = namedtuple('CalcResult', ['raw', 'corrected', 'mean_frequency'])


class FluctuationInputForm(Form):
    v_total = FloatField('Volume of a culture <i>(&#956;l)</i>, V<sub>tot</sub>', default=200)
    c_selective = TextAreaField('Observed numbers of clones, C<sub>sel</sub>')
    d_selective = FloatField('Dilution factor, D<sub>sel</sub>')  # >= 1
    v_selective = FloatField('Volume plated, V<sub>sel</sub>')

    c_complete = TextAreaField('Observed numbers of clones, C<sub>com</sub>')
    d_complete = FloatField('Dilution factor, D<sub>com</sub>')  # >= 1
    v_complete = FloatField('Volume plated, V<sub>com</sub>')

    submit = SubmitField("Calculate")


@app.route('/', methods=['GET', 'POST'])
def main_page():
    form = FluctuationInputForm(csrf_enabled=False)
    if form.validate_on_submit():
        result_data = process_input(flask.request.form)
        return flask.render_template('result.html', results=result_data)
    return flask.render_template('input_form.html', form=form)


def process_input(form):
    v_total = float(form['v_total'])
    r_values, z_sel = parse_section_data(form, v_total, section='selective')
    n_values, z_com = parse_section_data(form, v_total, section='complete')

    return CalcResult(
        raw=calc_results(r_values, n_values, 1),
        corrected=calc_results(r_values, n_values, z_sel),
        mean_frequency=mean(flucalc.frequency(r, n) for r, n in zip(r_values, n_values))
    )


def calc_results(selective, complete, z):
    m = flucalc.calc_estimated_mutants(selective, z=z)
    mu, interval = flucalc.calc_mutation_rate(m, selective, complete)
    return Values(m, mu, interval)


def parse_section_data(form, v_total, *, section):
    """ Extract from the form expected number of clones and plating efficiency
    :param form: `FluctuationInputForm` object
    :param section: ``'complete'`` or ``'selective'``
    :param v_total: float, volume of a culture
    :return: list of expected number of clones with plating efficiency in selected section
    :rtype: (list of float, float)
    """
    d = float(form['d_' + section])
    v = float(form['v_' + section])
    z = v / d / v_total
    expected_c = [float(row) / z for row in form['c_' + section].split()]
    return expected_c, z
