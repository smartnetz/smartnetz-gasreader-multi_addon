ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY run.sh /run.sh
COPY app.py /app.py
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
