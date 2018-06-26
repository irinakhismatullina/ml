# Algorithms pipeline
This page describes algorithms you can run via source{d} ml. Please ensure you install sourced.ml package before you proceed.  

## Common part
In all examples, we use the same Siva-files from [engine example directory](https://github.com/src-d/engine/tree/master/_examples/siva-files). Feel free to use any repositories you want, however, some parameters changes may be required. 

### Get the data
The easiest way to get the example of data is to run
```bash
mkdir example # Create a directory for this example  
cd example
mkdir sivas # Create a directory to store siva files
cd sivas
wget https://github.com/src-d/engine/raw/master/_examples/siva-files/2d58138f24fa863c235b0c33158b870a40c79ee2.siva
wget https://github.com/src-d/engine/raw/master/_examples/siva-files/5d4a8bf30c0da7209f651632b62a362620556c85.siva
wget https://github.com/src-d/engine/raw/master/_examples/siva-files/aac052c42c501abf6aa8c3509424e837bb27e188.siva
cd ..
```

Ok, now we have 3 siva files in `sivas` directory. You can check it via `ls -la sivas` command.

## Identifier embeddings

We build the source code identifier co-occurrence matrix for every repository from PGA dataset. Here we explain pipeline on a small example. 

### 1. Get repositories you want to analyze. 
Refer to the [Common part](#common-part) section to get the data.

### 2. Preprocessing step.
We do not need a lot of information that is stored in siva files but need a UAST. We use `preprocess` command, which gives us all we need:
```bash
python3 -m sourced.ml preprocrepos -r sivas -o parquets
```
We use `sivas` directory as input and put the result to `parquets` folder. If you try to process a lot of data, you should configure spark parameters. Please refer [spark section](spark.md) for more information.

Note: You can use `srcml` instead of `python3 -m sourced.ml`.

### 3. Build a co-occurrences
`repos2coocc` is used to build Cooccurencies modelforge model. About algorithm itself, you can read in [**TBD**]() section.
```bash
srcml repos2coocc \
    --parquet -r parquets \
    -o coocc.asdf --docfreq-out df.asdf \
    --split --min-docfreq 1 -l Java Python Go
```
Arguments description:
* `-r parquets` input directory with repositories information.
* `--parquet` tells that input directory contains parquet files after preprocessing step.
* `-o coocc.asdf` tells to save the result to `coocc.asdf` file.
* `--docfreq-out df.asdf` tells to save additional DocumentFrequensies model to `df.asdf` file.
* `--split` argument allow us to split identifiers based on special characters or case changes. For example split 'ThisIs_identifier' to 3 tokens ['this', 'is', 'identifier'] and use them instead of initial identifier. It is recommended to always use `--split` flag because it helps to keep dictionary size in reasonable values and get better identifiers embeddings.
* `--min-docfreq 1` specifies the minimum document frequency of each token. If token appears less than `min-docfreq` times, it will be excluded.
* `-l Java Python Go` specifies the languages to analyze. 

After running this command you can find two output models: `df.asdf` and `coocc.asdf`.
If you want to see what is inside you can run `srcml dump df.asdf` and `srcd dump coocc.asdf`

```text
$ srcml dump df.asdf
{'created_at': datetime.datetime(2018, 6, 19, 20, 2, 23, 931205),
 'dependencies': [],
 'model': 'docfreq',
 'uuid': '2cd008c8-c0e5-4f8e-bf1a-be473035cb69',
 'version': [1, 0, 0]}
Number of words: 879
Random 10 words: {'i.a': 8.0, 'i.abs': 4.0, 'i.abspath': 1.0, 'i.access': 4.0, 'i.acquir': 1.0, 'i.action': 2.0, 'i.activ': 4.0, 'i.adapt': 2.0, 'i.add': 5.0, 'i.addhead': 3.0}
Number of documents: 146
```

### 4. Train id2vec model
Now when we have a model with Co-occurrence matrix `coocc.asdf` we can build embeddings for each token we have in the matrix. [Swivel](https://github.com/tensorflow/models/tree/master/research/swivel) algorithm is used for that. Be sure you have tensorflow installed.

However, before we can run Swivel we should prepare data. 

#### 4.1. Swivel preprocessing.
To process huge matrixes Swivel uses shards. `id2vec_preproc` command is used to build them:
```bash
srcml id2vec_preproc \
    -i coocc.asdf --docfreq-in df.asdf \
    -o swivel_input \
    -s 879
```
Arguments description:
* `-i coocc.asdf` specifies input model to process.
* `--docfreq-in df.asdf` we also need additional DocumentFrequensies model from the previous stage.
* `-o swivel_input` specifies where to save swivel preprocessing results.
* `-s 879` is shard size. Default one in 4096. It is a small example with only 879 tokens, so we can not use a default value. 

After running this command you can find shards (only one in our case) in `swivel_input` directory. 

#### 4.2 Run swivel.
Now it is model training time. Run
```bash
srcml id2vec_train \
    --input_base_path swivel_input \
    --output_base_path swivel_output \
    --submatrix_cols 879 --submatrix_rows 879 \
    --num_epochs 4000  --embedding_size 3
```
You should spesify `--submatrix_cols` and `--submatrix_rows` for the same reason: it is too small example.
All others parameters names speak for themselves. 

As soon as it is a small toy example no guarantee it gives you any reasonable embeddings. Consider it as just demonstration.

#### 4.3 Swivel postprocessing.
The last step is to convert Swivel output to id2vec Modelforge model. 
```bash
srcml id2vec_postproc -i swivel_output -o id2vec.asdf
```
`-i swivel_output` is input directory with Swivel result and `-o id2vec.asdf` a name for your asdf model.

Here you are! You just build id2vec model. Dump it to see what is inside:
```text
$ srcml dump id2vec.asdf
{'created_at': datetime.datetime(2018, 6, 19, 20, 31, 57, 16511),
 'dependencies': [],
 'model': 'id2vec',
 'uuid': '4ba55218-eb8f-41f5-b191-14418cef39e1',
 'version': [1, 0, 0]}
Shape: (879, 3)
First 10 words: ['i.a', 'i.abs', 'i.abspath', 'i.access', 'i.acquir', 'i.action', 'i.activ', 'i.adapt', 'i.add', 'i.addhead']
```

## Weighted bag of features.

We can represent every repository as a weighted bag of features to solve any ML problem we want. For example, find code duplicates like we do in [Apollo project](https://github.com/src-d/apollo).
Here is a small example how to run `repos2bow`. Please, be sure you run [common part](#common-part) to get the `parquets` directory. 

```bash
srcml repos2bow --parquet -r parquets -f lit --bow bow.asdf --docfreq-out df-bow.asdf --mode func
```
Arguments description:
* `-r parquets` input directory with repositories information.
* `--parquet` tells that input directory contains parquet files after preprocessing step.
* `-f lit` specifies which features to extract. `lit` means literals, so source code will be converted to a bag of fixed numbers it has inside. To get more info about features refer to a [features page](doc/features.md).
* `--docfreq-out df-bow.asdf` will give you a Document Frequencies model. It shows how many documents contain certain literal. 
* `--mode func` specifies what to count as a document. `func` means functions. So each function considered as a separate document.

## Document Frequencies model.
If you extract [weighted bag of features.](#weighted-bag-of-features) via `repos2bow` you get Document Frequencies model as a bonus. However, in case you need only this model you can use `repos2df` command. Here is an example:
```bash
srcml repos2df --parquet -r parquets -f lit --docfreq-out df.asdf --mode func
```

## Identifiers sequence.
Converts each document to a sequence of identifiers.
```bash
srcml repos2idseq --parquet -r parquets -o ids_seq
```
`ids_seq` is a directory with a spark result. One can find `.csv` file inside.  

## Role-identifier pairs
`repos2roleids` converts a UAST to a list of node role and identifier pairs. The role is merged roles from UAST where identifier was found.
```bash
srcml repos2roleids --parquet -r parquets -o roleids
```
As a result, you have  `roleids` directory with `.csv` file inside. It is a dataset. One can try to build a model to predict identifier name by Node role and vise versa.

## Identifiers distance
`repos2id_distance` converts a UAST to a list of identifier pairs and distance between them. 
there are two distance types: `-t line` and `-t tree`. Line distance is distance is lines and tree distance is a length of the shortest path in UAST between identifiers nodes.
```bash
srcml repos2id_distance --parquet -r parquets -o ids_dist -t line
```
As a result, you have `ids_dist`  directory with `.csv` file inside. It is a dataset. One can try to build a model to predict a distance between identifiers.

## Topic modeling

See [here](topic_modeling.md).