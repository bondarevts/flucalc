import math
from statistics import mean
from collections import namedtuple
from functools import partial

import flask
from flask_wtf import Form
from wtforms.fields import TextAreaField, SubmitField, FloatField
from wtforms import validators, ValidationError

from . import flucalc
from . import keys

version = '0.1.4'

app = flask.Flask(__name__)
app.secret_key = keys.secret_key


FieldError = namedtuple('FieldError', ['field_name', 'message'])

MediaDescription = namedtuple('MediaDescription', ['c', 'd', 'v'])


Values = namedtuple('Values', ['m', 'mu', 'mu_interval', 'power'])
CalcResult = namedtuple('CalcResult', ['raw', 'corrected', 'mean_frequency'])

CalcStep = namedtuple('CalcStep', ['pos', 'description', 'value', 'img'])


def volume_value(_, field):
    if field.data is not None and float(field.data) <= 0:
        raise ValidationError('Non positive volume')


def clones_numbers(_, field):
    if field.data is not None:
        if any(clone < 0 for clone in field.data):
            raise ValidationError('Negative number of clones')


def int_values(_, field):
    if field.data is not None:
        if not all(value.is_integer() for value in field.data):
            raise ValidationError('Number must be integer')


dilution_validator = validators.NumberRange(min=1, message='Must be &#8805; 1')


# noinspection PyAttributeOutsideInit
class MultiFloatAreaField(TextAreaField):
    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        if self.data:
            return '\n'.join(self.data)
        return ''

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        data = []
        for pos, value in enumerate(valuelist[0].split(), 1):
            try:
                float_value = float(value)
            except ValueError as e:
                self.data = None
                if len(value) > 5:
                    value = value[:5] + '...'
                message = 'Value #{} is not a valid float: "{}"'.format(pos, value)
                raise ValueError(message) from e
            data.append(float_value)
        self.data = data


class FluctuationInputForm(Form):
    v_total = FloatField('Volume of a culture <i>(&mu;l)</i>, V<sub>tot</sub>',
                         [volume_value], default=200)
    c_selective = MultiFloatAreaField('Observed numbers of clones, C<sub>sel</sub>',
                                      [clones_numbers, int_values])
    d_selective = FloatField('Dilution factor, D<sub>sel</sub>', [dilution_validator])
    v_selective = FloatField('Volume plated <i>(&mu;l)</i>, V<sub>sel</sub>', [volume_value])

    c_complete = MultiFloatAreaField('Observed numbers of clones, C<sub>com</sub>',
                                     [clones_numbers])
    d_complete = FloatField('Dilution factor, D<sub>com</sub>', [dilution_validator])
    v_complete = FloatField('Volume plated <i>(&mu;l)</i>, V<sub>com</sub>', [volume_value])

    submit = SubmitField("Calculate")


@app.route('/', methods=['GET', 'POST'])
def main_page():
    form = FluctuationInputForm(flask.request.form, csrf_enabled=False)
    render_page_template = partial(flask.render_template,
                                   'form_with_results.html',
                                   format_number_with_power=format_number_with_power,
                                   form=form, version=version)
    if not form.is_submitted():
        return render_page_template()

    if form.validate():
        solution = Solver(form)
        return render_page_template(results=solution.result_data, process=solution.calc_steps)

    for error in get_errors(form):
        message = '<code>{error.field_name}:</code> {error.message}'.format(error=error)
        flask.flash(flask.Markup(message))

    return render_page_template()


def get_errors(form):
    for field in form:
        try:
            # extract field symbol
            field_name = field.label.text.rsplit(',', 1)[1].strip()
        except IndexError:
            field_name = field.label.text
        if field.errors:
            message = '; '.join(error.lower().rstrip('.') for error in field.errors)
            yield FieldError(field_name, message)


def _calc_min_power(*values):
    return int(min(math.floor(math.log10(value)) for value in values))


def format_number_with_power(number, power, precision=4):
    return '{0:.{1}f}e{2:+03d}'.format(number / pow(10, power), precision, power)


