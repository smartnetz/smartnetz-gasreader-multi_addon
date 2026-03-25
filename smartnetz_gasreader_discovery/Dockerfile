ARG BUILD_FROM
FROM ${BUILD_FROM}

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY run.sh /run.sh
COPY app.py /app.py
RUN chmod +x /run.sh

CMD ["/run.sh"]
