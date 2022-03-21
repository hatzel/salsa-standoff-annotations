# SALSA Standoff Annotations
This script does two things: creating standoff annotations and extracting document information for SALSA annotations from TIGER.
Document information enables you to use context beyond the individual sentence for frame annotations.

## Running the Script
Install dependecies, place required files in working directory and execute `main.py`.


### Dependencies
Only one: `pip install lxml`


### Required Files
- From [TIGER](https://www.ims.uni-stuttgart.de/documents/ressourcen/korpora/tiger-corpus/license/htmlicense.html):
    * `tiger_release_aug07.corrected.16012013.xml` [from here](https://www.ims.uni-stuttgart.de/documents/ressourcen/korpora/tiger-corpus/download/tigercorpus-2.2.xml.tar.gz) (download here after accepting their license)
    * `documents.tsv` from [here](https://www.ims.uni-stuttgart.de/documents/ressourcen/korpora/tiger-corpus/download/TIGER2.2.doc.zip) (download here after accepting their license)
- From [SALSA](https://www.coli.uni-saarland.de/projects/salsa/)
    - `salsa_release.xml` [from here](https://www.coli.uni-saarland.de/projects/salsa/corpus/download/salsa-corpus-2.0.tgz) (download from here after requesting access)


## Output Format
The output is a single jsonlines file where each line represents a document (i.e. each line is a valid JSON document).
Each document is represent as JSON with the following fields:
- `id`: TIGER's unique document id
- `text`: document text
- `frames`: a list of frames which each have:
    * `id`: SALSA's unique frame id
    * `name`: SALSA frame name (e.g. "Support")
    * `entities`: a list of frame entities which each have:
        * `id`: unique SALSA entity id
        * `name`: name of the frame entity (e.g. "Supported")
        * `refs`: list of indexes into `tokens` specifying which characters are covered by the annotation
    * `targets`: a list of frame targets which each have:
        * `lemma`: the base form of the target word
        * `refs`: list of indexes into `tokens` specifying which characters are covered by the annotation
- `tokens`: list of tokens with their individual character offsets in `text`
- `pos`: list of the part-of-speech tag for each token in `tokens`
- `sentences`: list of sentences with their individual character offsets in `text`


### Sample

<details>
<summary>Documents follow this basic JSON structure.</summary>

```json
{
  "id": "0001_0071",
  "text": "Kairo nimmt Extremisten fest KAIRO, 5. Juli (AFP). ...",
  "tokens": [
    [
      0,
      5
    ],
    [
      6,
      11
    ],
    [
      12,
      23
    ],
    [
      24,
      28
    ],
    [
      29,
      34
    ],
    [
      34,
      35
    ],
    [
      36,
      38
    ],
    [
      39,
      43
    ],
    [
      44,
      45
    ],
    [
      45,
      48
    ],
    [
      48,
      49
    ],
    [
      49,
      50
    ]
  ],
  "frames": [
    {
      "id": "festnehmen_s1394_f1",
      "name": "Arrest",
      "targets": [
        {
          "lemma": "festnehmen",
          "refs": [
            1,
            3
          ]
        }
      ],
      "entities": [
        {
          "id": "festnehmen_s1394_f1_e1",
          "name": "Authorities",
          "refs": [
            0
          ]
        },
        {
          "id": "festnehmen_s1394_f1_e2",
          "name": "Suspect",
          "refs": [
            2
          ]
        }
      ]
    }
  ],
  "sentences": [
    [
      0,
      28
    ],
    [
      29,
      50
    ]
  ]
}

```
</details>


The above example's content is taken from the [SALSA dataset](https://www.coli.uni-saarland.de/projects/salsa/) with meta information from [TIGER](https://www.ims.uni-stuttgart.de/documents/ressourcen/korpora/tiger-corpus/license/htmlicense.html).


### Example Code
This example below prints all frames with their respective target tokens.
```python
import json

for line in open("salsa.jsonlines"):
    doc = json.loads(line)
    tokens = doc["tokens"]
    for frame in doc["frames"]:
        name = frame["name"]
        spans = []
        for target in frame["targets"]:
            for ref in target["refs"]:
                spans.append(tokens[ref])
        target_words = []
        for span in spans:
            target_words.append(doc["text"][span[0]:span[1]])
        print(name, target_words)
```


## Limitations

Currently a lot of information from SALSA and TIGER is discarded, just some examples:
- part of speech information
- dependency information

In many machine learning based pipelines much of this information is probably no longer necessary, if you need it it should be fairly easy to add back in.
Pull requests welcome!

**Also note that the annotations are non-exhaustive!** SALSA only annotates a subset of sentences with frame information.

As far as I could tell neither TIGER nor SALSA contain information on whitespace around tokens, so the transformation from tokens to text relies on a heuristic.
This is bound to break in some edge cases but the text generally looks reasonable.

Split tokens: in some cases (~150 instances in the whole dataset) SALSA annotations only cover part of a token, this information is ignored and the annotation is treated as if it covers whole token instead. This split typically caused by compound words.
