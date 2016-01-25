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
    v_selective = FloatField('Volume plated <i>(&#956;l)</i>, V<sub>sel</sub>')

    c_complete = TextAreaField('Observed numbers of clones, C<sub>com</sub>')
    d_complete = FloatField('Dilution factor, D<sub>com</sub>')  # >= 1
    v_complete = FloatField('Volume plated <i>(&#956;l)</i>, V<sub>com</sub>')

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

    z_sel = calc_z(selective, v_total)
    z_com = calc_z(complete, v_total)

    selective = selective._replace(c=[c / z_sel for c in selective.c])
    complete = complete._replace(c=mean(complete.c) / z_com)

    raw_results = calc_raw_results(selective.c, complete.c)
    corrected_results = calc_corrected_results(raw_results, len(selective.c), z_sel, complete.c)

    return CalcResult(
        raw=raw_results,
        corrected=corrected_results,
        mean_frequency=mean(flucalc.frequency(r, complete.c) for r in selective.c)
    )


def calc_raw_results(c_selective, c_complete):
    m = flucalc.m_mle_estimation(c_selective)
    mu = flucalc.calc_mutation_rate(m, c_complete)
    interval = flucalc.mutation_rate_limits(m, mu, len(c_selective))
    return Values(m, mu, interval)


def calc_corrected_results(raw_results, count, z_sel, c_complete):
    plating_multiplier = flucalc.plating_efficiency_multiplier(z_sel)

    m = raw_results.m * plating_multiplier
    mu = m / c_complete
    interval = flucalc.mutation_rate_limits(m, mu, count)
    return Values(m, mu, interval)


def calc_z(media_description, v_total):
    return media_description.v / media_description.d / v_total


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
