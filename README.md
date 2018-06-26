# source{d} ml [![PyPI](https://img.shields.io/pypi/v/sourced-ml.svg)](https://pypi.python.org/pypi/sourced-ml) [![Build Status](https://travis-ci.org/src-d/ml.svg)](https://travis-ci.org/src-d/ml) [![Docker Build Status](https://img.shields.io/docker/build/srcd/ml.svg)](https://hub.docker.com/r/srcd/ml) [![codecov](https://codecov.io/github/src-d/ml/coverage.svg?branch=master)](https://codecov.io/gh/src-d/ml)
 
This project is the foundation for machine learning on source code (or simply [MLonCode](https://github.com/src-d/awesome-machine-learning-on-source-code)) research and development. It abstracts machine learning engineer daily routine like features extraction, datasets collection and models training, allowing you to focus on higher level tasks.

source{d} ml is tightly coupled with [Engine](https://docs.sourced.tech/engine) and delegates all the feature extraction parallelization to it. It is written in Python3 and has been tested on Linux and macOS.

Note that source{d} ml is still under active development and can be changed a lot.

## Quick start with docker image
For a quick start, you can try to use our prebuild docker image. Simply run
```bash
docker run -it --rm srcd/ml --help
```

If this first command fails with
```text
Cannot connect to the Docker daemon. Is the docker daemon running on this host?
```

And you are sure that the daemon is running, then you need to add your user to `docker` group: refer to the [documentation](https://docs.docker.com/engine/installation/linux/linux-postinstall/#manage-docker-as-a-non-root-user).

## Installation
[Engine](https://docs.sourced.tech/engine) uses Spark. So ethier you have it and want to [use existing Apache Spark installation](#use-existing-apache-spark) or [get it included](#with-apache-spark-included).

### Pre-requisites
In both cases, you will need to have some native libraries installed. E.g., on Ubuntu `apt install curl libxml2-dev libsnappy-dev`. Some parts require [Tensorflow](https://tensorflow.org). Please, refer its documentation to install.

### With Apache Spark included
If you do not have existing spark in your system, you can get automatically. Just run:
```bash
pip3 install sourced-ml
```

### Use existing Apache Spark
If you already have Apache Spark installed and configured on your environment at `$APACHE_SPARK` you can re-use it and avoid downloading 200Mb through [pip "editable installs"](https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs) by

```bash
pip3 install -e "$SPARK_HOME/python"
pip3 install sourced-ml
```

## Overview
This tool is designed and built for experimenting with data and models as well as for training already investigated models. Therefore, there are many intermediate steps to roll-back if you decide to change something in your processing procedure or parameters set. In many applications we use a common pipeline: 

* **Data preprocessing.** We extract a data from repositories we want to analyze and save it separately. It is still raw data, but without any redundant information, we would not use. 
* **Create a dataset.** Convert raw data to a model you can feed to some ML algorithm. 
* **Train the model.** A dataset model as input will give you ready to use ML model as output. Note, that there are three steps if the method implementation requires special input format: convert from model format to input, train the model and convert the result back.

Please refer examples section to see specific pipelines. 
All parts of the functionality are available via command line until you want to build something custom. You can get full commands list via:

```bash
srcml --help
```
You need to combine them wisely to get a result you want. Let's explain all these commands you can run. If you want to know more about particular pipelines we use, please refer to [algorithms](doc/algorithms.md) section.

### preprocrepos
Repositories preprocessing. Converts repositories to parquet files with all necessary information you need for next steps. It can handle pure repositories directories as well as Siva files. It is recommended to start your pipeline here because you can preprocess your data once and then reuse it. It saves your time and adds a roll-back point if something goes wrong. 

Usually, only this step requires [Engine](https://docs.sourced.tech/engine) to process repository content as well as [Babelfish](https://docs.sourced.tech/babelfish) if you extract UASTs for analysis.

Please refer to [preprocrepos page](doc/cmd/preprocrepos.md) for more information or [examples page](doc/examples#2-preprocessing-step) for usage example.

### repo2...
Such commands as 'repos to something' extract datasets one can use to train models. [Modelforge format](https://docs.sourced.tech/modelforge) is used to store such models.

There are next commands available now. You can find usage examples on [examples page](docs/examples.md).

* **repos2bow**. A bow is a weighted bag of words (or features). Converts a document to its features. Available features are described in [BOW Features](docs/bow_features.md) section. 
* **repos2df** calculate document frequencies of features extracted from source code.
* **repos2ids** convert source code to a bag of identifiers.
* **repos2coocc** convert source code to the sparse co-occurrence matrix of identifiers.
* **repos2roleids** converts a UAST to a list of node role, identifier pairs. The role is merged roles from UAST where identifier was found.
* **repos2id_distance** converts a UAST to a list of identifier pairs and distance between them.
* **repos2idseq**. Converts a UAST to a sequence of identifiers sorted by order of appearance.

### id2vec-...
Commands that start from `id2vec-` used to build identifiers embeddings from co-occurrence matrix model via [Swivel algorithm](https://github.com/tensorflow/models/tree/master/research/swivel). Requires tensorflow to run. 

There are next four commands to build `id2vec` model:
* **id2vec-preproc** convert a sparse co-occurrence matrix to the Swivel shards. One can get co-occurrence matrix via `repo2coocc` command.
* **id2vec-train** train identifier embeddings using Swivel.
* **id2vec-postproc** combine row and column embeddings produced by Swivel and write them to an id2vec model.
* **id2vec-project** present id2vec model in Tensorflow Projector.

### Topic modeling
There are a set of commands that can be used to build a topic model on top of documents. 
* **bow2vw** convert a bag-of-words model to the dataset in Vowpal Wabbit format. It is an input format to [BigARTM](https://github.com/bigartm/bigartm) a powerful tool for topic modeling.
* **bigartm** install bigartm/bigartm to the current working directory. After that, you can use it separately via `bigartm` command. Please refer [official documentation](http://docs.bigartm.org/en/stable/) for help.
* **bigartm2asdf** converts a human-readable BigARTM model back to Modelforge format.

For more information about Topic modeling pipeline and examples please refer [topic modeling page](doc/topic_modeling.md).

### Utils
There are several additional helpers in command list: 
* **dump** command dump a model to stdout. Shows minimal information what model contains.
* **merge-df** command merge several DocumentFrequencies models to a single one. It is useful if you process your data in small chunks. For example, if you process [PGA dataset](https://docs.sourced.tech/intro#pubic-git-archive-pga), you can use subdirectories as chunks.
* **merge-coocc** command merge several Cooccurrences models together. The same idea as for **merge-df** command.

## Dependent projects 
Here is the list of proof-of-concept projects which are built using sourced.ml:

* [vecino](https://github.com/src-d/vecino) - finding similar repositories.
* [tmsc](https://github.com/src-d/tmsc) - listing topics of a repository.
* [apollo](https://github.com/src-d/apollo) - source code deduplication at scale.

## Contributions

...are welcome! See [CONTRIBUTING](contributing.md) and [CODE\_OF\_CONDUCT.md](code_of_conduct.md).

## License

[Apache 2.0](license.md)
