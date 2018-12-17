# ===============================================
# pre-built python build stage
FROM python:3.7-alpine3.8 as python-build

RUN apk add -U gcc g++ musl-dev zlib-dev libuv libffi-dev make jpeg-dev openjpeg libjpeg-turbo

ADD ./requirements.txt /home/root/requirements.txt
RUN pip install -r /home/root/requirements.txt
# get rid of unnecessary files to keep the size of site-packages and the final image down
RUN find /usr/local/lib/python3.7/site-packages \
    -name '*.pyc' -o \
    -name '*.pyx' -o \
    -name '*.pyd' -o \
    -name '*.c' -o \
    -name '*.h' -o \
    -name '*.txt' | xargs rm
RUN find /usr/local/lib/python3.7/site-packages -name '__pycache__' -delete

# ===============================================
# final image
FROM python:3.7-alpine3.8
ENV PYTHONUNBUFFERED 1
ENV APP_ON_DOCKER 1
ENV ATOOLBOX_ROOT_DIR app
WORKDIR /home/root
USER root

COPY --from=python-build /usr/local/bin/atoolbox /usr/local/bin/
COPY --from=python-build /lib/* /lib/
COPY --from=python-build /usr/lib/* /usr/lib/
COPY --from=python-build /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
RUN ls -lhR /usr/local/lib/python3.7/site-packages

ADD ./app /home/root/app

ARG COMMIT
ENV COMMIT $COMMIT
ARG BUILD_TIME
ENV BUILD_TIME $BUILD_TIME

CMD ["atoolbox", "web"]
