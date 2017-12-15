import flask
from flask_cors import CORS
from flask_cache import Cache
import requests
from iiif_prezi.factory import ManifestFactory
from html_sanitizer import Sanitizer
import json

# from lxml import etree


app = flask.Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': './gen/cache'})
CORS(app)

WIKI_TEMPLATE = u"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts|images&imlimit=max&exintro=&titles="
COMMONS_TEMPLATE = u"https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|timestamp|user|mime|extmetadata&iiurlwidth={0}&titles={1}"
HEADERS = { 'user-agent': 'iiif_test (tom.crane@digirati.com)' }
sanitizer = Sanitizer({
    'tags': {
        'a', 'b', 'br', 'i', 'img', 'p', 'span'
    },
    'attributes': {
        'a': ('href'),
        'img': ('src', 'alt')
    },
    'empty': {'br'},
    'separate': {'a', 'p'}
})

def cache_key():
    return flask.request.url

def safe_str(obj):
    """ return the byte string representation of obj """
    try:
        return str(obj)
    except UnicodeEncodeError:
        # obj is unicode
        return unicode(obj).encode('ascii', 'xmlcharrefreplace')

def sanitise(html):

    # test
    # print "+++++++++++++++++++++++++++++++++++++++++++++"
    # print html
    # dom = etree.HTML(unicode(html))
    # print "============================================="
    # print etree.tostring(dom)
    # print "============================================="

    return sanitizer.sanitize(safe_str(html))


@app.route('/')
@cache.cached(timeout=20)
def index():
    with open('interesting_examples.json') as examples:
        return flask.render_template('index.html', examples=json.load(examples))


def get_manifest_url(wiki_slug):
    return flask.url_for('iiif_manifest', wiki_slug=wiki_slug, _external=True)


@app.route('/wiki/<wiki_slug>')
def wiki(wiki_slug):
    return flask.render_template('wiki.html', manifest=get_manifest_url(wiki_slug))


@app.route('/img/<identifier>')
def image_id(identifier):
    """Redirect a plain image id"""
    return flask.redirect(flask.url_for('image_info', identifier=identifier), code=303)


@app.route('/img/<identifier>/info.json')
@cache.cached(timeout=600)
def image_info(identifier):
    """
        TODO: Create an info.json for the wikipedia image
        Use available sizes as per https://tomcrane.github.io/scratch/osd/iiif-sizes.html
        This may not be worth it, just use a big image. Google Art Project images 
        on Wikipedia tend to have several smallish sizes then one huge one that is really 
        too big.
    """


@app.route('/img/<identifier>/<region>/<size>/<rotation>/<quality>.<fmt>')
def image_api_request(identifier, **kwargs):
    """
        TODO: A IIIF Image API request; redirect to Wikimedia image URI
    """


def get_image_details(titles, size):
    url = COMMONS_TEMPLATE.format(unicode(size), titles)
    resp = requests.get(url, headers=HEADERS)
    return resp.json().get('query', {}).get('pages', {})

def set_canvas_metadata(wiki_info, canvas):
    if 'user' in wiki_info:
        canvas.set_metadata({"Wikipedia user": wiki_info['user']})
        extmetadata = wiki_info.get('extmetadata', {})
    for key in extmetadata:
        value = extmetadata[key].get('value', None)
        if key == "LicenseUrl":
            canvas.license = value
        if key == "ImageDescription":
            canvas.label = sanitise(value)
        elif value:
            canvas.set_metadata({key: sanitise(value)})


def make_manifest(wiki_slug):
    """
        Get the wiki article information with a list of its images
        Then get a set of information for each image, and thumbs
    """
    res = requests.get(WIKI_TEMPLATE + wiki_slug, headers=HEADERS)
    details = res.json()
    if "pages" in details.get('query', {}):
        page = details["query"]["pages"].values()[0]
        titles = u"|".join([image["title"] for image in page["images"]])
        large_images = get_image_details(titles, 1600)
        thumbnail_images = get_image_details(titles, 100)
        fac = ManifestFactory()
        fac.set_base_prezi_uri(get_manifest_url(''))
        fac.set_debug("error")
        manifest = fac.manifest(ident=get_manifest_url(wiki_slug), label=page['title'])
        manifest.description = sanitise(page['extract'])
        sequence = manifest.sequence(ident="normal", label="default order")
        for image_page in large_images.values():
            page_id = image_page.get('pageid', None)
            wiki_info = image_page.get('imageinfo', [None])[0]
            if wiki_info is not None and wiki_info['mime'] == "image/jpeg":
                canvas = sequence.canvas(ident='c%s' % page_id, label=image_page['title'])
                canvas.set_hw(wiki_info['thumbheight'], wiki_info['thumbwidth'])
                set_canvas_metadata(wiki_info, canvas)
                anno = canvas.annotation(ident='a%s' % page_id)
                img = anno.image(ident=wiki_info['thumburl'], iiif=False)
                img.set_hw(wiki_info['thumbheight'], wiki_info['thumbwidth'])
                thumb_page = thumbnail_images.get(str(page_id), None)
                if thumb_page is not None:
                    thumb_info = thumb_page['imageinfo'][0]
                    canvas.thumbnail = fac.image(ident=thumb_info['thumburl'])
                    canvas.thumbnail.format = "image/jpeg"
                    canvas.thumbnail.set_hw(thumb_info['thumbheight'], thumb_info['thumbwidth'])
        return manifest.toJSON(top=True)
    return {}


@app.route('/iiif/<wiki_slug>')
@cache.cached(timeout=600)
def iiif_manifest(wiki_slug):
    return flask.jsonify(make_manifest(wiki_slug))


if __name__ == "__main__":
    app.run(threaded=True, debug=False, port=5000, host='0.0.0.0')
