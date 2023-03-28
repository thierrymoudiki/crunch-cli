import typing
import pandas
import os
import click

from . import utils, ensure
from . import command


class _Inline:

    def call_data_process(self) -> typing.Union[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]:
        pass

    def call_train(self) -> pandas.DataFrame:
        pass

    def call_infer(self) -> pandas.DataFrame:
        pass


class _NoOpInline(_Inline):

    def __init__(self):
        print("no inline available outside of a notebook")


class _JupyterInline(_Inline):

    def __init__(self, module: typing.Any):
        self.module = module

        self.x_train = None
        self.y_train = None
        self.x_test = None
        self.model = None
        self.prediction = None

        self.session = utils.CustomSession(
            os.environ["WEB_BASE_URL"],
            os.environ["API_BASE_URL"],
            bool(os.environ.get("DEBUG", "False")),
        )

        print(f"loaded inline runner with module: {module}")

    def call_process_data(self) -> typing.Union[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]:
        handler = ensure.is_function(self.module, "data_process")

        (
            x_train_path,
            y_train_path,
            x_test_path
        ) = command.download(self.session)

        x_train = utils.read(x_train_path)
        y_train = utils.read(y_train_path)
        x_test = utils.read(x_test_path)

        result = handler(x_train, y_train, x_test)

        (
            self.x_train,
            self.y_train,
            self.x_test
        ) = ensure.return_data_process(result)

        return self.x_train, self.y_train, self.x_test

    def call_train(self) -> pandas.DataFrame:
        if self.x_train is None or self.y_train is None:
            print("call process_data() first")
            raise click.Abort()

        handler = ensure.is_function(self.module, "train")
        model = handler(self.x_train, self.y_train)
        self.model = ensure.return_train(model)

        return self.model

    def call_infer(self) -> pandas.DataFrame:
        if self.x_test is None:
            print("call process_data() first")
            raise click.Abort()

        if self.model is None:
            print("call train() first")
            raise click.Abort()

        handler = ensure.is_function(self.module, "infer")
        prediction = handler(self.model, self.x_test)
        self.prediction = ensure.return_infer(prediction)

        return self.prediction


def load(module: typing.Any):
    if utils.is_notebook():
        return _JupyterInline(module)

    return _NoOpInline()
