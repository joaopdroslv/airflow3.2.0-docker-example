FROM apache/airflow:3.2.0

USER root

# Install Chrome dependencies + Chrome itself
RUN apt-get update && apt-get install -y \
   wget \
   gnupg \
   ca-certificates \
   fonts-liberation \
   libasound2 \
   libatk-bridge2.0-0 \
   libatk1.0-0 \
   libcups2 \
   libdbus-1-3 \
   libgdk-pixbuf2.0-0 \
   libnspr4 \
   libnss3 \
   libx11-xcb1 \
   libxcomposite1 \
   libxdamage1 \
   libxrandr2 \
   xdg-utils \
   --no-install-recommends \
&& wget -q -O /tmp/chrome.deb \
   https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
&& apt-get install -y /tmp/chrome.deb \
&& rm /tmp/chrome.deb \
&& rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /

RUN pip install --no-cache-dir -r /requirements.txt
