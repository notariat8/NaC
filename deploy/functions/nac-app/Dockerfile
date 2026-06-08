FROM fnproject/python:3.12-dev AS build-stage

WORKDIR /function
COPY pyproject.toml README.md /function/
COPY src /function/src
COPY deploy/functions/nac-app/func.py /function/func.py
COPY deploy/functions/nac-app/func.yaml /function/func.yaml
COPY deploy/functions/nac-app/requirements.txt /function/requirements.txt
RUN pip3 install --target /python/ -r /function/requirements.txt

FROM fnproject/python:3.12

WORKDIR /function
COPY --from=build-stage /function /function
COPY --from=build-stage /python /python
RUN chmod -R a+rX /function /python
ENV PYTHONPATH=/python:/function/src
ENTRYPOINT ["/python/bin/fdk", "/function/func.py", "handler"]
