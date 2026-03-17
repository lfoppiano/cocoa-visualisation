import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List

import dotenv
import openai
from keybert.llm import OpenAI
from keybert.llm._openai import chat_completions_with_backoff, completions_with_backoff
from keybert.llm._utils import process_candidate_keywords

dotenv.load_dotenv(override=True)

from keybert import KeyLLM
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm


class AsyncOpenAIWrapper(OpenAI):

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

    async def _async_backoff_call(self, func, *args, **kwargs):
        """Async wrapper for backoff functions."""
        max_retries = kwargs.pop('max_retries', 3)
        for attempt in range(max_retries):
            try:
                # Run the synchronous backoff function in an executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            except Exception as e:
                # Handle redirect and timeout errors specifically
                if "redirect" in str(e).lower() or "timeout" in str(e).lower():
                    print(f"Redirect/timeout error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # Exponential backoff
                await asyncio.sleep(wait_time)

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
                response = await self._async_backoff_call(chat_completions_with_backoff, self.client, **kwargs)
            else:
                response = await self.client.chat.completions.create(**kwargs)
            keywords = response.choices[0].message.content.strip()

        # Use a non-chat model
        else:
            if self.exponential_backoff:
                response = await self._async_backoff_call(completions_with_backoff,
                                                          self.client, model=self.model, prompt=prompt,
                                                          **self.generator_kwargs
                                                          )
            else:
                response = await self.client.completions.create(model=self.model, prompt=prompt,
                                                                **self.generator_kwargs)
            keywords = response.choices[0].text.strip()

        return [keyword.strip() for keyword in keywords.split(",")]

    async def extract_keywords_async(self, documents: List[str], candidate_keywords: List[List[str]] = None):
        """Extract topics using parallel async processing.

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
        tasks = []
        for document, candidates in zip(documents, candidate_keywords):
            task = self._extract_single_keyword(document, candidates, semaphore)
            tasks.append(task)

        # Run all tasks concurrently and collect results
        all_keywords = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions and return successful results
        processed_keywords = []
        for result in all_keywords:
            if isinstance(result, Exception):
                print(f"Error in keyword extraction: {result}")
                processed_keywords.append([])  # Return empty list for failed extractions
            else:
                processed_keywords.append(result)

        return processed_keywords

    def extract_keywords(self, documents: List[str], candidate_keywords: List[List[str]] = None):
        """Synchronous wrapper for extract_keywords_async.

        Arguments:
            documents: The documents to extract keywords from
            candidate_keywords: A list of candidate keywords that the LLM will fine-tune

        Returns:
            all_keywords: All keywords for each document
        """
        # Check if we're already in an event loop
        try:
            asyncio.get_running_loop()
            # If we're in an event loop, we need to run the async function in a separate thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.extract_keywords_async(documents, candidate_keywords))
                return future.result()
        except RuntimeError:
            # No event loop running, we can use asyncio.run directly
            return asyncio.run(self.extract_keywords_async(documents, candidate_keywords))


client = openai.AsyncOpenAI(
    base_url=os.environ['LLM_URL'],
    api_key=os.environ['LLM_API_KEY'],
    timeout=120.0,
    max_retries=3,
    # http_client=None  # Let it handle redirects automatically
)

chatgpt = AsyncOpenAIWrapper(
    client,
    nb_workers=20,
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
    import gc
    try:
        # Process in smaller batches to avoid memory issues
        batch_size = 50
        all_results = []

        for i in range(0, len(works), batch_size):
            batch = works[i:i + batch_size]
            print(f"Processing batch {i // batch_size + 1} ({len(batch)} works)")

            abstracts = [work['abstract'] if 'abstract' in work and work['abstract'] is not None else "" for work in
                         batch]
            embeddings_abstracts = model.encode(abstracts, convert_to_tensor=True)
            keywords_abstracts = kw_model.extract_keywords(abstracts, embeddings=embeddings_abstracts, threshold=0.5)

            titles = [work['title'] if 'title' in work and work['title'] is not None else "" for work in batch]
            embeddings_titles = model.encode(titles, convert_to_tensor=True)
            keywords_titles = kw_model.extract_keywords(titles, embeddings=embeddings_titles, threshold=0.5)

            for idx, keywords_abstract in enumerate(keywords_abstracts):
                keyword_title = keywords_titles[idx]
                batch[idx]["keyterms_T"] = keyword_title[:2]
                batch[idx]["keyterms_A"] = keywords_abstract[:10]

            all_results.extend(batch)

            # Cleanup memory
            del embeddings_abstracts, embeddings_titles, keywords_abstracts, keywords_titles
            gc.collect()

        return all_results
    except Exception as e:
        import traceback
        print(f"Error in process_works: {e}")
        print(traceback.format_exc())
        raise


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
                import traceback

                print(f"Error processing {input_file}: {e}")
                print(traceback.format_exc())
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
