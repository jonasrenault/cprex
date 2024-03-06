# nosec
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import click
import requests
from tqdm import tqdm

from cprex.crawler.chemrxiv import download_paper_metadata, download_pdfs_from_dump
from cprex.ner.chem_ner import get_ner_pipeline
from cprex.rel.evaluate import evaluate_model
from cprex.rel.parse_data import parse_label_studio_annotations

PUBMED_BERT_MODEL_URL = "https://ftp.ncbi.nlm.nih.gov/pub/lu/BC7-NLM-Chem-track/model_PubMedBERT_NLMChemBC5CDRBC7Silver.tar.gz"
GROBID_URL = "https://github.com/kermitt2/grobid/archive/"
GROBID_MASTER_URL = "https://github.com/kermitt2/grobid/zipball/master"


def pbar_download(url: str, fname: str | None = None, chunk_size: int = 1024) -> str:
    """
    Download a file from given url while displaying a progress bar.

    Parameters
    ----------
    url : str
        the url to download
    fname : str, optional
        filename to download to, by default None
    chunk_size : int, optional
        chunksize, by default 1024

    Returns
    -------
    str
        the downloaded filename
    """
    resp = requests.get(url, stream=True)
    total = int(resp.headers.get("content-length", 0))
    if fname is None:
        fname = tempfile.NamedTemporaryFile().name
    with (
        open(fname, "wb") as file,
        tqdm(
            desc=fname,
            total=total,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar,
    ):
        for data in resp.iter_content(chunk_size=chunk_size):
            size = file.write(data)
            bar.update(size)

    return fname


@click.group()
def main():
    pass


@click.group()
def rel():
    pass


@main.command()
@click.option(
    "-d",
    "--model-dir",
    "model_directory",
    help="directory where the model will be saved",
    default="pubmedbert",
    type=click.Path(dir_okay=True),
)
def download_pubmedbert(model_directory: str = "model") -> None:
    if Path(model_directory).is_dir():
        click.echo(
            f"Model directory {model_directory} already exists. "
            "PubMedBert model will not be downloaded."
        )
        return

    click.echo(f"Downloading PubMedBert model to {model_directory}")
    click.echo("This can take a while as model file is 1.4G ...")
    zipped_file = Path() / "pubmedbert-model.tar.gz"
    try:
        pbar_download(PUBMED_BERT_MODEL_URL, str(zipped_file))
        with tempfile.TemporaryDirectory() as tmp_dir:
            with tarfile.open(zipped_file, mode="r|gz") as f:
                f.extractall(path=tmp_dir)

            root_dir = os.listdir(tmp_dir)[0]
            shutil.move(os.path.join(tmp_dir, root_dir), model_directory)
    finally:
        if zipped_file.exists():
            os.remove(zipped_file)

    click.echo(f"Downloaded downloaded to {model_directory}")


@main.command()
@click.option(
    "-d",
    "--grobid-dir",
    "grobid_directory",
    help="directory where grobid will be saved",
    default="grobid",
    type=click.Path(dir_okay=True),
)
@click.option(
    "-v",
    "--grobid-version",
    "version",
    help="grobid version",
    default="0.8.0",
    type=str,
)
def download_grobid(grobid_directory: str, version: str = "0.8.0") -> None:
    if Path(grobid_directory).is_dir():
        click.echo(
            f"GROBID directory {grobid_directory} already exists. "
            "Grobid will not be downloaded."
        )
        click.echo("Run cprex start-grobid to start a Grobid server.")
    else:
        click.echo(f"Downloading Grobid ({version}) to {grobid_directory}")

        url = GROBID_MASTER_URL if version == "latest" else f"{GROBID_URL}{version}.zip"
        zipped_file = Path() / f"grobid-{version}.zip"
        try:
            pbar_download(url, str(zipped_file))
            with tempfile.TemporaryDirectory() as tmp_dir:
                subprocess.run(["unzip", str(zipped_file), "-d", str(tmp_dir)])
                root_dir = os.listdir(tmp_dir)[0]
                shutil.move(os.path.join(tmp_dir, root_dir), grobid_directory)
        finally:
            if zipped_file.exists():
                os.remove(zipped_file)

        click.echo(f"Downloaded Grobid ({version}) to {grobid_directory}")

    click.echo("Cloning grobid-quantities to grobid-quantites directory")
    subprocess.run(
        [
            "git",
            "clone",
            "--single-branch",
            "--branch",
            "chemical-units",
            "git@github.com:jonasrenault/grobid-quantities.git",
        ],
        cwd=grobid_directory,
    )

    click.echo("Installing grobid-quantities model")
    subprocess.run(
        ["./gradlew", "copyModels"], cwd=grobid_directory + "/grobid-quantities"
    )


@main.command()
@click.option(
    "-d",
    "--grobid-dir",
    "grobid_directory",
    help="path to the grobid directory",
    default="grobid",
    type=click.Path(dir_okay=True),
)
def start_grobid(grobid_directory: str):
    grobid_dir = Path() / grobid_directory
    qty_dir = grobid_dir / "grobid-quantities"
    cwds = [str(grobid_dir)]
    if qty_dir.is_dir():
        cwds.append(str(qty_dir))
    click.secho(
        "###########################################################",
        bg="blue",
        fg="white",
    )
    click.secho(
        "###########################################################",
        bg="blue",
        fg="white",
    )
    click.secho(
        "######           STARTING GROBID SERVER              ######",
        bg="blue",
        fg="white",
    )
    if qty_dir.is_dir():
        click.secho(
            "######       STARTING GROBID QUANTITIES SERVER       ######",
            bg="blue",
            fg="bright_magenta",
        )
    click.secho(
        "###########################################################",
        bg="blue",
        fg="white",
    )
    click.secho(
        "###########################################################",
        bg="blue",
        fg="white",
    )

    procs = [subprocess.Popen(["./gradlew", "run"], cwd=cwd) for cwd in cwds]
    for p in procs:
        p.wait()


@main.command()
@click.option(
    "-f",
    "--dump-file",
    "dump_file",
    help="file name for article metadata",
    default="chemrxiv_dump.jsonl",
    type=click.Path(file_okay=True),
)
@click.option(
    "-d",
    "--save-dir",
    "save_dir",
    help="save dir for downloaded article pdfs",
    default="chemrxiv_papers",
    type=click.Path(dir_okay=True),
)
@click.option(
    "-l", "limit", help="maximum number of articles to fetch", default=100, type=int
)
def crawl_chemrxiv(dump_file, save_dir, limit):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    metadata = Path(str(dump_file))
    download_paper_metadata(metadata, limit=limit)

    download_pdfs_from_dump(metadata, Path(save_dir))


@rel.command()
@click.option(
    "-c",
    "--corpus",
    "corpus_file",
    help="the annotated corpus file",
    default="resources/corpus/corpus.json",
    type=click.Path(file_okay=True),
)
@click.option(
    "-d",
    "--data-dir",
    "data_dir",
    help="output dir for train, dev and test sets",
    default="resources/rel/data",
    type=click.Path(dir_okay=True),
)
@click.option(
    "--test/--no-test",
    help="split data to create a test set",
    default=True,
)
@click.option(
    "-cv",
    "--cross-val",
    "cv",
    help="use cross validation",
    default=False,
    is_flag=True,
)
@click.option(
    "-m",
    "--mask",
    "masking",
    help="obfuscate entity names",
    default=False,
    is_flag=True,
)
def data(corpus_file: str, data_dir: str, test: bool, cv: bool, masking: bool):
    click.echo("Loading nlp pipeline...")
    nlp = get_ner_pipeline(enable_ner_pipelines=False)
    click.echo(f"Reading annotated corpus {corpus_file}...")
    parse_label_studio_annotations(
        Path(corpus_file), Path(data_dir), nlp, test, cv, masking
    )


@rel.command()
@click.option(
    "-c",
    "--config",
    "config",
    help="the model config file",
    default="cprex/rel/configs/rel_tok2vec.cfg",
    type=click.Path(file_okay=True),
)
@click.option(
    "-o",
    "--output",
    "output",
    help="the output directory",
    default="resources/rel/training",
    type=click.Path(dir_okay=True),
)
@click.option(
    "-t",
    "--train",
    "train_data",
    help="the train dataset",
    default="resources/rel/data/train.spacy",
    type=click.Path(file_okay=True),
)
@click.option(
    "-d",
    "--dev",
    "dev_data",
    help="the dev dataset",
    default="resources/rel/data/dev.spacy",
    type=click.Path(file_okay=True),
)
def train_tok2vec(config: str, output: str, train_data: str, dev_data: str):
    command = [
        "python",
        "-m",
        "spacy",
        "train",
        config,
        "--output",
        output,
        "--paths.train",
        train_data,
        "--paths.dev",
        dev_data,
        "-c",
        "./cprex/rel/custom_functions.py",
    ]
    subprocess.run(command)


@rel.command()
@click.option(
    "-c",
    "--config",
    "config",
    help="the model config file",
    default="cprex/rel/configs/rel_trf.cfg",
    type=click.Path(file_okay=True),
)
@click.option(
    "-o",
    "--output",
    "output",
    help="the output directory",
    default="resources/rel/training",
    type=click.Path(dir_okay=True),
)
@click.option(
    "-t",
    "--train",
    "train_data",
    help="the train dataset",
    default="resources/rel/data/train.spacy",
    type=click.Path(file_okay=True),
)
@click.option(
    "-d",
    "--dev",
    "dev_data",
    help="the dev dataset",
    default="resources/rel/data/dev.spacy",
    type=click.Path(file_okay=True),
)
@click.option(
    "-f",
    "--force",
    "force",
    help="force output directory",
    default=False,
    is_flag=True,
)
@click.option(
    "-cv",
    "--cross-val",
    "cv",
    help="run 5 fold cross validation training",
    default=False,
    is_flag=True,
)
def train_trf(
    config: str, output: str, train_data: str, dev_data: str, force: bool, cv: bool
):
    if cv:
        # Run 5 training while incrementing output, train and dev files
        output_dir = get_filename_with_count(Path(output), 0)
        for fold in range(5):
            output_dir = increment_directory(str(output_dir), force)
            train_file = get_filename_with_count(Path(train_data), fold)
            dev_file = get_filename_with_count(Path(dev_data), fold)
            click.echo(
                f"Training fold {fold}: output dir {output_dir}, train file "
                f"{train_file}, dev file {dev_file}"
            )
            command = [
                "python",
                "-m",
                "spacy",
                "train",
                config,
                "--output",
                str(output_dir),
                "--paths.train",
                str(train_file),
                "--paths.dev",
                str(dev_file),
                "-c",
                "./cprex/rel/custom_functions.py",
                "--gpu-id",
                "0",
            ]
            subprocess.run(command)

    else:
        output_dir = increment_directory(str(output), force)

        command = [
            "python",
            "-m",
            "spacy",
            "train",
            config,
            "--output",
            str(output_dir),
            "--paths.train",
            train_data,
            "--paths.dev",
            dev_data,
            "-c",
            "./cprex/rel/custom_functions.py",
            "--gpu-id",
            "0",
        ]
        subprocess.run(command)


def increment_directory(dir: str, force: bool) -> Path:
    output_dir = Path(dir)
    if (
        not force
        and output_dir.exists()
        and ((output_dir / "model-best").exists() or (output_dir / "model-last").exists())
    ):
        count = 0
        while output_dir.exists():
            output_dir = get_filename_with_count(Path(dir), count)
            count += 1

        click.echo(
            f"Target directory {dir} already exists. Saving results to {output_dir} "
            "instead. Use -f option to force directory."
        )

    return output_dir


def get_filename_with_count(file: Path, count: int) -> Path:
    basename = file.stem
    try:
        if basename.rindex("_") >= 0 and basename[basename.rindex("_") + 1 :].isdigit():
            basename = basename[: basename.rindex("_")]
    except ValueError:
        pass
    return file.parent / f"{basename}_{count}{file.suffix}"


@rel.command()
@click.option(
    "-m",
    "--model",
    "model",
    help="the trained model to evaluate",
    default="resources/rel/training/model-best",
    type=click.Path(dir_okay=True),
)
@click.option(
    "-t",
    "--test-data",
    "test_data",
    help="the test dataset",
    default="resources/rel/data/test.spacy",
    type=click.Path(file_okay=True),
)
def evaluate(model: str, test_data: str):
    evaluate_model(Path(model), Path(test_data), True)


cli = click.CommandCollection(sources=[main, rel])
