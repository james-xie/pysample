import os
import datetime

from pysample.context import SampleContext


class OutputRepository:
    """
    Store the sampling result with given OutputRepository.
    """

    def store(self, sample_context: SampleContext):
        raise NotImplementedError


class FileRepository(OutputRepository):
    """
    Store the sampling result to the given directory.
    """

    def __init__(self, directory: str):
        """
        :param directory:
            The directory for storing sampling results.
        """
        directory = self._prepare_dir(directory)
        self._directory = directory

    def _prepare_dir(self, directory: str) -> str:
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        full_dirname = f"{directory}/{today}"

        if not os.path.exists(directory):
            os.makedirs(full_dirname)
        elif not os.path.exists(full_dirname):
            os.makedirs(full_dirname)
        elif not os.path.isdir(directory):
            raise ValueError(f"'{directory}' is not a directory.")

        return full_dirname

    def store(self, sample_context: SampleContext):
        curtime = datetime.datetime.now().strftime("%H_%M_%S_%f")

        filename = f"{self._directory}/{sample_context.name}-{curtime}.txt"
        with open(filename, 'w') as file:
            file.write(sample_context.flame_output())
