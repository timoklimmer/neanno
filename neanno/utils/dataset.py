import os
import config
import pandas as pd
import re

WINDOWS_LINE_ENDING = b"\r\n"
UNIX_LINE_ENDING = b"\n"


class DatasetLocation:
    supported_datasource_types = ["csv"]
    type = None
    path = None

    def __init__(self, location_as_string):
        self.type = location_as_string.split(":")[0]
        self.path = re.sub(r"^{}:".format(re.escape(self.type)), "", location_as_string)
        if self.type not in self.supported_datasource_types:
            config.parser.error(
                "Dataset location '{}' uses a datasource type '{}' which is not supported. Ensure that a valid datasource type is specified. Valid datasource types are: {}.".format(
                    location_as_string, type, ", ".join(self.supported_datasource_types)
                )
            )


class DatasetManager:
    def load_dataset_from_location_string(
        location_as_string, schema, fillna=True
    ):
        location = DatasetLocation(location_as_string)
        required_columns = list(schema.keys())
        result = getattr(
            DatasetManager, "load_dataset_from_location_string_{}".format(location.type)
        )(location, required_columns, True)
        for column_name in schema.keys():
            result[0][column_name] = result[0][column_name].astype(schema[column_name])
        return result

    def load_dataset_from_location_string_csv(location, required_columns, fill_na=True):
        file_to_load = location.path
        if not os.path.isfile(file_to_load):
            config.parser.error(
                "The file '{}' does not exist. Ensure that you specify a file which exists.".format(
                    file_to_load
                )
            )
        result = pd.read_csv(file_to_load)
        if fill_na:
            result = result.fillna("")
        if not pd.Series(required_columns).isin(result.columns).all():
            config.parser.error(
                "The specified dataset does not have the expected columns. Ensure that the dataset includes the following columns (case-sensitive): {}.".format(
                    ", ".join(required_columns)
                )
            )
        friendly_dataset_name = os.path.basename(file_to_load)
        return (result, friendly_dataset_name)

    def save_dataset_to_location_string(dataframe, location_as_string):
        location = DatasetLocation(location_as_string)
        getattr(
            DatasetManager, "save_dataset_to_location_string_{}".format(location.type)
        )(dataframe, location)

    def save_dataset_to_location_string_csv(dataframe, location):
        DatasetManager.save_dataset_to_csv(dataframe, location.path)

    def save_dataset_to_csv(dataframe, file_path):
        """This is a workaround to save CSV files properly on Windows. Due to a bug too many newlines may be added. This function prevents that."""

        dataframe.to_csv(file_path, header=True, index=False)

        # due to a bug in pandas we need to ensure our own on Windows that the contained line-endings are correct.
        # else we get duplicate newlines when reloading the written file.
        # bug might be solved in pandas 0.24, following code can be removed once a fixed pandas can be ensured
        if os.name == "nt":
            with open(file_path, "rb") as open_file:
                content = open_file.read()
            content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)
            with open(file_path, "wb") as open_file:
                open_file.write(content)
