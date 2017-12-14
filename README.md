# wikipedia-to-iiif

Generate a IIIF manifest for a Wikipedia entry

Requests the Wikimedia API description for a given Wikipedia slug to determine what images it has.

Then queries for size information for those image to get thumbnails and 1600px (or closest) images.

Generates a IIIF manifest pointing to those images.

