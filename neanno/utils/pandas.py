import os

WINDOWS_LINE_ENDING = b"\r\n"
UNIX_LINE_ENDING = b"\n"


def save_dataframe_to_csv(dataframe, file_path):
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
