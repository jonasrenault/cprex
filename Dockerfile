## Docker CPREx image

## docker build -t cprex/cprex:CPREX_VERSION --build-arg CPREX_VERSION=CPREX_VERSION .
## docker run -t --rm -p 80:8501 {image_name}

# To connect to the container with a bash shell
# > docker exec -i -t {container_name} /bin/bash

# # -------------------
# # build builder image
# # -------------------
# FROM  openjdk:17-jdk-slim AS builder

# RUN apt-get update && apt-get -y --no-install-recommends install unzip

# ### download models
# # ADD https://ftp.ncbi.nlm.nih.gov/pub/lu/BC7-NLM-Chem-track/model_PubMedBERT_NLMChemBC5CDRBC7Silver.tar.gz /cprex/
# # RUN tar -xzf model_PubMedBERT_NLMChemBC5CDRBC7Silver.tar.gz \
# #     && rm model_PubMedBERT_NLMChemBC5CDRBC7Silver.tar.gz \
# #     && mv PubMedBERT_NLMChemBC5CDRBC7Silver pubmedbert

# # ADD https://gitlab.inria.fr/api/v4/projects/43830/packages/generic/cprex-rel-model/0.4.0/cprex-rel-model-0.4.0.tar.gz /cprex/
# # RUN tar -xzf cprex-rel-model-0.4.0.tar.gz \
# #     && rm cprex-rel-model-0.4.0.tar.gz \
# #     && mv model rel_model

# #############################
# ### download and build grobid
# #############################
# WORKDIR /opt/cprex
# ### download grobid source
# ADD https://github.com/kermitt2/grobid/archive/0.8.0.zip /opt/cprex/
# RUN unzip /opt/cprex/0.8.0.zip -d /opt/cprex \
#     && rm /opt/cprex/0.8.0.zip

# WORKDIR /opt/cprex/grobid-0.8.0/
# ### cleaning unused native libraries and models before packaging
# RUN rm -rf grobid-home/pdf2xml
# RUN rm -rf grobid-home/pdfalto/lin-32
# RUN rm -rf grobid-home/pdfalto/mac-64
# RUN rm -rf grobid-home/pdfalto/mac_arm-64
# RUN rm -rf grobid-home/pdfalto/win-*
# RUN rm -rf grobid-home/lib/lin-32
# RUN rm -rf grobid-home/lib/win-*
# RUN rm -rf grobid-home/lib/mac-64

# ### build grobid
# RUN ./gradlew clean assemble --no-daemon --info --stacktrace

# ### prepare grobid service
# WORKDIR /opt/cprex/grobid
# RUN unzip -o /opt/cprex/grobid-0.8.0/grobid-service/build/distributions/grobid-service-*.zip && \
#     mv grobid-service* grobid-service
# RUN unzip -o /opt/cprex/grobid-0.8.0/grobid-home/build/distributions/grobid-home-*.zip && \
#     chmod -R 755 /opt/cprex/grobid/grobid-home/pdfalto
# RUN rm -rf grobid-0.8.0

# # ########################################
# # ### download and build grobid-quantities
# # ########################################
# ### download grobid-quantities
# ADD --keep-git-dir=true https://github.com/jonasrenault/grobid-quantities.git#chemical-units /opt/cprex/grobid-quantities

# WORKDIR /opt/cprex/grobid-quantities
# RUN ./gradlew clean assemble --no-daemon --stacktrace --info

# ### prepare grobid-quantities service
# WORKDIR /opt/cprex/grobid
# RUN unzip -o /opt/cprex/grobid-quantities/build/distributions/grobid-quantities-*.zip -d grobid-quantities_distribution \
#     && mv grobid-quantities_distribution/grobid-quantities-* grobid-quantities

# ### Cleanup
# RUN rm -rf /opt/cprex/grobid-quantities

# ### Remove unused grobid models and files
# RUN rm -rf /opt/cprex/grobid/grobid-home/models/*-BidLSTM_*
# RUN rm -rf /opt/cprex/grobid/grobid-home/models/*-BERT_CRF*

# ----------------
# build python app
# ----------------
FROM python:3.11-slim AS app-builder

ENV PATH="$PATH:/root/.local/bin"

WORKDIR /cprex

### install poetry
RUN pip install poetry && poetry config virtualenvs.in-project true

### install dependencies and project
ADD pyproject.toml README.md ./
ADD .streamlit /cprex/.streamlit
ADD cprex /cprex/cprex

### Only install cpu version of pytorch in docker image.
### installing GPU version of pytorch for linux/amd64 image leads to image size of > 5Gb.
### see https://github.com/pytorch/pytorch/issues/17621
RUN sed -i 's/\(.*\)platform="linux", source="pypi"}/\1platform="linux", source="torchcpu"}/g' pyproject.toml
RUN poetry install --no-interaction --no-ansi --without dev --with models

# -------------------
# build runtime image
# -------------------
FROM python:3.11-slim

### instal JRE
# RUN apt-get update && apt-get -y --no-install-recommends install openjdk-17-jre

### COPY /cprex
WORKDIR /cprex
COPY --from=app-builder /cprex .

### copy .CPREX directory with models and grobid
# COPY --from=builder /opt/cprex /root/.cprex/

### Expose streamlit port
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT [ "./.venv/bin/python"]
CMD ["-m", "streamlit", "run", "cprex/ui/streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