class Solver:
    def __init__(self, form):
        self._form = form
        self._result = None
        self._steps = []

    @property
    def result_data(self):
        if not self._result:
            self._process_input()
        return self._result

    @property
    def calc_steps(self):
        if not self._steps:
            self._process_input()
        return self._steps

    def _add_step(self, position, description, value, img=None):
        self._steps.append(CalcStep(position, description, float(value), img))

    def _process_input(self):
        v_total = self._form.v_total.data
        selective = MediaDescription(
            c=self._form.c_selective.data,
            d=self._form.d_selective.data,
            v=self._form.v_selective.data
        )
        complete = MediaDescription(
            c=mean(self._form.c_complete.data),
            d=self._form.d_complete.data,
            v=self._form.v_complete.data
        )

        self._add_step(2, 'Mean of C<sub>com</sub>', complete.c, 'mean_c_com')
        c_complete_to_selective = complete.c * selective.v * complete.d / complete.v / selective.d
        self._add_step(3, 'C<sub>com</sub> adjusted to selective media', c_complete_to_selective,
                       'c_com_sel')

        raw_results = self._calc_raw_results(selective, c_complete_to_selective)
        corrected_results = self._calc_corrected_results(raw_results, selective, v_total)

        frequency = mean(flucalc.frequency(r, c_complete_to_selective) for r in selective.c)
        self._add_step(13, 'Mean frequency, <span style="border-top:1px solid black">f</span>',
                       frequency, 'frequency')
        self._result = CalcResult(
            raw=raw_results,
            corrected=corrected_results,
            mean_frequency=frequency
        )
        self._steps.sort()

    def _calc_raw_results(self, selective, c_complete_to_selective):
        m = flucalc.m_mle_estimation(selective.c)
        self._add_step(1, 'Number of mutations, m', m, 'm_raw')
        mu = flucalc.calc_mutation_rate(m, c_complete_to_selective)
        self._add_step(4, 'Mutation rate, &mu;', mu, 'mu_raw')
        interval = flucalc.mutation_rate_limits(m, mu, len(selective.c))
        self._add_step(5, 'Lower limit for mutation rate, &mu;<sup>&minus;</sup>',
                       interval.lower, 'mu_raw_lower')
        self._add_step(6, 'Upper limit for mutation rate, &mu;<sup>+</sup>',
                       interval.upper, 'mu_raw_upper')
        return Values(m, mu, interval, _calc_min_power(mu, *interval))

    def _calc_corrected_results(self, raw_results, selective, v_total):
        z_selective = self._calc_z(selective, v_total)
        self._add_step(7, 'Fraction of a culture plated on selective media, z<sub>sel</sub>',
                       z_selective, 'z_sel')
        plating_multiplier = flucalc.plating_efficiency_multiplier(z_selective)
        self._add_step(8, 'Plating efficiency multiplier, &#969;', plating_multiplier,
                       'plating_efficiency')
        m = raw_results.m * plating_multiplier
        self._add_step(9, 'Corrected number of mutations, m<sub>&#969;</sub>', m, 'm_corr')
        mu = raw_results.mu * plating_multiplier * z_selective
        self._add_step(10, 'Corrected mutation rate, &mu;<sub>&#969;</sub>', mu, 'mu_corr')
        interval = flucalc.mutation_rate_limits(m, mu, len(selective.c))
        self._add_step(11, 'Corrected lower limit for mutation rate, '
                           '&mu;<span style="position: relative;"><sub>&omega;</sub>'
                           '<sup style="position: absolute; left: 0;">&#8722;</sup><span>',
                       interval.lower, 'mu_corr_lower')
        self._add_step(12, 'Corrected upper limit for mutation rate, '
                           '&mu;<span style="position: relative;"><sub>&omega;</sub>'
                           '<sup style="position: absolute; left: 0;">+</sup><span>',
                       interval.upper, 'mu_corr_upper')
        return Values(m, mu, interval, _calc_min_power(mu, *interval))

    def _calc_z(self, media_description, v_total):
        return media_description.v / media_description.d / v_total
