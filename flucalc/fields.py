from wtforms.fields import TextAreaField


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
