FROM python:3.12

COPY . /app
RUN pip3 install -r /app/req.txt 