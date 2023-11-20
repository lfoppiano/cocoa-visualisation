import os
from pathlib import Path

import dotenv
from langchain.chat_models import PromptLayerChatOpenAI, ChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate, \
    PromptTemplate
from langchain.schema import OutputParserException
from tqdm import tqdm

dotenv.load_dotenv(override=True)
import argparse
import json
from typing import List

from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel

PROMPT_TEMPLATE_CHAT_SYSTEM = """You are a useful assistant in extracting keywords from text."""
PROMPT_TEMPLATE_USER = """Given the following text between triple quotes: 
```
{text}
```
Extract a list of {top_n} keywords sorted by importance."""

lc_chatgpt = PromptLayerChatOpenAI(model_name="gpt-3.5-turbo",
                                   frequency_penalty=0.1,
                                   temperature=0,
                                   return_pl_id=True,
                                   pl_tags=["chatgpt", "concepts"])

lc_gpt4 = ChatOpenAI(model_name="gpt-4",
                     frequency_penalty=0.1,
                     temperature=0
                     )


def get_prompt(user_template, format_instructions=None) -> ChatPromptTemplate:
    system_message_prompt = SystemMessagePromptTemplate.from_template(PROMPT_TEMPLATE_CHAT_SYSTEM)
    human_message_prompt = HumanMessagePromptTemplate.from_template(user_template)

    if format_instructions:
        user_template += "\n{format_instructions}"

        human_message_prompt = HumanMessagePromptTemplate(
            prompt=PromptTemplate(
                template=user_template,
                input_variables=["text", "top_n"],
                partial_variables={"format_instructions": format_instructions})
        )

    prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    return prompt


def extract_entities(text, prompt_template, llm, output_parser_class=None, top_n=10):
    format_instructions = None
    if output_parser_class:
        output_parser = PydanticOutputParser(pydantic_object=output_parser_class)
        format_instructions = output_parser.get_format_instructions()

    prompt_chat_template = get_prompt(prompt_template, format_instructions)
    prompt_text = prompt_chat_template.format_messages(text=text, top_n=top_n)
    # print("Nb Tokens", chat.get_num_tokens_from_messages(prompt_text))

    results = llm(prompt_text)

    if output_parser_class:
        output = output_parser.parse(results.content)
        output = output_parser_class.parse_to_list(output)
    else:
        output = results.content

    return output


def _parse_json(response, llm, output_parser):
    system_message = "You are an useful assistant expert in materials science, physics, and chemistry " \
                     "that can process text and transform it to JSON."
    human_message = """Transform the text between three double quotes in JSON.\n\n\n\n
        {format_instructions}\n\nText: \"\"\"{text}\"\"\""""

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_message)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message)

    prompt_template = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    results = llm(
        prompt_template.format_prompt(
            text=response,
            format_instructions=output_parser.get_format_instructions()
        ).to_messages()
    )
    parsed_output = output_parser.parse(results.content)

    return parsed_output


class ListOfKeywordsOutputParser(BaseModel):
    keywords: List[str]

    @staticmethod
    def parse_to_list(obj):
        return obj.keywords


def extract_keywords(text, llm, top_n=10):
    try:
        keywords = extract_entities(text, PROMPT_TEMPLATE_USER, llm, ListOfKeywordsOutputParser, top_n=top_n)
    except OutputParserException as ope:
        output_data_quantities_raw = extract_entities(text, PROMPT_TEMPLATE_USER, llm, top_n=top_n)
        if output_data_quantities_raw.startswith("I don't know"):
            return ""
        output_parser = PydanticOutputParser(pydantic_object=ListOfKeywordsOutputParser)
        parsed_output = _parse_json(output_data_quantities_raw, llm, output_parser=output_parser)
        keywords = ListOfKeywordsOutputParser.parse_to_list(parsed_output)

    return keywords


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract keywords with LLM")

    parser.add_argument("--input-corpus",
                        help="Openalex dump in JSON",
                        required=False)
    parser.add_argument("--output-dir",
                        required=False,
                        help="Output directory")
    parser.add_argument("--input",
                        help="Input file as text, with one line per document on which generate keywords",
                        required=False)
    parser.add_argument("--output",
                        required=False,
                        help="Output file")
    parser.add_argument("--model", help="Select the LLM model to use",
                        required=False, default="chatgpt", choices=["chatgpt", "gpt4"])

    args = parser.parse_args()

    input_corpus = args.input_corpus
    output_dir = args.output_dir
    input_file = args.input
    output_file = args.output
    model = args.model

    llm = lc_chatgpt
    if model == "gpt4":
        llm = lc_gpt4

    if input_corpus and output_dir:
        for filename in tqdm(os.listdir(input_corpus), desc="Dump files"):
            with open(os.path.join(input_corpus, filename)) as dump_file:
                output_path = os.path.join(output_dir, Path(filename).stem + ".chatgpt.json")
                if os.path.exists(output_path):
                    continue

                works = json.load(dump_file)
                new_data = False

                for work in tqdm(works, desc="Document"):
                    abstract = work['abstract'] if 'abstract' in work and work['abstract'] is not None else ""
                    if abstract and 'keyterms_A' not in work:
                        try:
                            keywords_abstract = extract_keywords(abstract, llm, top_n=10)
                            work["keyterms_A"] = keywords_abstract
                            new_data = True
                        except:
                            print("Some problem processing abstract of {}. Ignoring it for the moment.".format(
                                work['doi']))

                    title = work['title'] if 'title' in work and work['title'] is not None else ""
                    if title and 'keyterms_T' not in work:
                        try:
                            keywords_title = extract_keywords(title, llm, top_n=2)
                            work["keyterms_T"] = keywords_title
                            new_data = True
                        except:
                            print(
                                "Some problem processing title of {}. Ignoring it for the moment.".format(work['doi']))

                if new_data:
                    with open(output_path, 'w') as fo:
                        json.dump(works, fo)

    elif input_file and output_file:
        lines = []
        with open(input_file, 'r') as input_file_text:
            for line in input_file_text:
                if not line:
                    continue

                lines.append(line)

        keywords = extract_keywords(" ".join(lines), llm)
        with open(output_file, 'w') as fo:
            json.dump(keywords, fo)
