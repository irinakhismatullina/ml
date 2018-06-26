# Features 
This page explains features one can use in `repo2df` and `repo2bow` command via `-f` or `--feature` flags. 

## id
Converts code to a weighted bag of identifiers as features. For example, if you have python code:
```python
a = 1
b = 2
c = a + b
```
you have 3 identifiers here: `a`, `b` and `c`. So via `repo2bow -f id` command, you get next bag
```python
{
    'i.a': 2,
    'i.b': 2,
    'i.c': 1
}
```
`i.` is a prefix (or a namespace) to distinguish different types of features.

## lit
Converts code to a weighted bag of literals as features. For the same code snippet, we have next bag 
```python
{
    'l.1': 1,
    'l.2': 1
}
```
`l.` is a namespace for literals features. 

One can combine both features as `repo2bow -f id lit` and get next bag
```python
{
    'i.a': 2,
    'i.b': 2,
    'i.c': 1,
    'l.1': 1,
    'l.2': 1
}
```

## node2vec
Converts code to random sequencies of UAST nodes.
`r.` is a namespace.
Example **TBD**.

## uast2seq
Converts code to sequences of UAST nodes in order of appearance.  
`s.` is a namespace.
Example **TBD**.

## children
Converts code to pairs of UAST Role and number of children the node has.
`c.` is a namespace.
Example **TBD**.

## graphlet
Converts a UAST to a bag of graphlets. The graphlet of a UAST node is composed of the node itself, its parent and its children. Each node is represented by the internal role string.
`g.` is a namespace.
Example **TBD**.
