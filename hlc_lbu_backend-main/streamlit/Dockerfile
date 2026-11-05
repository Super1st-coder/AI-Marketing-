FROM python:3.8

WORKDIR /app/streamlit

COPY . /app/streamlit

RUN pip install  -r requirements.txt 

# COPY run.sh /app/sinergia/run.sh
RUN chmod a+x ./run.sh
CMD ["./run.sh"]