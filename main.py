from lxml import etree
import itertools
from collections import defaultdict
from typing import Set, Tuple, List
import json


def recurse_to_terminals(full_ids, graph, terminals=None) -> Set[int]:
    if terminals is None:
        terminals = set()
    for id in full_ids:
        if "s" in id.split("_")[-1]:
            id = "_".join(id.split("_")[1:-1])
            print("Discarding split id, using whole word instead!")
        terminal = graph.find(f".//t[@id='{id}']")
        if terminal is not None:
            terminals.add(terminal)
        else:
            recurse_to_terminals(
                [
                    edge.attrib["idref"]
                    for edge in graph.findall(f".//nt[@id='{id}']/edge")
                ],
                graph,
                terminals,
            )
    return terminals


def get_id(item, key="id"):
    split = item.attrib[key].split("_")
    if "s" in split[-1]:
        print("Discarding split")
        return int(split[-2])
    else:
        return int(split[-1])


def parse_entity(entity, frame, graph):
    refs = []
    for fenode in entity.findall("fenode"):
        terminals = recurse_to_terminals([fenode.attrib["idref"]], graph)
        refs.extend([get_id(term, key="id") for term in terminals])
    return {
        "id": entity.attrib["id"],
        "name": entity.attrib["name"],
        "refs": list(set(refs)),
    }


def parse_target(target, frame, graph):
    refs = []
    for fenode in target.findall("fenode"):
        terminals = recurse_to_terminals([fenode.attrib["idref"]], graph)
        refs.extend([get_id(term, key="id") for term in terminals])
    return {
        "lemma": target.attrib["lemma"],
        "refs": list(set(refs)),
    }


def sentence_from_tokens(tokens: List[str], pos_list: List[str]) -> Tuple[str, List[Tuple[int, int]]]:
    """
    Apply some heuristics to create a sensible text text from the tokens.

    Unfortunately the original whitespace information is not available.
    """
    assert len(tokens) == len(pos_list)
    token_list = []
    out = ""
    for i, (token, pos) in enumerate(zip(tokens, pos_list)):
        if i < len(tokens) - 1:
            next_token = tokens[i + 1]
            next_pos = pos_list[i + 1]
        else:
            next_token = None
            next_pos = None
        token_list.append(tuple([len(out), len(out) + len(token)]))
        if (next_pos in ["$.", "$,"]
                or token in ["``", "(", "/"]
                or next_token in ["''", ")", "/"]
                or next_token is None):
            out += token
        else:
            out += token + " "
    return out, token_list


def text_from_tokens(sentences: List[List[str]], pos_lists: List[List[str]]) -> Tuple[str, List[Tuple[int, int]]]:
    text = ""
    token_list = []
    for sent_tokens, sent_pos in zip(sentences, pos_lists):
        sentence, sent_token_spec = sentence_from_tokens(sent_tokens, sent_pos)
        if len(text) != 0:
            add_whitespace = 1
        else:
            add_whitespace = 0
        sent_token_spec = [tuple([span[0] + len(text) + add_whitespace, span[1] + len(text) + add_whitespace]) for span in sent_token_spec]
        token_list.append(sent_token_spec)
        text += (" " * add_whitespace) + sentence
    return text, token_list


def read_salsa():
    parser = etree.XMLParser(ns_clean=True)
    tree = etree.parse(open("salsa_release.xml"), parser)
    sentences_iterator = tree.iterfind(".//body/s")
    sentences_salsa = {}
    frames_per_sent = defaultdict(list)
    for sentence in sentences_iterator:
        id_ = int(sentence.attrib["id"][1:])
        tokens = []
        pos_tags = []
        for terminal in sentence.findall(".//t"):
            tokens.append(terminal.attrib["word"])
            pos_tags.append(terminal.attrib["pos"])
        sentences_salsa[id_] = tokens
        graph = sentence.find("./graph")
        for frame in sentence.findall("./sem/frames/frame"):
            targets = frame.findall("./target")
            entities = frame.findall("./fe")
            targets_out = [parse_target(target, frame, graph) for target in targets]

            frames_per_sent[id_].append(
                {
                    "id": frame.attrib["id"],
                    "name": frame.attrib["name"],
                    "targets": targets_out,
                    "entities": [parse_entity(entity, frame, graph) for entity in entities],
                }
            )
    return sentences_salsa, frames_per_sent


def read_tiger():
    parser = etree.XMLParser(ns_clean=True, encoding="iso-8859-1")
    tiger_tree = etree.parse(open("tiger_release_aug07.corrected.16012013.xml", encoding="iso-8859-1"), parser)
    sentences_iterator = tiger_tree.iterfind(".//body/s")
    sentences_tiger = {}
    for sentence in sentences_iterator:
        id_ = int(sentence.attrib["id"][1:])
        tokens = []
        pos_tags = []
        for terminal in sentence.findall(".//t"):
            tokens.append(terminal.attrib["word"])
            pos_tags.append(terminal.attrib["pos"])
        sentences_tiger[id_] = (tokens, pos_tags)
    return sentences_tiger


def get_sent_doc_mapping():
    sentence_to_doc_file = open("documents.tsv")
    sent_doc_mapping = {}
    for line in sentence_to_doc_file:
        doc_id, sent_id = line.strip().split("\t")
        sent_id = int(sent_id)
        sent_doc_mapping[sent_id] = doc_id
    return sent_doc_mapping


sentences_salsa, frames_per_sent = read_salsa()
frames_file = open("frames.jsonlines", "w")
lemma_to_frame = defaultdict(set)
for frame in itertools.chain.from_iterable(frames_per_sent.values()):
    for target in frame["targets"]:
        lemma_to_frame[target["lemma"]].add(frame["name"])
    frames_file.write(json.dumps(frame))
    frames_file.write("\n")

sent_doc_mapping = get_sent_doc_mapping()
sentences_tiger = read_tiger()

# for salsa_id, salsa_sent in sentences_salsa.items():
#     assert salsa_sent == sentences_tiger[salsa_id]
#     if salsa_sent != sentences_tiger[salsa_id]:
#         print(salsa_sent, sentences_tiger[salsa_id])

documents = defaultdict(list)
document_frames = defaultdict(list)
for id_, sentence in sentences_tiger.items():
    documents[sent_doc_mapping[int(id_)]].append(sentence)
    document_frames[sent_doc_mapping[int(id_)]].append(frames_per_sent[id_])

out_file = open("out.jsonlines", "w")
for id_, doc in documents.items():
    sentence_tokens, sentence_pos = zip(*doc)
    text, token_spec = text_from_tokens(sentence_tokens, sentence_pos)
    data = {
        "id": id_,
        "text": text,
        "tokens": token_spec,
        "frames_per_sentence": document_frames[id_],
    }
    out_file.write(json.dumps(data))
    out_file.write("\n")
