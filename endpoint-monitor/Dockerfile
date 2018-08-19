FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY endpoint-monitor.py ./endpoint-monitor.py

CMD [ "python", "./endpoint-monitor.py" ]