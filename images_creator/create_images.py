import urllib.request
import urllib.parse
import os.path

imgs_source_path = 'source'
out_base_path = '../flucalc/static/imgs'
request_base_path = "http://latex.codecogs.com/svg.download?%5Clarge%20"

for filename in os.listdir(imgs_source_path):
    print('process', filename, end='... ')
    out_filename, _ = os.path.splitext(os.path.basename(filename))
    out_path = os.path.join(out_base_path, out_filename + '.svg')
    with open(os.path.join(imgs_source_path, filename)) as source_file, open(out_path, 'wb') as out:
        request_url = request_base_path + urllib.parse.quote(source_file.read())
        out.write(urllib.request.urlopen(request_url).read())
    print('end')
