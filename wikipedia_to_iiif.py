import flask
from flask_cors import CORS
import requests
from iiif_prezi.factory import ManifestFactory
from bs4 import BeautifulSoup
import json


app = flask.Flask(__name__)
CORS(app)

WIKI_TEMPLATE = u"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts|images&imlimit=max&exintro=&titles="
COMMONS_TEMPLATE = u"https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|commonmetadata&iiurlwidth={0}&titles={1}"
HEADERS = { 'user-agent': 'iiif_test (tom.crane@digirati.com)' }

def sanitise(html):
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup.findAll(True): 
        tag.attrs = None
    return "".join([unicode(x) for x in soup.find('body').findChildren()])


@app.route('/')
def index():
    with open('interesting_examples.json') as examples:
        return flask.render_template('index.html', examples=json.load(examples))


def get_manifest_url(wiki_slug):
    return flask.url_for('iiif_manifest', wiki_slug=wiki_slug, _external=True)


@app.route('/wiki/<wiki_slug>')
def wiki(wiki_slug):
    return flask.render_template('wiki.html', manifest=get_manifest_url(wiki_slug))


@app.route('/iiif/<wiki_slug>')
def iiif_manifest(wiki_slug):
    # first get the image information for the slug
    res = requests.get(WIKI_TEMPLATE + wiki_slug, headers=HEADERS)
    details = res.json()
    if "pages" in details.get('query', {}):
        page = details["query"]["pages"].values()[0]
        titles = u"|".join([image["title"] for image in page["images"]])
        # Now get the image information
        large_images = COMMONS_TEMPLATE.format(u"1600", titles)
        thumbnails = COMMONS_TEMPLATE.format(u"100", titles)
        print "______________________"
        print large_images
        print thumbnails
        print "______________________"
        large_images_resp = requests.get(large_images, headers=HEADERS)
        query = large_images_resp.json()['query']


        thumbs_resp = requests.get(thumbnails, headers=HEADERS)
        thumbs_query = thumbs_resp.json()['query']
        fac = ManifestFactory()
        fac.set_base_prezi_uri(get_manifest_url(''))
        manifest = fac.manifest(ident=get_manifest_url(wiki_slug), label=page['title'])
        manifest.description = sanitise(page['extract'])
        sequence = manifest.sequence(ident="normal", label="default order")
        for image_page in query.get('pages', {}).values():
            page_id = image_page.get('pageid', None)
            if page_id is not None:
                canvas = sequence.canvas(ident='c%s' % page_id, label=image_page['title'])
                wiki_info = image_page['imageinfo'][0]
                canvas.set_hw(wiki_info['thumbheight'], wiki_info['thumbwidth'])
                anno = canvas.annotation(ident='a%s' % page_id)
                img = anno.image(ident=wiki_info['thumburl'], iiif=False)
                img.set_hw(wiki_info['thumbheight'], wiki_info['thumbwidth'])
                thumb_page = thumbs_query['pages'].get(str(page_id), None)
                if thumb_page is not None:
                    thumb_info = thumb_page['imageinfo'][0]
                    canvas.thumbnail = fac.image(ident=thumb_info['thumburl'])
                    canvas.thumbnail.set_hw(thumb_info['thumbheight'], thumb_info['thumbwidth'])
        return flask.jsonify(manifest.toJSON(top=True))

    return flask.jsonify({})


if __name__ == "__main__":
    app.run(threaded=True, debug=True, port=5000, host='0.0.0.0')
