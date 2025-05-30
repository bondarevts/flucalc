from flask_wtf import FlaskForm
from markupsafe import Markup
from wtforms.fields import FloatField
from wtforms.fields import SubmitField

from flucalc.fields import MultiFloatAreaField
from flucalc.validators import clones_numbers
from flucalc.validators import dilution_validator
from flucalc.validators import int_values
from flucalc.validators import volume_value


class FluctuationInputForm(FlaskForm):
    class Meta:
        csrf = False

    v_total = FloatField(Markup('Volume of a culture <i>(&mu;l)</i>, V<sub>tot</sub>'), [volume_value], default=200)

    c_selective = MultiFloatAreaField(Markup('Observed numbers of clones, C<sub>sel</sub>'), [clones_numbers, int_values])
    d_selective = FloatField(Markup('Dilution factor, D<sub>sel</sub>'), [dilution_validator])
    v_selective = FloatField(Markup('Volume plated <i>(&mu;l)</i>, V<sub>sel</sub>'), [volume_value])

    c_complete = MultiFloatAreaField(Markup('Observed numbers of clones, C<sub>com</sub>'), [clones_numbers])
    d_complete = FloatField(Markup('Dilution factor, D<sub>com</sub>'), [dilution_validator])
    v_complete = FloatField(Markup('Volume plated <i>(&mu;l)</i>, V<sub>com</sub>'), [volume_value])
 
    submit = SubmitField('Calculate')

    def __repr__(self):
        c_sel = ';'.join(self.c_selective.raw_data[0].split())
        c_com = ';'.join(self.c_complete.raw_data[0].split())
        return 'V_tot={}|C_sel={}|D_sel={}|V_sel={}|C_com={}|D_com={}|V_com={}'.format(
            self.v_total.raw_data[0],
            c_sel, self.d_selective.raw_data[0], self.v_selective.raw_data[0],
            c_com, self.d_complete.raw_data[0], self.v_complete.raw_data[0]
        )
