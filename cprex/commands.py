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


cli = click.CommandCollection(sources=[main, rel])
