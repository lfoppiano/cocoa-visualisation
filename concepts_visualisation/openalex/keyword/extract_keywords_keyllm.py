import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Union, List

import dotenv
import openai
from keybert.llm import OpenAI
from keybert.llm._openai import chat_completions_with_backoff, completions_with_backoff
from keybert.llm._utils import process_candidate_keywords

dotenv.load_dotenv(override=True)

from keybert import KeyLLM
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

class ASyncOpenAIWrapper(OpenAI):

    def __init__(self, client, nb_workers: int = 4, **kwargs):
        super().__init__(client, **kwargs)
        self.nb_workers = nb_workers

    async def _extract_single_keyword(self, document: str, candidates: List[str] = None, semaphore=None):
        """Extract keywords for a single document asynchronously."""
        if semaphore:
            async with semaphore:
                return await self._process_document(document, candidates)
        else:
            return await self._process_document(document, candidates)

    async def _process_document(self, document: str, candidates: List[str] = None):
        """Process a single document and return keywords."""
        prompt = self.prompt.replace("[DOCUMENT]", document)
        if candidates is not None:
            prompt = prompt.replace("[CANDIDATES]", ", ".join(candidates))

        # Delay
        if self.delay_in_seconds:
            await asyncio.sleep(self.delay_in_seconds)

        # Use a chat model
        if self.chat:
            messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": prompt}]
            kwargs = {"model": self.model, "messages": messages, **self.generator_kwargs}
            if self.exponential_backoff:
                response = await chat_completions_with_backoff(self.client, **kwargs)
            else:
                response = await self.client.chat.completions.create(**kwargs)
            keywords = response.choices[0].message.content.strip()

        # Use a non-chat model
        else:
            if self.exponential_backoff:
                response = await completions_with_backoff(
                    self.client, model=self.model, prompt=prompt, **self.generator_kwargs
                )
            else:
                response = await self.client.completions.create(model=self.model, prompt=prompt, **self.generator_kwargs)
            keywords = response.choices[0].text.strip()

        return [keyword.strip() for keyword in keywords.split(",")]

    def extract_keywords(self, documents: List[str], candidate_keywords: List[List[str]] = None):
        """Extract topics using parallel processing.

        Arguments:
            documents: The documents to extract keywords from
            candidate_keywords: A list of candidate keywords that the LLM will fine-tune
                        For example, it will create a nicer representation of
                        the candidate keywords, remove redundant keywords, or
                        shorten them depending on the input prompt.

        Returns:
            all_keywords: All keywords for each document
        """
        candidate_keywords = process_candidate_keywords(documents, candidate_keywords)

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.nb_workers)

        # Create async tasks for all documents
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            tasks = []
            for document, candidates in zip(documents, candidate_keywords):
                task = self._extract_single_keyword(document, candidates, semaphore)
                tasks.append(task)

            # Run all tasks concurrently and collect results
            all_keywords = loop.run_until_complete(asyncio.gather(*tasks))
            return all_keywords
        finally:
            loop.close()


client = openai.AsyncOpenAI(
    base_url=os.environ['LLM_URL'],
    api_key=os.environ['LLM_API_KEY']
)

chatgpt = ASyncOpenAIWrapper(
    client,
    nb_workers=50,
    model="Qwen/Qwen3-4B",
    chat=True
)


def process_single(input_file, output_file, model):
    with open(input_file) as dump_file:
        works = json.load(dump_file)

    works = process_works(works, model)

    with(open(output_file, 'w')) as fo:
        json.dump(works, fo)


def process_works(works, model):
    abstracts = [work['abstract'] if 'abstract' in work and work['abstract'] is not None else "" for work in
                 works]
    embeddings_abstracts = model.encode(abstracts, convert_to_tensor=True)
    keywords_abstracts = kw_model.extract_keywords(abstracts, embeddings=embeddings_abstracts, threshold=0.5)

    titles = [work['title'] if 'title' in work and work['title'] is not None else "" for work in works]
    embeddings_titles = model.encode(titles, convert_to_tensor=True)
    keywords_titles = kw_model.extract_keywords(titles, embeddings=embeddings_titles, threshold=0.5)

    for idx, keywords_abstract in enumerate(keywords_abstracts):
        keyword_title = keywords_titles[idx]

        works[idx]["keyterms_T"] = keyword_title[:2]
        works[idx]["keyterms_A"] = keywords_abstract[:10]

    return works


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract keywords using KeyLLM + KeyBERT. The documents are aggregated.")

    # Create mutually exclusive group for input/output options
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--input-corpus",
                       help="Directory containing the Openalex dump in JSON ",
                       required=False)
    group.add_argument("--input-json",
                       help="Single JSON file containing a list of openalex works",
                       required=False)
    group.add_argument("--input-text",
                       help="Input file as text, with one line per document on which generate keywords",
                       required=False)

    parser.add_argument("--output-dir",
                        required=False,
                        help="Output directory where to store the openalex dump + keywords (used with --input-corpus)")
    parser.add_argument("--output-json",
                        required=False,
                        help="Output JSON file where to store the input file with the added keywords (used with --input-json)")
    parser.add_argument("--output-text",
                        required=False,
                        help="Output file (used with --input-text)")

    args = parser.parse_args()

    # Validate input-output parameter pairs
    input_output_pairs = [
        ("input_corpus", "output_dir"),
        ("input_json", "output_json"),
        ("input_text", "output_text")
    ]

    for input_attr, output_attr in input_output_pairs:
        input_value = getattr(args, input_attr)
        output_value = getattr(args, output_attr)

        if input_value and not output_value:
            parser.error(f"--{output_attr.replace('_', '-')} is required when using --{input_attr.replace('_', '-')}")
        elif output_value and not input_value:
            parser.error(f"--{output_attr.replace('_', '-')} can only be used with --{input_attr.replace('_', '-')}")

    kw_model = KeyLLM(llm=chatgpt)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    if args.input_corpus and args.output_dir:
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)

        for filename in tqdm(os.listdir(args.input_corpus)):
            input_file = os.path.join(args.input_corpus, filename)
            output_file = os.path.join(args.output_dir, Path(filename).stem + ".json")
            if os.path.exists(output_file):
                continue

            print(f"Processing {input_file} -> {output_file}")

            with open(input_file) as dump_file:
                works = json.load(dump_file)
            try:
                works = process_works(works, model)

                with(open(output_file, 'w')) as fo:
                    json.dump(works, fo)
            except Exception as e:
                print(e)
                print(f"File {input_file} could not be processed. Skip it.")
                continue

                # middle = ceil(len(works)/2)
                # works_tmp = works[0:middle]
                # works1 = process_works(works_tmp, model)
                # output_file = os.path.join(output_dir, Path(filename).stem + "1.json")
                # with(open(output_file, 'w')) as fo:
                #     json.dump(works1, fo)
                #
                # works_tmp = works[middle:]
                # works2 = process_works(works_tmp, model)
                # output_file = os.path.join(output_dir, Path(filename).stem + "2.json")
                # with(open(output_file, 'w')) as fo:
                #     json.dump(works2, fo)


    elif args.input_text and args.output_text:
        lines = []
        with open(args.input_text, 'r') as input_file_text:
            for line in input_file_text:
                if not line:
                    continue
                lines.append(line)

        keywords = kw_model.extract_keywords(" ".join(lines))
        with open(args.output_text, 'w') as fo:
            json.dump(keywords, fo)

    elif args.input_json and args.output_json:
        if not os.path.exists(args.input_json):
            print("Input file does not exits. ")
            sys.exit(-1)
        process_single(args.input_json, args.output_json, model)
