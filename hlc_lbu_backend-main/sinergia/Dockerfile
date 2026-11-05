FROM python:3.8

WORKDIR /app/sinergia

COPY . /app/sinergia

RUN pip install -r requirements.txt 

RUN mkdir -p logs && chmod 755 logs

# COPY run.sh /app/sinergia/run.sh
RUN chmod a+x ./run.sh
CMD ["./run.sh"]