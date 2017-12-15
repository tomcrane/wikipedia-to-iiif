FROM ubuntu

RUN apt-get update -y && apt-get install -y python-pip python-dev build-essential
COPY requirements.txt /opt/iiif/requirements.txt
RUN pip install -r /opt/iiif/requirements.txt

WORKDIR /opt/iiif
EXPOSE 5000

COPY templates /opt/iiif/templates
COPY interesting_examples.json /opt/iiif/
COPY wikipedia_to_iiif.py /opt/iiif/
COPY run_server.sh /opt/iiif/run_server.sh

CMD /opt/iiif/run_server.sh
