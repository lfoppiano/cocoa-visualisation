import dotenv
from langchain.schema import OutputParserException

dotenv.load_dotenv(override=True)
import argparse
import json
from typing import List

from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from commons.openai import chat4_prompt_layer, chat_prompt_layer
from grobid_magneto.data_preparation.process_openai_extraction_quantities import extract_entities, _parse_json

PROMPT_TEMPLATE_USER = """Extract a list of 10 keywords sorted by importance."""


class ListOfKeywordsOutputParser(BaseModel):
    keywords: List[str]

    @staticmethod
    def parse_to_list(obj):
        return obj.keywords


def extract_keywords(text, llm):
    try:
        keywords = extract_entities(text, PROMPT_TEMPLATE_USER, llm,
                                                  ListOfKeywordsOutputParser)
    except OutputParserException as ope:
        output_data_quantities_raw = extract_entities(text, PROMPT_TEMPLATE_USER, llm)
        if output_data_quantities_raw.startswith("I don't know"):
            return ""
        output_parser = PydanticOutputParser(pydantic_object=ListOfKeywordsOutputParser)
        parsed_output = _parse_json(output_data_quantities_raw, llm, output_parser=output_parser)
        keywords = ListOfKeywordsOutputParser.parse_to_list(parsed_output)

    return keywords


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract keywords with LLM")

    parser.add_argument("--input",
                        help="Input file as text, with one line per document on which generate keywords",
                        required=False)
    parser.add_argument("--output",
                        required=False,
                        help="Output file")
    parser.add_argument("--model", help="Select the LLM model to use",
                        required=False, default="chatgpt", choices=["chatgpt", "gpt4"])

    args = parser.parse_args()

    # input_corpus = args.input_corpus
    # output_dir = args.output_dir
    input_file = args.input
    output_file = args.output
    model = args.model


    llm = chat_prompt_layer
    if model == "gpt4":
        llm = chat4_prompt_layer

    llm.pl_tags.append("keyword")

    lines = []
    with open(input_file, 'r') as input_file_text:
        for line in input_file_text:
            if not line:
                continue

            lines.append(line)

    keywords = extract_keywords(" ".join(lines), llm)
    with open(output_file, 'w') as fo:
        json.dump(keywords, fo)
