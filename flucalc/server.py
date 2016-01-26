from statistics import mean
from collections import namedtuple

import flask
from flask_wtf import Form
from wtforms.fields import TextAreaField, SubmitField, FloatField
from wtforms import validators, ValidationError

from . import flucalc
from . import keys

app = flask.Flask(__name__)
app.secret_key = keys.secret_key


MediaDescription = namedtuple('MediaDescription', ['c', 'd', 'v'])


Values = namedtuple('Values', ['m', 'mu', 'mu_interval'])
CalcResult = namedtuple('CalcResult', ['raw', 'corrected', 'mean_frequency'])


def volume_validator(_, field):
    if field.data is not None and float(field.data) <= 0:
        raise ValidationError('Non positive volume')


def clones_validator(_, field):
    assert field.data
    clones = []
    for pos, clone in enumerate(field.data.split(), 1):
        try:
            value = float(clone)
        except ValueError:
            if len(clone) > 5:
                clone = clone[:5] + '...'
            message = 'Value #{} is not a valid float: "{}"'.format(pos, clone)
            raise ValidationError(message)
        clones.append(value)
    if any(clone < 0 for clone in clones):
        raise ValidationError('Negative number of clones')


dilution_validator = validators.NumberRange(min=1, message='Must be &#8805; 1')


class FluctuationInputForm(Form):
    v_total = FloatField('Volume of a culture <i>(&#956;l)</i>, V<sub>tot</sub>',
                         [volume_validator], default=200)
    c_selective = TextAreaField('Observed numbers of clones, C<sub>sel</sub>',
                                [validators.DataRequired(), clones_validator])
    d_selective = FloatField('Dilution factor, D<sub>sel</sub>', [dilution_validator])
    v_selective = FloatField('Volume plated <i>(&#956;l)</i>, V<sub>sel</sub>', [volume_validator])

    c_complete = TextAreaField('Observed numbers of clones, C<sub>com</sub>',
                               [validators.DataRequired(), clones_validator])
    d_complete = FloatField('Dilution factor, D<sub>com</sub>', [dilution_validator])
    v_complete = FloatField('Volume plated <i>(&#956;l)</i>, V<sub>com</sub>', [volume_validator])

    submit = SubmitField("Calculate")


@app.route('/', methods=['GET', 'POST'])
def main_page():
    form = FluctuationInputForm(csrf_enabled=False)
    if not form.is_submitted():
        return flask.render_template('input_form.html', form=form)

    if form.validate():
        result_data = process_input(flask.request.form)
        return flask.render_template('result.html', results=result_data)

    for field in form:
        try:
            # extract field symbol
            field_name = field.label.text.rsplit(',', 1)[1].strip()
        except IndexError:
            field_name = field.label.text
        if field.errors:
            message = '; '.join(error.lower().rstrip('.') for error in field.errors)
            flask.flash(flask.Markup('<code>{}:</code> {}'.format(field_name, message)))

    return flask.render_template('input_form.html', form=form)


def process_input(form):
    v_total = float(form['v_total'])
    selective = parse_media_description(form, section='selective')
    complete = parse_media_description(form, section='complete')
    complete = complete._replace(c=mean(complete.c))

    c_complete_to_selective = complete.c * selective.v * complete.d / complete.v / selective.d

    raw_results = calc_raw_results(selective, c_complete_to_selective)
    corrected_results = calc_corrected_results(raw_results, selective, v_total)

    return CalcResult(
        raw=raw_results,
        corrected=corrected_results,
        mean_frequency=mean(flucalc.frequency(r, c_complete_to_selective) for r in selective.c)
    )


def calc_raw_results(selective, c_complete_to_selective):
    m = flucalc.m_mle_estimation(selective.c)
    mu = flucalc.calc_mutation_rate(m, c_complete_to_selective)
    interval = flucalc.mutation_rate_limits(m, mu, len(selective.c))
    return Values(m, mu, interval)


def calc_corrected_results(raw_results, selective, v_total):
    z_selective = calc_z(selective, v_total)
    plating_multiplier = flucalc.plating_efficiency_multiplier(z_selective)
    m = raw_results.m * plating_multiplier
    mu = raw_results.mu * plating_multiplier * z_selective
    interval = flucalc.mutation_rate_limits(m, mu, len(selective.c))
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
