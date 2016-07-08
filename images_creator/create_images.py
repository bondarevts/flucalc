import os.path
import urllib.parse
from urllib.request import urlopen

imgs_source_path = 'source'
out_base_path = '../flucalc/static/imgs'
request_base_path = "http://latex.codecogs.com/svg.download?%5Clarge%20"

for filename in os.listdir(imgs_source_path):
    print('process', filename, end='... ')
    source_path = os.path.join(imgs_source_path, filename)

    out_filename, _ = os.path.splitext(os.path.basename(filename))
    out_path = os.path.join(out_base_path, out_filename + '.svg')

    if os.path.isfile(out_path) and os.path.getmtime(out_path) > os.path.getmtime(source_path):
        print('skipped')
        continue

    with open(source_path) as source_file:
        tex_string = source_file.read()

    request_url = request_base_path + urllib.parse.quote(tex_string)
    svg_text = urlopen(request_url).read()

    if svg_text.startswith(b'Error'):
        print('<<<{}>>>'.format(svg_text.decode()))
        continue

    with open(out_path, 'wb') as out:
        out.write(svg_text)

    print('end')
