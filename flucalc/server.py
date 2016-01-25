from statistics import mean
from collections import namedtuple

import flask
from flask_wtf import Form
from wtforms.fields import TextAreaField, SubmitField, FloatField

from . import flucalc
from . import keys

app = flask.Flask(__name__)
app.secret_key = keys.secret_key


MediaDescription = namedtuple('MediaDescription', ['c', 'd', 'v'])


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
    selective = parse_media_description(form, section='selective')
    complete = parse_media_description(form, section='complete')
    complete = complete._replace(c=mean(complete.c))

    c_complete_to_selective = complete.c * selective.v * complete.d / complete.v / selective.v

    raw_results = calc_raw_results(selective, c_complete_to_selective)
    corrected_results = calc_corrected_results(raw_results, selective, v_total)

    return CalcResult(
        raw=raw_results,
        corrected=corrected_results,
        mean_frequency=mean(flucalc.frequency(r, complete.c) for r in selective.c)
    )


def calc_raw_results(selective, mean_complete):
    m = flucalc.calc_estimated_mutants(selective)
    mu = flucalc.calc_mutation_rate(m, mean_complete)
    interval = flucalc.mutation_rate_limits(m, mu, len(selective.c))
    return Values(m, mu, interval)


def calc_corrected_results(raw_results, selective, v_total):
    z_selective = calc_z(selective.d, selective.v, v_total)
    plating_multiplier = flucalc.plating_efficiency_multiplier(z_selective)
    m = raw_results.m * plating_multiplier
    mu = raw_results.mu * plating_multiplier * z_selective
    interval = flucalc.mutation_rate_limits(m, mu, len(selective.c))
    return Values(m, mu, interval)


def calc_results(selective, complete, z):
    m = flucalc.calc_estimated_mutants(selective, z=z)
    mu, interval = flucalc.calc_mutation_rate(m, complete)
    return Values(m, mu, interval)


def calc_z(d, v, v_total):
    return v / d / v_total


def parse_media_description(form, *, section):
    """ Extract media description values from the form.
    :param form: `FluctuationInputForm` object
    :param section: ``'complete'`` or ``'selective'``
    :return: `MediaDescription` value
    """
    return MediaDescription(
            c=[float(row) for row in form['c_' + section].split()],
            d=float(form['d_' + section]),
            v=float(form['v_' + section])
    )
